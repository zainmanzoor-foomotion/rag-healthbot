from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from rag_healthbot_server.config import settings
from rag_healthbot_server.routers.report import router as report_router
from rag_healthbot_server.routers.conversations import router as conversations_router
from rag_healthbot_server.routers.chat import router as chat_router
from rag_healthbot_server.routers.review import router as review_router
from rag_healthbot_server.utilities.icd10_lookup import set_icd10_file
from rag_healthbot_server.utilities.cpt_lookup import set_cpt_file


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load local code files if configured
    if settings.icd10_file:
        set_icd10_file(settings.icd10_file)
    if settings.cpt_file:
        set_cpt_file(settings.cpt_file)
    yield


class _DBSessionMiddleware(BaseHTTPMiddleware):
    """Remove the scoped SQLAlchemy session after each request.

    Without this, thread-pool threads keep their session open indefinitely,
    eventually exhausting the connection pool.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        finally:
            from rag_healthbot_server.db import remove_session

            remove_session()


app = FastAPI(lifespan=lifespan)

app.add_middleware(_DBSessionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")
api_router.include_router(report_router)
api_router.include_router(conversations_router)
api_router.include_router(chat_router)
api_router.include_router(review_router)

app.include_router(api_router)
