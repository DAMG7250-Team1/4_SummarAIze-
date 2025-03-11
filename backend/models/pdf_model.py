from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PDFContent(BaseModel):
    """Model for storing PDF content and metadata."""
    filename: str
    content: str
    pages: int
    created_at: datetime = datetime.now()
    file_path: str
    s3_url: Optional[str] = None
    chunks: Optional[List[str]] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class PDFResponse(BaseModel):
    """Model for PDF processing response."""
    filename: str
    message: str
    success: bool
    error: Optional[str] = None
    s3_url: Optional[str] = None

class QuestionRequest(BaseModel):
    """Model for question answering request."""
    filename: str
    question: str
    model: str

class SummaryRequest(BaseModel):
    """Model for summarization request."""
    filename: str
    model: str
    max_length: Optional[int] = 1000 