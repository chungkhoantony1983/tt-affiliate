"""
Local service for app.html — no database, Redis or video stack needed.

Run from the repo root:
  .venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.creator import router
from app.core.config import settings


class PrivateNetworkAccess:
    """Let the public HTTPS page reach this service on localhost in Chrome."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_with_header(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append(
                    (b"access-control-allow-private-network", b"true")
                )
            await send(message)

        await self.app(scope, receive, send_with_header)


app = FastAPI(title="TT Content Publisher local service", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CREATOR_WEB_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(PrivateNetworkAccess)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
