import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..schemas import ChunkOut, DocumentDetail, MetadataOut, MetaUpdate
from ..services.document_processor import document_processor
from ..services.embedding import embedding_service
from ..services.vector_store import vector_store
from ..storage import metadata_store

router = APIRouter()


@router.post("/documents/upload", response_model=DocumentDetail)
async def upload_document(
    file: UploadFile = File(...),
    source_name: str = Form(default=""),
):
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="仅支持 .md 格式文件")

    raw = await file.read()
    text = document_processor.extract_text(raw)
    chunks = document_processor.split(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容为空或无法解析")

    if not source_name:
        source_name = file.filename

    document_id = metadata_store.new_id()

    try:
        vectors = embedding_service.embed(chunks)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"向量化失败: {exc}")

    try:
        vector_store.ensure_collection()
        for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            chunk_id = f"{document_id}_c{i}"
            vector_store.insert(document_id, chunk_id, i, chunk_text, vector)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"写入向量库失败: {exc}")

    chunk_count = len(chunks)
    created_at = datetime.datetime.now().isoformat(timespec="seconds")
    metadata = {
        "source_name": source_name,
        "filename": file.filename,
        "size": len(raw),
        "chunk_count": chunk_count,
        "created_at": created_at,
        "doc_type": "markdown",
        "extras": {},
    }

    chunk_out = [ChunkOut(index=i, text=t, chunk_id=f"{document_id}_c{i}") for i, t in enumerate(chunks)]
    metadata_store.save_document(document_id, metadata, [c.model_dump() for c in chunk_out])

    return DocumentDetail(
        document_id=document_id,
        metadata=MetadataOut(**metadata),
        chunks=chunk_out,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str):
    doc = metadata_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    chunks = [ChunkOut(**c) for c in doc["chunks"]]
    return DocumentDetail(
        document_id=document_id,
        metadata=MetadataOut(**doc["metadata"]),
        chunks=chunks,
    )


@router.patch("/documents/{document_id}/metadata", response_model=MetadataOut)
async def update_document_metadata(document_id: str, body: MetaUpdate):
    updated = metadata_store.update_metadata(document_id, body.metadata)
    if not updated:
        raise HTTPException(status_code=404, detail="文档不存在")
    return MetadataOut(**updated)