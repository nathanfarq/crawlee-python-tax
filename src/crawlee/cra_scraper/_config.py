"""Configuration module for CRA scraping."""

import os
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class QdrantConfig(BaseModel):
    """Qdrant vector database configuration."""

    cluster_name: str = ''
    cluster_id: str = ''
    endpoint: str = ''
    api_key: str | None = None
    collection_name: str = 'cra_tax_data'
    vector_size: int = 384  # sentence-transformers/all-MiniLM-L6-v2 size


class ScrapingLimits(BaseModel):
    """Rate limiting and scraping restrictions."""

    # Conservative defaults for government sites like canada.ca
    max_requests_per_minute: int = 10
    max_requests_per_hour: int = 200
    max_requests_per_day: int = 1000
    request_delay: float = 3.0  # seconds between requests
    max_concurrent_requests: int = 1
    max_retries: int = 3
    retry_delay: float = 10.0


class CRAConfig(BaseSettings):
    """Main configuration for CRA scraping."""

    model_config = {'env_prefix': 'CRA_', 'env_file': '.env'}

    # Base URLs
    base_url: str = 'https://www.canada.ca/en/revenue-agency.html'
    allowed_domains: list[str] = Field(default_factory=lambda: ['canada.ca'])

    # Qdrant configuration
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)

    # Scraping limits
    limits: ScrapingLimits = Field(default_factory=ScrapingLimits)

    # Text processing
    min_text_length: int = 50
    max_text_length: int = 10000

    # Storage
    data_dir: str = './cra_data'

    # Logging
    log_level: str = 'INFO'

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Override Qdrant configuration from environment variables if available
        if 'QDRANT_API_KEY' in os.environ:
            self.qdrant.api_key = os.environ['QDRANT_API_KEY']
        if 'QDRANT_ENDPOINT' in os.environ:
            self.qdrant.endpoint = os.environ['QDRANT_ENDPOINT']
        if 'QDRANT_CLUSTER_NAME' in os.environ:
            self.qdrant.cluster_name = os.environ['QDRANT_CLUSTER_NAME']
        if 'QDRANT_CLUSTER_ID' in os.environ:
            self.qdrant.cluster_id = os.environ['QDRANT_CLUSTER_ID']
