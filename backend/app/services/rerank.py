import httpx

from ..config import settings


class RerankService:
    def __init__(self) -> None:
        self.model = settings.RERANK_MODEL_NAME
        self.base_url = settings.RERANK_BASE_URL
        self.api_key = settings.RERANK_API_KEY
        self.top_n = settings.RERANK_TOP_K

    def rerank(self, query: str, documents: list[str]) -> list[int]:
        if not documents or not settings.RERANK_API_KEY:
            return list(range(len(documents)))
        url = f"{self.base_url.rstrip('/')}/rerank"
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": min(self.top_n, len(documents)),
            "return_documents": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        ordered = sorted(data.get("results", []), key=lambda x: x["index"])
        ordered = sorted(ordered, key=lambda x: x.get("relevance_score", 0), reverse=True)
        indices = [int(item["index"]) for item in ordered[: self.top_n]]
        return indices


rerank_service = RerankService()