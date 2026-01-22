from fastapi import FastAPI, APIRouter

app = FastAPI()

api_router = APIRouter(prefix="/api")


@api_router.get("/report")
def main():
    return {"message": "Hello World"}


app.include_router(api_router)
