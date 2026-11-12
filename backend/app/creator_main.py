"""
Local service for app.html and the Studio review page (/studio) — no database, Redis or video stack needed.

Run from the repo root:
  .venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from app.api.creator import router
from app.api.studio import router as studio_router
from app.core.config import settings

STUDIO_PAGE = Path(__file__).resolve().parent / "web" / "studio.html"


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
# Studio (DR-0001): same-origin page for the operator. Its write endpoints need the X-Studio
# header, which is deliberately not in allow_headers above.
app.include_router(studio_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/studio")


@app.get("/studio", include_in_schema=False)
def studio_page():
    return FileResponse(STUDIO_PAGE, media_type="text/html", headers={"Cache-Control": "no-store"})
