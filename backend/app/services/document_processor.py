import re

from ..config import settings


class DocumentProcessor:
    def __init__(self) -> None:
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP

    @staticmethod
    def extract_text(raw: bytes) -> str:
        return raw.decode("utf-8", errors="ignore")

    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        sections = self._split_by_headings(text)
        chunks: list[str] = []
        for section in sections:
            chunks.extend(self._chunk_by_size(section))
        return chunks

    def _split_by_headings(self, text: str) -> list[str]:
        parts = re.split(r"(?m)(?=^#{1,6}\s)", text)
        return [p.strip() for p in parts if p.strip()]

    def _chunk_by_size(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        chunks: list[str] = []
        step = max(self.chunk_size - self.chunk_overlap, 1)
        for i in range(0, len(text), step):
            chunk = text[i : i + self.chunk_size]
            if chunk.strip():
                chunks.append(chunk)
            if i + self.chunk_size >= len(text):
                break
        return chunks


document_processor = DocumentProcessor()