"""Qdrant vector database client for CRA tax data."""

import uuid
from typing import Any

from crawlee._utils import console

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.models import Distance, PointStruct, VectorParams
except ImportError:
    QdrantClient = None  # type: ignore
    Distance = None  # type: ignore
    VectorParams = None  # type: ignore
    PointStruct = None  # type: ignore
    models = None  # type: ignore


class CRAQdrantClient:
    """Qdrant client for storing and searching CRA tax data vectors."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str | None = None,
        collection_name: str = 'cra_tax_data',
        vector_size: int = 384,
    ) -> None:
        if QdrantClient is None:
            raise ImportError(
                'qdrant-client is required for vector storage. Install with: pip install crawlee[cra-scraper]'
            )

        self._endpoint = endpoint
        self._api_key = api_key
        self._collection_name = collection_name
        self._vector_size = vector_size
        self._client: QdrantClient | None = None

    async def initialize(self) -> None:
        """Initialize the Qdrant client and create collection if needed."""
        if self._client is not None:
            return

        console.print(f'[blue]Connecting to Qdrant at {self._endpoint}[/blue]')

        # Initialize client
        self._client = QdrantClient(
            url=self._endpoint,
            api_key=self._api_key,
        )

        # Check if collection exists, create if not
        try:
            collection_info = self._client.get_collection(self._collection_name)
            console.print(f'[green]Connected to existing collection: {self._collection_name}[/green]')
        except Exception:
            console.print(f'[yellow]Creating new collection: {self._collection_name}[/yellow]')
            await self._create_collection()

    async def _create_collection(self) -> None:
        """Create the collection with appropriate vector configuration."""
        if self._client is None:
            raise RuntimeError('Client not initialized')

        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(
                size=self._vector_size,
                distance=Distance.COSINE,
            ),
        )
        console.print(f'[green]Collection {self._collection_name} created successfully[/green]')

    async def store_data(self, data: dict[str, Any]) -> str:
        """Store vectorized tax data in Qdrant."""
        if self._client is None:
            await self.initialize()

        if 'vector' not in data:
            raise ValueError("Data must contain a 'vector' field")

        # Generate unique ID
        point_id = str(uuid.uuid4())

        # Prepare payload (exclude vector)
        payload = {k: v for k, v in data.items() if k != 'vector'}

        # Convert datetime to string if present
        if 'extracted_at' in payload:
            payload['extracted_at'] = payload['extracted_at'].isoformat()

        # Create point
        point = PointStruct(
            id=point_id,
            vector=data['vector'],
            payload=payload,
        )

        # Upload point
        self._client.upsert(
            collection_name=self._collection_name,
            points=[point],
        )

        console.print(f'[green]Stored data point {point_id} in Qdrant[/green]')
        return point_id

    async def store_batch(self, data_list: list[dict[str, Any]]) -> list[str]:
        """Store multiple vectorized tax data points efficiently."""
        if self._client is None:
            await self.initialize()

        points = []
        point_ids = []

        for data in data_list:
            if 'vector' not in data:
                continue

            point_id = str(uuid.uuid4())
            point_ids.append(point_id)

            # Prepare payload
            payload = {k: v for k, v in data.items() if k != 'vector'}

            # Convert datetime to string if present
            if 'extracted_at' in payload:
                payload['extracted_at'] = payload['extracted_at'].isoformat()

            points.append(
                PointStruct(
                    id=point_id,
                    vector=data['vector'],
                    payload=payload,
                )
            )

        if points:
            self._client.upsert(
                collection_name=self._collection_name,
                points=points,
            )
            console.print(f'[green]Stored {len(points)} data points in Qdrant[/green]')

        return point_ids

    async def search_similar(
        self,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search for similar tax data using vector similarity."""
        if self._client is None:
            await self.initialize()

        search_result = self._client.search(
            collection_name=self._collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )

        results = []
        for hit in search_result:
            result = {
                'id': hit.id,
                'score': hit.score,
                **hit.payload,
            }
            results.append(result)

        return results

    async def get_collection_info(self) -> dict[str, Any]:
        """Get information about the collection."""
        if self._client is None:
            await self.initialize()

        info = self._client.get_collection(self._collection_name)

        return {
            'name': self._collection_name,
            'points_count': info.points_count,
            'vector_size': info.config.params.vectors.size,
            'distance_metric': info.config.params.vectors.distance.value,
        }

    async def delete_collection(self) -> None:
        """Delete the entire collection (use with caution)."""
        if self._client is None:
            await self.initialize()

        self._client.delete_collection(self._collection_name)
        console.print(f'[red]Deleted collection: {self._collection_name}[/red]')

    async def count_points(self) -> int:
        """Get the total number of points in the collection."""
        if self._client is None:
            await self.initialize()

        info = self._client.get_collection(self._collection_name)
        return info.points_count
