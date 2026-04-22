"""Pydantic model representing a parsed source file.

The model mirrors the dictionary produced by ``parse_file`` and adds validation
against the schema used downstream.
"""

from pydantic import BaseModel, Field
from typing import Dict

class ParsedFile(BaseModel):
    path: str = Field(..., description="Absolute path to the source file")
    size: int = Field(..., ge=0, description="File size in bytes")
    mtime: float = Field(..., description="Last modification timestamp (seconds since epoch)")
    parse_time_ms: float = Field(..., ge=0, description="Parsing duration in milliseconds")
    language: str = Field(..., description="Detected programming language")
    ast_summary: Dict[str, int] = Field(
        ..., description="Lightweight summary of AST nodes (functions, classes, imports, calls)"
    )

    class Config:
        orm_mode = True

__all__ = ["ParsedFile"]
