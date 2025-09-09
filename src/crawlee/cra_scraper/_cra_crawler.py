"""CRA-specific crawler for tax data collection."""

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from marshmallow import ValidationError

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

from ._config import CRAConfig
from ._data_validator import CRADataValidator
from ._qdrant_client import CRAQdrantClient
from ._rate_limiter import CRARateLimiter
from ._vectorizer import CRAVectorizer

logger = logging.getLogger(__name__)


class CRACrawler:
    """CRA-specific crawler with integrated data processing pipeline."""

    def __init__(self, *, config: CRAConfig | None = None) -> None:
        self._config = config or CRAConfig()

        # Initialize components
        self._rate_limiter = CRARateLimiter(
            max_requests_per_minute=self._config.limits.max_requests_per_minute,
            max_requests_per_hour=self._config.limits.max_requests_per_hour,
            max_requests_per_day=self._config.limits.max_requests_per_day,
            request_delay=self._config.limits.request_delay,
        )

        self._validator = CRADataValidator(allowed_domains=self._config.allowed_domains)

        self._vectorizer = CRAVectorizer()

        self._qdrant_client = CRAQdrantClient(
            endpoint=self._config.qdrant.endpoint,
            api_key=self._config.qdrant.api_key,
            collection_name=self._config.qdrant.collection_name,
            vector_size=self._config.qdrant.vector_size,
        )

        # Crawler instance
        self._crawler: PlaywrightCrawler | None = None

        # Statistics
        self._stats = {
            'pages_crawled': 0,
            'pages_processed': 0,
            'pages_stored': 0,
            'chunks_created': 0,
            'validation_errors': 0,
            'processing_errors': 0,
        }

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info('Initializing CRA crawler components...')

        # Initialize vectorizer and Qdrant client
        await self._vectorizer.initialize()
        await self._qdrant_client.initialize()

        # Update vector size in config if different
        actual_vector_size = self._vectorizer.vector_size
        if actual_vector_size != self._config.qdrant.vector_size:
            logger.warning(f'Vector size mismatch. Using {actual_vector_size}')

        # Create crawler
        self._crawler = PlaywrightCrawler(
            max_requests_per_crawl=self._config.limits.max_requests_per_day,
            max_request_retries=self._config.limits.max_retries,
            request_handler_timeout=60,
        )

        # Set up request handler
        @self._crawler.router.default_handler
        async def handle_page(context: PlaywrightCrawlingContext) -> None:
            await self._handle_page(context)

        logger.info('CRA crawler initialized successfully')

    async def _handle_page(self, context: PlaywrightCrawlingContext) -> None:
        """Handle a single page crawl."""
        # Rate limiting
        await self._rate_limiter.acquire()

        self._stats['pages_crawled'] += 1

        try:
            # Extract page data
            data = await self._extract_page_data(context)

            if not data:
                logger.warning(f'No data extracted from {context.request.url}')
                return

            # Validate data
            try:
                validated_data = self._validator.validate_data(data)
                logger.info(f'Validated data from {context.request.url}')
            except ValidationError as e:
                logger.error(f'Validation error for {context.request.url}: {e}')
                self._stats['validation_errors'] += 1
                return

            self._stats['pages_processed'] += 1

            # Vectorize data (now returns list of chunks)
            vectorized_chunks = await self._vectorizer.vectorize_tax_data(validated_data)

            # Store all chunks in Qdrant using batch operation
            if len(vectorized_chunks) > 1:
                point_ids = await self._qdrant_client.store_batch(vectorized_chunks)
                logger.info(
                    f'Successfully processed and stored {context.request.url} as {len(point_ids)} chunks: {point_ids}'
                )
            else:
                # Single chunk - use individual storage
                point_id = await self._qdrant_client.store_data(vectorized_chunks[0])
                logger.info(f'Successfully processed and stored {context.request.url} as {point_id}')

            self._stats['pages_stored'] += len(vectorized_chunks)
            self._stats['chunks_created'] += len(vectorized_chunks)

            # Discover new links if this is the base URL
            if context.request.url == self._config.base_url:
                await self._discover_links(context)

        except Exception as e:
            logger.error(f'Processing error for {context.request.url}: {e}')
            self._stats['processing_errors'] += 1

    async def _extract_page_data(self, context: PlaywrightCrawlingContext) -> dict[str, Any] | None:
        """Extract relevant data from the page."""
        try:
            # Wait for page to load
            await context.page.wait_for_load_state('networkidle', timeout=10000)

            # Extract title
            title_element = await context.page.query_selector('title')
            title = await title_element.text_content() if title_element else ''

            if not title:
                # Try h1 as fallback
                h1_element = await context.page.query_selector('h1')
                title = await h1_element.text_content() if h1_element else 'No title'

            # Extract main content
            content_selectors = [
                'main',
                '[role="main"]',
                '.main-content',
                '.content',
                'article',
                '.article-content',
                '#content',
                'body',  # fallback
            ]

            content = ''
            for selector in content_selectors:
                element = await context.page.query_selector(selector)
                if element:
                    content = await element.text_content()
                    if content and len(content.strip()) > self._config.min_text_length:
                        break

            # Clean up content
            content = content.strip() if content else ''

            # Check minimum requirements
            if not title or not content or len(content) < self._config.min_text_length:
                return None

            # Truncate if too long
            if len(content) > self._config.max_text_length:
                content = content[: self._config.max_text_length] + '...'

            return {
                'url': context.request.url,
                'title': title.strip(),
                'content': content,
                'extracted_at': datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f'Data extraction error: {e}')
            return None

    async def _discover_links(self, context: PlaywrightCrawlingContext) -> None:
        """Discover and queue relevant links from the main page."""
        try:
            # Find links that might contain tax information
            tax_link_patterns = [
                'href*="tax"',
                'href*="form"',
                'href*="business"',
                'href*="individual"',
                'href*="guide"',
                'href*="information"',
                'href*="/en/"',  # English pages
            ]

            discovered_links = set()

            for pattern in tax_link_patterns:
                links = await context.page.query_selector_all(f'a[{pattern}]')

                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        # Convert to absolute URL
                        absolute_url = urljoin(context.request.url, href)

                        # Validate URL
                        if self._validator.validate_url(absolute_url):
                            discovered_links.add(absolute_url)

            # Queue discovered links
            requests = [{'url': url} for url in discovered_links]

            if requests:
                logger.info(f'Discovered {len(requests)} potential tax-related links')
                await context.add_requests(requests[:100])  # Limit to 100 links per page

        except Exception as e:
            logger.error(f'Link discovery error: {e}')

    async def crawl(self, start_url: str | None = None) -> dict[str, Any]:
        """Start crawling from the specified URL."""
        if self._crawler is None:
            await self.initialize()

        url = start_url or self._config.base_url

        logger.info(f'Starting CRA crawl from {url}')

        # Reset stats
        self._stats = {
            'pages_crawled': 0,
            'pages_processed': 0,
            'pages_stored': 0,
            'chunks_created': 0,
            'validation_errors': 0,
            'processing_errors': 0,
        }

        # Start crawling
        await self._crawler.run([url])

        # Get final stats
        final_stats = {
            **self._stats,
            'rate_limiter_stats': self._rate_limiter.get_stats(),
            'collection_stats': await self._qdrant_client.get_collection_info(),
        }

        logger.info(f'Crawl completed. Results: {final_stats}')

        return final_stats

    async def search_similar_content(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar content in the stored data."""
        if self._vectorizer._model is None:
            await self._vectorizer.initialize()

        # Vectorize the query
        query_vector = await self._vectorizer.vectorize_text(query)

        # Search in Qdrant
        results = await self._qdrant_client.search_similar(
            query_vector=query_vector,
            limit=limit,
        )

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get current crawler statistics."""
        return {
            **self._stats,
            'rate_limiter_stats': self._rate_limiter.get_stats(),
            'config': {
                'base_url': self._config.base_url,
                'allowed_domains': self._config.allowed_domains,
                'limits': {
                    'max_requests_per_minute': self._config.limits.max_requests_per_minute,
                    'max_requests_per_hour': self._config.limits.max_requests_per_hour,
                    'max_requests_per_day': self._config.limits.max_requests_per_day,
                },
            },
        }
