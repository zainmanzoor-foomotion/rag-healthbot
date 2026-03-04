from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .config import settings


def _import_models() -> None:
    from rag_healthbot_server.Models import (
        Conversation,
        Disease,
        Medication,
        Procedure,
        Report,
        ReportDisease,
        ReportEmbedding,
        ReportMedication,
        ReportProcedure,
    )


engine = create_engine(url=settings.database_url, echo=True)
Session = sessionmaker(bind=engine)
# scoped_session provides a thread-local session registry so that concurrent
# requests (each handled in their own thread by Uvicorn/Starlette) each get
# an independent SQLAlchemy session instead of sharing a single global one.
session = scoped_session(Session)


def remove_session() -> None:
    """Remove the current thread's session from the registry.

    Call this at the end of every request so the thread-local session is
    returned to the pool rather than staying open indefinitely.
    """
    session.remove()


_import_models()
