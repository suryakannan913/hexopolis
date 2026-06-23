from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import game

app = FastAPI(title="Hexopolis API", version="0.1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
