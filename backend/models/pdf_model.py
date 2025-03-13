from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PDFContent(BaseModel):
    """Model for storing PDF content and metadata."""
    filename: str
    content: Optional[str] = None
    pages: Optional[List[str]] = None
    created_at: datetime = datetime.now()
    file_path: Optional[str] = None
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
    model: str = "gpt-4"
    s3_url: Optional[str] = None

class SummaryRequest(BaseModel):
    """Model for summarization request."""
    filename: str
    model: str = "gpt-4"
    max_length: int = 1000
    s3_url: Optional[str] = None

class PDFListItem(BaseModel):
    filename: str
    url: Optional[str] = None
    max_length: Optional[int] = 1000 