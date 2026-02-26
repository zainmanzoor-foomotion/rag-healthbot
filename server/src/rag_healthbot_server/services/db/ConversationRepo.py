from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.Conversation import Conversation, IConversation

from pydantic import validate_call
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


@validate_call
def create_conversation(data: IConversation) -> Conversation:
    # Ensure we use the API alias `metadata` while mapping to ORM attribute `metadata_`.
    payload = data.model_dump(by_alias=True)
    if "metadata" in payload and "metadata_" not in payload:
        payload["metadata_"] = payload.pop("metadata")
    conversation = Conversation(**payload)
    try:
        db.session.add(conversation)
        db.session.commit()
        db.session.refresh(conversation)
        return conversation
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_conversation(conversation_id: int) -> Conversation | None:
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    return db.session.scalar(stmt)


def list_conversations() -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.created_at.desc())
    return list(db.session.scalars(stmt).all())


@validate_call
def delete_conversation(conversation_id: int) -> bool:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return False
    try:
        db.session.delete(conversation)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def append_conversation_message_pair(
    conversation_id: int,
    user_content: str,
    ai_content: str,
) -> Conversation | None:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return None

    messages = list(conversation.messages or [])
    messages.append(
        {
            "userContent": user_content,
            "aiContent": ai_content,
        }
    )
    conversation.messages = messages

    try:
        db.session.commit()
        db.session.refresh(conversation)
        return conversation
    except SQLAlchemyError:
        db.session.rollback()
        raise
