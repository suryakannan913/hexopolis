from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Hexopolis API", version="0.1.0")


@app.get("/")
def root():
    """Health check endpoint."""
    return {"message": "Hexopolis API is running"}


@app.get("/docs")
def docs():
    """Redirect to Swagger UI."""
    return {"message": "Visit /docs for Swagger UI"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
