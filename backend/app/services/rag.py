import json
from collections.abc import Iterator

from openai import OpenAI

from ..config import settings
from .embedding import embedding_service
from .rerank import rerank_service
from .vector_store import vector_store


class RagService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        self.model = settings.LLM_MODEL_NAME

    def retrieve(
        self, query: str, top_k: int, threshold: float
    ) -> list[dict]:
        qvec = embedding_service.embed([query])[0]
        hits = vector_store.search(qvec, top_k=top_k, threshold=threshold)
        if not hits:
            return []
        texts = [
            f"[片段 {h['chunk_index']} · {h.get('document_id', '')} · 相关度{h['score']}]\n{h['text']}"
            for h in hits
        ]
        idxs = rerank_service.rerank(query, texts)
        return [hits[i] for i in idxs]

    def build_context(self, hits: list[dict]) -> str:
        blocks = []
        for h in hits:
            blocks.append(f"[片段 {h['chunk_index']} · 文档 {h.get('document_id', '')} · 相关度{h['score']}]")
            blocks.append(h["text"])
            blocks.append("")
        return "\n".join(blocks).strip()

    def stream_answer(self, messages: list[dict]) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.7,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            token = getattr(delta, "content", None) or ""
            if token:
                yield token

    def chat_prompt(self, query: str, context: str, top_k: int, threshold: float, hits: list[dict]) -> list[dict]:
        system = (
            "你是一个企业知识库问答助手。请严格根据提供的知识片段回答问题，"
            "不要编造知识片段中没有的内容。如果片段不足以回答，请如实说明。"
        )
        user = (
            f"知识片段：\n{context}\n\n"
            f"检索参数：top_k={top_k}, threshold={threshold}，命中{len(hits)}条。\n\n"
            f"问题：{query}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


rag_service = RagService()