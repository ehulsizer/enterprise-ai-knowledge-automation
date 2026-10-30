from typing import Literal
from pydantic import BaseModel, Field


class Customer(BaseModel):
    id: str
    name: str
    tier: str


class Order(BaseModel):
    id: str
    customer_id: str
    status: str
    expected_delivery: str


class Ticket(BaseModel):
    id: str
    customer_id: str
    priority: Literal['P1', 'P2', 'P3']
    status: Literal['open', 'closed']
    summary: str


class Query(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    top_k: int = Field(default=4, ge=1, le=10)


class Citation(BaseModel):
    id: str
    source: str
    page: int
    chunk: int
    text: str
    score: float


class Answer(BaseModel):
    answer: str
    route: str
    citations: list[Citation] = []
    operational_data: dict = {}
    tools: list[str] = []
    trace: list[str] = []
    warnings: list[str] = []
    embedding_mode: str
    generation_mode: str
