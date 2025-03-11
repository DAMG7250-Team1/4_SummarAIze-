from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
from services.pdf_service import pdf_service
from models.pdf_model import PDFResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=PDFResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file."""
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        contents = await file.read()
        pdf_content = await pdf_service.process_pdf(contents, file.filename)

        return PDFResponse(
            filename=pdf_content.filename,
            message="PDF processed successfully",
            success=True
        )

    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        return PDFResponse(
            filename=file.filename,
            message="Failed to process PDF",
            success=False,
            error=str(e)
        )

@router.get("/list", response_model=List[Dict])
async def list_pdfs():
    """List all processed PDFs."""
    try:
        return await pdf_service.list_pdfs()
    except Exception as e:
        logger.error(f"Error listing PDFs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/r")
async def get_pdf_content(filename: str):
    """Get processed PDF content."""
    try:
        pdf_content = await pdf_service.get_pdf_content(filename)
        if not pdf_content:
            raise HTTPException(status_code=404, detail="PDF not found")
        return pdf_content
    except Exception as e:
        logger.error(f"Error retrieving PDF content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 