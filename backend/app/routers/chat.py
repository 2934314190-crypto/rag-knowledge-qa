import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import ChatRequest
from ..services.rag import rag_service
from ..services.embedding import embedding_service

router = APIRouter()


@router.post("/chat")
async def chat(body: ChatRequest):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        hits = rag_service.retrieve(body.query, body.top_k, body.threshold)
    except Exception:
        hits = []

    if not hits:
        answer = "未在知识库中找到相关内容，无法回答该问题。可以尝试调整相似度阈值或检索数量。"
        async def empty_stream():
            yield f"data: {json.dumps({'token': answer}, ensure_ascii=False)}\n\n"

        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    context = rag_service.build_context(hits)
    messages = rag_service.chat_prompt(body.query, context, body.top_k, body.threshold, hits)

    def gen():
        try:
            for token in rag_service.stream_answer(messages):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")