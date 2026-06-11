"""
FastAPI application entry point for ReArtFlow backend.
Includes the input, semantic, parse, and diagram routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .parse_endpoint import router as parse_router
from .routes.diagram import router as diagram_router
from .routes.input import router as input_router
from .routes.semantic import router as semantic_router

app = FastAPI(title="ReArtFlow Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(input_router)
app.include_router(semantic_router)
app.include_router(parse_router)
app.include_router(diagram_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
