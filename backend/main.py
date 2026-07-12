from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import game

app = FastAPI(title="Hexopolis API", version="0.1.0")

# Enable CORS for the frontend. Local dev origins are always allowed;
# a deployed frontend origin is added via ALLOWED_ORIGINS (comma-separated).
import os

_origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:3001", "http://127.0.0.1:3001",
]
_origins += [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include game routes
app.include_router(game.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"message": "Hexopolis API is running"}


@app.get("/health")
def health():
    """Health check for deployment."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
