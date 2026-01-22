def main():
    import uvicorn

    uvicorn.run(
        "rag_healthbot_server.main:app", host="localhost", port=8000, reload=True
    )
