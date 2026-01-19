from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from src.config import settings

engine = create_engine(url=settings.database_url, echo=True)
Session = sessionmaker(bind=engine)
session = Session()


class Base(DeclarativeBase):
    pass
