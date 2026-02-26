from __future__ import annotations

import json
import logging
from typing import Iterable

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_ollama import OllamaEmbeddings
from pydantic import BaseModel, Field

from rag_healthbot_server.config import settings
from rag_healthbot_server.services.db.ConversationRepo import (
    append_conversation_message_pair,
    get_conversation,
)
from rag_healthbot_server.services.db.ReportEmbeddingRepo import (
    search_report_embeddings_by_cosine_distance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    conversationId: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


def _sse_data(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _make_llm() -> ChatGroq:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY must be set")
    if not settings.llm_model:
        raise ValueError("LLM_MODEL must be set")

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
        temperature=0.2,
        timeout=60,
        streaming=True,
    )


def _make_embedder() -> OllamaEmbeddings:
    if not settings.ollama_host or not settings.ollama_embed_model:
        raise ValueError("OLLAMA_HOST and OLLAMA_MODEL must be set")
    return OllamaEmbeddings(
        base_url=settings.ollama_host,
        model=settings.ollama_embed_model,
    )


def _build_messages(
    *,
    report_context: str | None,
    history: list[dict],
    user_message: str,
) -> list[SystemMessage | HumanMessage | AIMessage]:
    system = SystemMessage(
        content=(
            "You are a helpful medical-information assistant. "
            "Answer clearly and concisely. "
            "If the user asks for medical advice, include a brief safety note to consult a clinician."
        )
    )

    messages: list[SystemMessage | HumanMessage | AIMessage] = [system]

    if report_context and report_context.strip():
        messages.append(
            SystemMessage(
                content=(
                    "Relevant excerpts from the report are provided below. "
                    "Use them as primary evidence when answering questions about the report.\n\n"
                    f"{report_context.strip()}"
                )
            )
        )

    for m in history or []:
        user = (m or {}).get("userContent")
        ai = (m or {}).get("aiContent")
        if user:
            messages.append(HumanMessage(content=str(user)))
        if ai:
            messages.append(AIMessage(content=str(ai)))

    messages.append(HumanMessage(content=user_message))
    return messages


def _format_report_context(chunks: list[str]) -> str:
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        text = (c or "").strip()
        if not text:
            continue
        lines.append(f"[Excerpt {i}]\n{text}")
    return "\n\n".join(lines)


@router.post("")
def post_chat(payload: ChatRequest):
    try:
        conversation_id = int(payload.conversationId)
    except Exception:
        return JSONResponse(
            status_code=404, content={"error": "Conversation not found"}
        )

    conversation = get_conversation(conversation_id)
    if conversation is None:
        return JSONResponse(
            status_code=404, content={"error": "Conversation not found"}
        )

    user_message = payload.message.strip()
    if not user_message:
        return JSONResponse(status_code=400, content={"error": "message required"})

    def event_stream() -> Iterable[str]:
        full_text_parts: list[str] = []

        try:
            report_context: str | None = None
            metadata = getattr(conversation, "metadata_", None) or {}
            report_id_raw = metadata.get("reportId")
            if report_id_raw is not None:
                try:
                    report_id = int(str(report_id_raw))
                    embedder = _make_embedder()
                    query_vec = embedder.embed_query(user_message)
                    matches = search_report_embeddings_by_cosine_distance(
                        report_id=report_id,
                        query_embedding=query_vec,
                        top_k=6,
                    )
                    report_context = _format_report_context([m.text for m in matches])
                except Exception as e:
                    logger.warning("RAG retrieval failed: %s", e)

            llm = _make_llm()
            msgs = _build_messages(
                report_context=report_context,
                history=list(conversation.messages or []),
                user_message=user_message,
            )

            yield _sse_data({"type": "start"})

            for chunk in llm.stream(msgs):
                token = getattr(chunk, "content", None)
                if not token:
                    continue
                full_text_parts.append(token)
                yield _sse_data({"type": "token", "token": token})

            full_text = "".join(full_text_parts)
            append_conversation_message_pair(
                conversation_id=conversation_id,
                user_content=user_message,
                ai_content=full_text,
            )
            yield _sse_data({"type": "end"})
        except Exception as e:
            logger.exception("Chat streaming failed")
            yield _sse_data({"type": "error", "error": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
