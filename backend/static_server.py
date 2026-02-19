"""
Static file serving for PharmaGuard frontend.
Serves the single-page HTML frontend from the /static directory.
"""
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(__file__).parent.parent / "frontend_static"


def mount_frontend(app):
    """Mount the static frontend if the directory exists."""
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(str(FRONTEND_DIR / "index.html"))
