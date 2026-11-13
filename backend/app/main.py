from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import chat, documents, health

app = FastAPI(title="RAG 知识库问答系统", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    return {"service": "rag", "status": "running"}