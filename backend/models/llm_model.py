from pydantic import BaseModel
from typing import Optional

class SummaryResponse(BaseModel):
    """Model for summarization response."""
    filename: str
    summary: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float

class QuestionResponse(BaseModel):
    """Model for question answering response."""
    filename: str
    question: str
    answer: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float 