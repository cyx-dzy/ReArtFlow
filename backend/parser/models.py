"""Pydantic model representing a parsed source file."""

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


class ParsedFile(BaseModel):
    path: str = Field(..., description="Absolute path to the source file")
    size: int = Field(..., ge=0, description="File size in bytes")
    mtime: float = Field(..., description="Last modification timestamp (seconds since epoch)")
    parse_time_ms: float = Field(..., ge=0, description="Parsing duration in milliseconds")
    language: str = Field(..., description="Detected programming language")
    ast_summary: Dict[str, int] = Field(
        ..., description="AST summary of structural elements (functions, classes, imports, calls)"
    )

    model_config = ConfigDict(from_attributes=True)


__all__ = ["ParsedFile"]
