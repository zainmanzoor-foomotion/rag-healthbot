from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from rag_healthbot_server.routers.report import router as report_router
from rag_healthbot_server.routers.conversations import router as conversations_router
from rag_healthbot_server.routers.chat import router as chat_router

app = FastAPI()

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

app.include_router(api_router)
