from pymilvus import DataType, MilvusClient

from ..config import settings


class VectorStore:
    def __init__(self) -> None:
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection = settings.MILVUS_COLLECTION
        self.dim = settings.MILVUS_EMBED_DIM
        self._client: MilvusClient | None = None

    @property
    def client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(uri=settings.milvus_uri)
        return self._client

    def ensure_collection(self) -> None:
        if self.client.has_collection(self.collection):
            return
        schema = self.client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field("document_id", DataType.VARCHAR, max_length=128)
        schema.add_field("chunk_id", DataType.VARCHAR, max_length=128)
        schema.add_field("chunk_index", DataType.INT64)
        schema.add_field("text", DataType.VARCHAR, max_length=8192)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self.dim)

        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
        self.client.create_collection(
            collection_name=self.collection,
            schema=schema,
            index_params=index_params,
        )

    def insert(self, document_id: str, chunk_id: str, index: int, text: str, vector: list[float]) -> None:
        self.client.insert(
            self.collection,
            {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "chunk_index": index,
                "text": text,
                "vector": vector,
            },
        )

    def search(self, vector: list[float], top_k: int, threshold: float) -> list[dict]:
        res = self.client.search(
            collection_name=self.collection,
            data=[vector],
            limit=top_k,
            output_fields=["document_id", "chunk_id", "chunk_index", "text"],
            search_params={"metric_type": "COSINE", "params": {"radius": threshold}},
        )
        hits = res[0]
        out = []
        for h in hits:
            entity = h.get("entity", {})
            out.append(
                {
                    "score": round(float(h.get("distance", 0.0)), 4),
                    "document_id": entity.get("document_id"),
                    "chunk_id": entity.get("chunk_id"),
                    "chunk_index": entity.get("chunk_index"),
                    "text": entity.get("text"),
                }
            )
        return out

    def count(self) -> int:
        stats = self.client.get_collection_stats(self.collection)
        return int(stats.get("row_count", 0))

    def is_connected(self) -> bool:
        try:
            self.client.list_collections()
            return True
        except Exception:
            return False


vector_store = VectorStore()