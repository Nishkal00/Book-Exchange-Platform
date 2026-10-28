from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.auth import router as auth_router

from app.config import get_settings

app = FastAPI(title="Book Exchange Platform API", version="0.1.0")
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness probe used by CI, Docker Compose and the uptime monitor (SR-003 / NF-002)."""
    return {"status": "ok"}
