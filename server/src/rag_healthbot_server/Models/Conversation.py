from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class IMessage(BaseModel):
    userContent: str | None = None
    aiContent: str | None = None


class IConversation(BaseModel):
    title: str
    messages: list[IMessage] = Field(default_factory=list)
    # SQLAlchemy reserves the attribute name `metadata`, so the ORM column uses
    # `metadata_` but the API/client uses `metadata`.
    metadata_: dict[str, object] = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(nullable=False)

    # Store the message list as JSON to match the existing client shape.
    # Each element is typically { userContent?: string, aiContent?: string }.
    messages: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Arbitrary per-conversation metadata (e.g. reportId, embeddingDim).
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(), onupdate=datetime.now()
    )
