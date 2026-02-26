from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings


def _import_models() -> None:
    from rag_healthbot_server.Models import (
        Conversation,
        Medication,
        Report,
        ReportEmbedding,
        ReportMedication,
    )


engine = create_engine(url=settings.database_url, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

_import_models()
