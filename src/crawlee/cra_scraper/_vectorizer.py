"""Text vectorization for CRA tax data."""

import asyncio
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore


class CRAVectorizer:
    """Text vectorizer using sentence transformers for semantic search."""

    def __init__(
        self,
        *,
        model_name: str = 'all-MiniLM-L6-v2',
        chunk_size: int = 3000,
        overlap_size: int = 500,
        max_chunks_per_page: int = 10,
    ) -> None:
        if SentenceTransformer is None:
            raise ImportError(
                'sentence-transformers is required for vectorization. Install with: pip install crawlee[cra-scraper]'
            )

        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._vector_size = 384  # Default for all-MiniLM-L6-v2

        # Chunking configuration
        self._chunk_size = chunk_size
        self._overlap_size = overlap_size
        self._max_chunks_per_page = max_chunks_per_page

    async def initialize(self) -> None:
        """Initialize the sentence transformer model."""
        if self._model is not None:
            return

        logger.info(f'Loading sentence transformer model: {self._model_name}')

        # Load model in executor to avoid blocking
        loop = asyncio.get_event_loop()
        self._model = await loop.run_in_executor(None, SentenceTransformer, self._model_name)

        # Get actual vector size from model
        self._vector_size = self._model.get_sentence_embedding_dimension()

        logger.info(f'Model loaded. Vector size: {self._vector_size}')

    async def vectorize_text(self, text: str) -> list[float]:
        """Convert text to vector representation."""
        if self._model is None:
            await self.initialize()

        # Truncate text if too long (model has token limits)
        if len(text) > 8000:  # Conservative limit
            text = text[:8000] + '...'

        # Generate embedding in executor to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self._model.encode, text)

        return embedding.tolist()

    async def vectorize_batch(self, texts: list[str]) -> list[list[float]]:
        """Vectorize multiple texts efficiently."""
        if self._model is None:
            await self.initialize()

        # Truncate texts if needed
        processed_texts = []
        for text in texts:
            if len(text) > 8000:
                text = text[:8000] + '...'
            processed_texts.append(text)

        # Generate embeddings in executor
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._model.encode, processed_texts)

        return [emb.tolist() for emb in embeddings]

    def _split_text_into_chunks(self, text: str) -> list[str]:
        """Split text into overlapping chunks for comprehensive vectorization."""
        if len(text) <= self._chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text) and len(chunks) < self._max_chunks_per_page:
            # Calculate end position
            end = start + self._chunk_size

            # If this is not the last chunk, try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 200 characters
                search_start = max(start + self._chunk_size - 200, start)
                sentence_endings = [m.end() for m in re.finditer(r'[.!?]\s+', text[search_start:end])]

                if sentence_endings:
                    # Use the last sentence ending as the chunk boundary
                    end = search_start + sentence_endings[-1]

                # Ensure we don't create chunks smaller than overlap size
                if end - start < self._overlap_size:
                    end = start + self._chunk_size

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            if end >= len(text):
                break

            start = end - self._overlap_size

            # Ensure we make progress even with overlap
            if len(chunks) > 1 and start <= end - self._chunk_size + self._overlap_size:
                start = end - (self._overlap_size // 2)

        return chunks

    def _create_chunk_metadata(
        self, base_data: dict[str, Any], chunk_text: str, chunk_index: int, total_chunks: int
    ) -> dict[str, Any]:
        """Create metadata for a text chunk."""
        chunk_data = base_data.copy()

        # Add chunk-specific metadata
        chunk_data.update(
            {
                'chunk_index': chunk_index,
                'total_chunks': total_chunks,
                'chunk_text': chunk_text,
                'is_chunked': total_chunks > 1,
            }
        )

        # Modify title to indicate chunk
        if total_chunks > 1 and 'title' in chunk_data:
            chunk_data['title'] = f'{chunk_data["title"]} (Part {chunk_index + 1}/{total_chunks})'

        return chunk_data

    def create_combined_text(self, data: dict[str, Any], use_chunk_text: bool = False) -> str:
        """Create combined text from structured tax data for vectorization."""
        parts = []

        # Title (weighted more heavily)
        if data.get('title'):
            parts.append(f'Title: {data["title"]}')

        # Page type
        if data.get('page_type'):
            parts.append(f'Type: {data["page_type"]}')

        # Tax year
        if data.get('tax_year'):
            parts.append(f'Tax Year: {data["tax_year"]}')

        # Form number
        if data.get('form_number'):
            parts.append(f'Form: {data["form_number"]}')

        # Main content - use chunk_text if available, otherwise full content
        if use_chunk_text and data.get('chunk_text'):
            parts.append(f'Content: {data["chunk_text"]}')
        elif data.get('content'):
            parts.append(f'Content: {data["content"]}')

        return ' | '.join(parts)

    async def vectorize_tax_data(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Vectorize tax data using chunking approach and return list of vectorized chunks."""
        content = data.get('content', '')

        # Split content into chunks
        chunks = self._split_text_into_chunks(content)
        logger.info(f'Split content into {len(chunks)} chunks for vectorization')

        # Create chunk data
        chunk_data_list = []
        for i, chunk_text in enumerate(chunks):
            chunk_data = self._create_chunk_metadata(data, chunk_text, i, len(chunks))
            chunk_data_list.append(chunk_data)

        # Create combined texts for all chunks
        combined_texts = [self.create_combined_text(chunk_data, use_chunk_text=True) for chunk_data in chunk_data_list]

        # Vectorize all chunks in batch
        vectors = await self.vectorize_batch(combined_texts)

        # Combine chunk data with vectors
        result = []
        for chunk_data, vector, combined_text in zip(chunk_data_list, vectors, combined_texts, strict=False):
            result.append(
                {
                    **chunk_data,
                    'vector': vector,
                    'combined_text': combined_text,
                }
            )

        return result

    @property
    def vector_size(self) -> int:
        """Get the size of vectors produced by this model."""
        return self._vector_size

    @property
    def model_name(self) -> str:
        """Get the name of the model being used."""
        return self._model_name
