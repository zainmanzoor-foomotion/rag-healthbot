# server

A project created with FastAPI CLI.

## Quick Start

### Start the development server

```bash
uv run fastapi dev
```

Visit http://localhost:8000

### Deploy to FastAPI Cloud

> FastAPI Cloud is currently in private beta. Join the waitlist at https://fastapicloud.com

```bash
uv run fastapi login
uv run fastapi deploy
```

## Project Structure

- `main.py` - Your FastAPI application
- `pyproject.toml` - Project dependencies

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [FastAPI Cloud](https://fastapicloud.com)

## Model Contracts

{
"run_id": "uuid",
"agent_type": "booking_agent",
"intent": "book_meeting",
"input": {
"user_request": "Book a call with sales tomorrow at 3pm",
"extracted_entities": {
"date": "2026-01-09",
"time": "15:00",
"department": "sales"
}
},
"constraints": {
"max_tool_calls": 3,
"timeout_ms": 5000
},
"schema_version": "1.0"
}
