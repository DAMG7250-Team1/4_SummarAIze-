from fastapi import APIRouter, HTTPException
from models.pdf_model import QuestionRequest, SummaryRequest
from services.llm_service import llm_service
import logging
from litellm import AuthenticationError

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/summarize")
async def summarize_pdf(request: SummaryRequest):
    """Generate a summary of the PDF content."""
    try:
        return await llm_service.generate_summary(
            filename=request.filename,
            model=request.model,
            max_length=request.max_length
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail="Invalid API key or authentication error")
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
async def answer_question(request: QuestionRequest):
    """Answer a question about the PDF content."""
    try:
        return await llm_service.answer_question(
            filename=request.filename,
            question=request.question,
            model=request.model
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail="Invalid API key or authentication error")
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 