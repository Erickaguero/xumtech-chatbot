from __future__ import annotations
from typing import Literal, List, Optional
from pydantic import BaseModel, Field


class FAQOut(BaseModel):
    id: int
    question: str


class FAQIn(BaseModel):
    question: str = Field(min_length=5)
    answer: str = Field(min_length=5)
    tags: Optional[List[str]] = None


class QueryIn(BaseModel):
    message: str = Field(min_length=1)


class QueryOut(BaseModel):
    answer: Optional[str] = None
    confidence: float
    matched_question: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)
    status: Literal["understood", "ambiguous", "not_understood"]