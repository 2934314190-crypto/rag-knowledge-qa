from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL_NAME: str = "deepseek-chat"

    EMBED_MODEL_NAME: str = "BAAI/bge-m3"
    EMBED_API_KEY: str
    EMBED_BASE_URL: str = "https://api.siliconflow.cn/v1"

    RERANK_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    RERANK_API_KEY: str
    RERANK_BASE_URL: str = "https://api.siliconflow.cn/v1"

    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "rag_knowledge"
    MILVUS_EMBED_DIM: int = 1024

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RERANK_TOP_K: int = 3
    DEFAULT_TOP_K: int = 4
    DEFAULT_THRESHOLD: float = 0.3

    DATA_DIR: Path = BASE_DIR / "data"

    @property
    def milvus_uri(self) -> str:
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"


settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)