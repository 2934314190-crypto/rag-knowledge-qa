from fastapi import APIRouter

from ..config import settings
from ..schemas import HealthOut
from ..services.vector_store import vector_store

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health():
    connected, count = True, 0
    if vector_store.is_connected():
        try:
            count = vector_store.count()
        except Exception:
            count = 0
    else:
        connected = False
    return HealthOut(
        status="ok" if connected else "offline",
        model=settings.LLM_MODEL_NAME,
        embedding=settings.EMBED_MODEL_NAME,
        embedding_dim=settings.MILVUS_EMBED_DIM,
        collection_count=count,
    )