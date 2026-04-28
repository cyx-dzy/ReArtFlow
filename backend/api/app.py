"""
FastAPI application entry point for ReArtFlow backend.
Includes the input, semantic, and diagram routers.
"""

from fastapi import FastAPI

# Import routers from sub-modules
from .routes.input import router as input_router
from .routes.semantic import router as semantic_router
from .routes.diagram import router as diagram_router

app = FastAPI(title="ReArtFlow Backend")

# Register routers under their respective prefixes (if needed)
app.include_router(input_router, prefix="/input")
app.include_router(semantic_router, prefix="/semantic")
app.include_router(diagram_router)

# Root endpoint for quick health check
@app.get("/health")
def health_check():
    return {"status": "ok"}
