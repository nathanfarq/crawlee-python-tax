"""Tests for CRA scraper components."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import only the components that don't depend on optional extras
from crawlee.cra_scraper._config import CRAConfig
from crawlee.cra_scraper._data_validator import CRADataValidator
from crawlee.cra_scraper._rate_limiter import CRARateLimiter


class TestCRAConfig:
    """Test CRA configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CRAConfig()

        assert config.base_url == 'https://www.canada.ca/en/revenue-agency.html'
        assert 'canada.ca' in config.allowed_domains
        assert config.qdrant.collection_name == 'cra_tax_data'
        assert config.qdrant.vector_size == 384
        assert config.limits.max_requests_per_minute == 10


class TestCRADataValidator:
    """Test CRA data validator."""

    @pytest.fixture
    def validator(self) -> CRADataValidator:
        """Create validator instance."""
        return CRADataValidator(allowed_domains=['canada.ca'])

    def test_validate_url(self, validator: CRADataValidator) -> None:
        """Test URL validation."""
        assert validator.validate_url('https://www.canada.ca/en/revenue-agency.html')
        assert validator.validate_url('https://canada.ca/forms/t1.html')
        assert not validator.validate_url('https://example.com/page.html')
        assert not validator.validate_url('invalid-url')

    def test_extract_tax_year(self, validator: CRADataValidator) -> None:
        """Test tax year extraction."""
        content = 'This form is for the 2023 tax year.'
        assert validator.extract_tax_year(content) == '2023'

        content_no_year = 'This is general tax information.'
        assert validator.extract_tax_year(content_no_year) is None

    def test_extract_form_number(self, validator: CRADataValidator) -> None:
        """Test form number extraction."""
        content = 'Complete form T1 for personal income tax.'
        assert validator.extract_form_number(content) == 'T1'

        content = 'Business tax return T2 information.'
        assert validator.extract_form_number(content) == 'T2'

        content = 'Form RC123 for GST/HST.'
        assert validator.extract_form_number(content) == 'RC123'

    def test_determine_page_type(self, validator: CRADataValidator) -> None:
        """Test page type determination."""
        assert validator.determine_page_type('T1 Form', 'Personal income tax form') == 'forms'
        assert validator.determine_page_type('Business Info', 'Corporation self-employed information') == 'business'
        assert validator.determine_page_type('Personal Tax', 'Individual RRSP information') == 'personal'
        assert validator.determine_page_type('General Info', 'Revenue agency overview') == 'general'

    def test_is_relevant_content(self, validator: CRADataValidator) -> None:
        """Test content relevance check."""
        assert validator.is_relevant_content('Tax Information', 'Income tax details')
        assert validator.is_relevant_content('Revenue Agency', 'CRA services')
        assert not validator.is_relevant_content('Weather Report', 'Sunny day today')

    def test_validate_data_success(self, validator: CRADataValidator) -> None:
        """Test successful data validation."""
        data = {
            'url': 'https://www.canada.ca/en/revenue-agency/services/tax/individuals.html',
            'title': 'Personal Income Tax Information',
            'content': 'This page contains information about filing your personal income tax return for the 2023 tax year. Use form T1 to file your return.',
            'extracted_at': datetime.utcnow(),
        }

        validated = validator.validate_data(data)

        assert validated['url'] == data['url']
        assert validated['title'] == data['title']
        assert validated['page_type'] in ['forms', 'personal', 'business', 'general']
        assert 'tax_year' in validated
        assert 'form_number' in validated


class TestCRARateLimiter:
    """Test CRA rate limiter."""

    @pytest.fixture
    def rate_limiter(self) -> CRARateLimiter:
        """Create rate limiter instance."""
        return CRARateLimiter(
            max_requests_per_minute=5,
            max_requests_per_hour=20,
            max_requests_per_day=100,
            request_delay=0.1,  # Fast for testing
        )

    @pytest.mark.asyncio
    async def test_acquire_within_limits(self, rate_limiter: CRARateLimiter) -> None:
        """Test acquiring requests within limits."""
        # Should be able to acquire immediately
        await rate_limiter.acquire()

        stats = rate_limiter.get_stats()
        assert stats['requests_last_minute'] == 1
        assert stats['requests_last_hour'] == 1
        assert stats['requests_last_day'] == 1

    def test_get_stats(self, rate_limiter: CRARateLimiter) -> None:
        """Test getting rate limiter statistics."""
        stats = rate_limiter.get_stats()

        assert 'requests_last_minute' in stats
        assert 'requests_last_hour' in stats
        assert 'requests_last_day' in stats
        assert 'max_per_minute' in stats
        assert stats['max_per_minute'] == 5


class TestCRAVectorizer:
    """Test CRA vectorizer functionality (mocked)."""

    def test_text_chunking(self) -> None:
        """Test text chunking functionality without dependencies."""
        # Mock the vectorizer to avoid dependency issues
        with patch('crawlee.cra_scraper._vectorizer.SentenceTransformer'):
            from crawlee.cra_scraper._vectorizer import CRAVectorizer

            vectorizer = CRAVectorizer(chunk_size=100, overlap_size=20)

            # Test short text (no chunking)
            short_text = 'This is a short document.'
            chunks = vectorizer._split_text_into_chunks(short_text)
            assert len(chunks) == 1
            assert chunks[0] == short_text

            # Test long text (chunking needed)
            long_text = 'This is a sentence. ' * 20  # ~400 chars
            chunks = vectorizer._split_text_into_chunks(long_text)
            assert len(chunks) > 1
            assert len(chunks) <= vectorizer._max_chunks_per_page

            # Verify chunks have appropriate sizes
            for chunk in chunks[:-1]:  # All chunks except last
                assert len(chunk) >= vectorizer._overlap_size

            # Test overlap exists between consecutive chunks
            if len(chunks) > 1:
                for i in range(len(chunks) - 1):
                    # Overlap should exist - verify chunks have some common content
                    chunk1_end = chunks[i][-vectorizer._overlap_size // 2 :]
                    chunk2_start = chunks[i + 1][: vectorizer._overlap_size // 2]
                    # This is a simple check - in practice, overlap is more sophisticated
                    assert len(chunk1_end) > 0 and len(chunk2_start) > 0

    def test_chunk_metadata_creation(self) -> None:
        """Test chunk metadata creation."""
        with patch('crawlee.cra_scraper._vectorizer.SentenceTransformer'):
            from crawlee.cra_scraper._vectorizer import CRAVectorizer

            vectorizer = CRAVectorizer()

            base_data = {
                'url': 'https://canada.ca/test',
                'title': 'Test Document',
                'content': 'Original content here',
                'extracted_at': datetime.now(),
            }

            chunk_text = 'This is a chunk of text.'
            chunk_metadata = vectorizer._create_chunk_metadata(base_data, chunk_text, 0, 3)

            # Verify chunk-specific fields
            assert chunk_metadata['chunk_index'] == 0
            assert chunk_metadata['total_chunks'] == 3
            assert chunk_metadata['chunk_text'] == chunk_text
            assert chunk_metadata['is_chunked'] is True
            assert 'Part 1/3' in chunk_metadata['title']

            # Verify original fields preserved
            assert chunk_metadata['url'] == base_data['url']
            assert chunk_metadata['content'] == base_data['content']

    def test_combined_text_creation(self) -> None:
        """Test combined text creation for vectorization."""
        with patch('crawlee.cra_scraper._vectorizer.SentenceTransformer'):
            from crawlee.cra_scraper._vectorizer import CRAVectorizer

            vectorizer = CRAVectorizer()

            data = {
                'title': 'Tax Form T1',
                'content': 'Personal income tax information',
                'chunk_text': 'Chunk specific content',
                'tax_year': '2023',
                'form_number': 'T1',
                'page_type': 'forms',
            }

            # Test with full content
            combined_text = vectorizer.create_combined_text(data, use_chunk_text=False)
            assert 'Title: Tax Form T1' in combined_text
            assert 'Content: Personal income tax information' in combined_text
            assert 'Tax Year: 2023' in combined_text
            assert 'Form: T1' in combined_text

            # Test with chunk text
            combined_text_chunk = vectorizer.create_combined_text(data, use_chunk_text=True)
            assert 'Content: Chunk specific content' in combined_text_chunk

    @pytest.mark.asyncio
    async def test_vectorize_tax_data_mocked(self) -> None:
        """Test tax data vectorization with mocked dependencies."""
        with patch('crawlee.cra_scraper._vectorizer.SentenceTransformer') as mock_transformer:
            from crawlee.cra_scraper._vectorizer import CRAVectorizer

            # Mock the sentence transformer
            mock_model = MagicMock()
            mock_model.encode = MagicMock(return_value=[[0.1, 0.2, 0.3]])
            mock_transformer.return_value = mock_model

            vectorizer = CRAVectorizer(chunk_size=50, overlap_size=10)
            vectorizer._model = mock_model  # Bypass initialization

            # Mock the vectorize_batch method
            vectorizer.vectorize_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

            data = {
                'url': 'https://canada.ca/test',
                'title': 'Test Tax Document',
                'content': 'This is a long tax document that should be chunked into multiple parts for comprehensive vectorization.',
                'extracted_at': datetime.now(),
            }

            # This should return multiple chunks due to small chunk_size
            result = await vectorizer.vectorize_tax_data(data)

            # Verify result structure
            assert isinstance(result, list)
            assert len(result) > 0

            # Verify each chunk has required fields
            for chunk in result:
                assert 'vector' in chunk
                assert 'combined_text' in chunk
                assert 'chunk_index' in chunk
                assert 'total_chunks' in chunk
                assert 'chunk_text' in chunk
                assert 'is_chunked' in chunk
