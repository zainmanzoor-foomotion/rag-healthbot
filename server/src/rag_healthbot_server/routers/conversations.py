from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rag_healthbot_server.Models.Conversation import IConversation
from rag_healthbot_server.services.db.ConversationRepo import (
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)
from rag_healthbot_server.services.db.ReportRepo import get_report
from rag_healthbot_server.services.db.ReportEmbeddingRepo import list_report_embeddings
from rag_healthbot_server.services.agents.embeddings_agent import (
    IEmbeddingsAgentInput,
    IInputData as EmbeddingsInputData,
    run_embeddings_agent,
)

import uuid

router = APIRouter(prefix="/conversations", tags=["conversations"])


class MessageOut(BaseModel):
    userContent: str | None = None
    aiContent: str | None = None


class ConversationDoc(BaseModel):
    # Match Mongoose JSON shape used by the client.
    # Pydantic v2 treats underscore-prefixed fields as private, so we use
    # a regular field name with a serialization alias.
    model_config = {"populate_by_name": True}

    id: str = Field(serialization_alias="_id")
    title: str
    messages: list[MessageOut] = []
    metadata: dict[str, object] = {}

    createdAt: datetime
    updatedAt: datetime


class CreateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1)


class DeleteConversationResponse(BaseModel):
    message: str
    id: str


class CreateConversationFromReportRequest(BaseModel):
    reportId: str = Field(..., min_length=1)


class CreateConversationFromReportResponse(BaseModel):
    id: str


def _to_doc(c) -> dict:
    """Return a plain dict matching the Mongoose-like JSON shape the client expects."""
    doc = ConversationDoc(
        id=str(c.id),
        title=c.title,
        messages=[MessageOut(**m) for m in (c.messages or [])],
        metadata=getattr(c, "metadata_", None) or {},
        createdAt=c.created_at,
        updatedAt=c.updated_at,
    )
    return doc.model_dump(by_alias=True, mode="json")


@router.get("")
def get_conversations():
    try:
        conversations = list_conversations()
        return JSONResponse(content=[_to_doc(c) for c in conversations])
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch chats"},
        )


@router.post("", status_code=201)
def post_conversation(payload: CreateConversationRequest):
    if not payload.title:
        return JSONResponse(status_code=400, content={"error": "Title is required"})

    try:
        conv = create_conversation(
            IConversation(
                title=payload.title,
                messages=[],
                metadata={},
            )
        )
        return JSONResponse(content=_to_doc(conv), status_code=201)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"},
        )


@router.post(
    "/from-report",
    response_model=CreateConversationFromReportResponse,
    status_code=200,
)
def post_conversation_from_report(payload: CreateConversationFromReportRequest):
    try:
        report_id = int(payload.reportId)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "reportId required"})

    report = get_report(report_id)
    if report is None:
        return JSONResponse(status_code=404, content={"error": "not found"})

    extracted_text = (report.extracted_text or "").strip()
    if len(extracted_text) < 20:
        return JSONResponse(
            status_code=400, content={"error": "no text available for embeddings"}
        )

    try:
        existing = list_report_embeddings(report_id)
        if not existing:
            run_embeddings_agent(
                IEmbeddingsAgentInput(
                    rund_id=str(uuid.uuid4()),
                    input=EmbeddingsInputData(texts=[extracted_text]),
                    constraints={"report_id": report_id},
                )
            )
    except Exception:
        return JSONResponse(status_code=500, content={"error": "server"})

    try:
        conv = create_conversation(
            IConversation(
                title=f"Chat — {report.file_name or 'Report'}",
                messages=[],
                metadata={"reportId": str(report_id)},
            )
        )
        return CreateConversationFromReportResponse(id=str(conv.id))
    except Exception:
        return JSONResponse(status_code=500, content={"error": "server"})


@router.delete("/{id}", response_model=DeleteConversationResponse)
def delete_conversation_by_id(id: str):
    if not id:
        return JSONResponse(
            status_code=400,
            content={"error": "Conversation ID is required"},
        )

    try:
        conv_id = int(id)
    except Exception:
        # In Mongo this would be a 24-char ObjectId; keep behavior roughly similar.
        return JSONResponse(
            status_code=404, content={"error": "Conversation not found"}
        )

    deleted = delete_conversation(conv_id)
    if not deleted:
        return JSONResponse(
            status_code=404, content={"error": "Conversation not found"}
        )

    return DeleteConversationResponse(
        message="Conversation deleted successfully",
        id=id,
    )


@router.get("/{id}")
def get_conversation_by_id(id: str):
    if not id:
        return JSONResponse(
            status_code=400,
            content={"error": "Conversation ID is required"},
        )

    try:
        conv_id = int(id)
    except Exception:
        return JSONResponse(
            status_code=404, content={"error": "Conversation not found"}
        )

    conv = get_conversation(conv_id)
    if conv is None:
        return JSONResponse(
            status_code=404, content={"error": "Conversation not found"}
        )

    return JSONResponse(content=_to_doc(conv))
