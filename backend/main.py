# backend/main.py
"""FastAPI application entry point. Creates the FastAPI app and includes API routers.
Provides static file serving for the frontend UI.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Import routers
try:
    from backend.api.routes import router as api_router
except ImportError:
    api_router = None

app = FastAPI(title="ContractGuard API", version="0.1.0")

if api_router:
    app.include_router(api_router)

# Serve the frontend UI located in the "frontend" directory at the root URL.
# The "html=True" flag ensures that a request to '/' returns index.html automatically.
# Static file serving removed; use Streamlit for the frontend UI.

# Optional root endpoint (will be overridden by static file serving for '/').
@app.get("/")
async def root():
    return {"message": "ContractGuard API is running"}
