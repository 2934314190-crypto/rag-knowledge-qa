import httpx

from ..config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self.model = settings.EMBED_MODEL_NAME
        self.base_url = settings.EMBED_BASE_URL
        self.api_key = settings.EMBED_API_KEY
        self.dim = settings.MILVUS_EMBED_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        url = f"{self.base_url.rstrip('/')}/embeddings"
        payload = {"model": self.model, "input": texts}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        result = []
        for item in data["data"]:
            emb = item["embedding"]
            result.append(emb[: self.dim] if self.dim else emb)
        return result


embedding_service = EmbeddingService()