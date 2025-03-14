from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
from services.pdf_service import pdf_service
from models.pdf_model import PDFResponse, PDFContent, PDFListItem
import logging
import os
import requests
import boto3
from config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

settings = get_settings()

@router.post("/upload", response_model=PDFResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file."""
    try:
        # Save file temporarily
        temp_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Upload to S3
        s3_client = boto3.client('s3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        
        bucket_name = os.getenv('S3_BUCKET_NAME')
        s3_path = f"pdfs/{file.filename}"
        
        # Upload file to S3
        s3_client.upload_file(temp_path, bucket_name, s3_path)
        
        # Generate presigned URL
        s3_url = s3_client.generate_presigned_url('get_object',
            Params={'Bucket': bucket_name, 'Key': s3_path},
            ExpiresIn=3600  # URL valid for 1 hour
        )
        
        # Clean up temp file
        os.remove(temp_path)
        
        return PDFResponse(
            filename=file.filename,
            message="PDF processed successfully",
            success=True,
            s3_url=s3_url
        )
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return PDFResponse(
            filename=file.filename,
            message="Failed to process PDF",
            success=False,
            error=str(e)
        )

@router.get("/list", response_model=List[PDFListItem])
async def list_pdfs():
    """List all processed PDFs."""
    try:
        # Get list of PDFs from S3
        pdf_files = await pdf_service.list_pdfs()
        return pdf_files
    except Exception as e:
        logger.error(f"Error listing PDFs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/r")
async def get_pdf_content(filename: str):
    """Get the content of a processed PDF."""
    try:
        # First, try to get the PDF metadata to get the S3 URL
        pdfs = await pdf_service.list_pdfs()
        s3_url = None
        
        # Find the PDF in the list and get its S3 URL
        for pdf in pdfs:
            if pdf.get('filename') == f"pdfs/{filename}" or pdf.get('filename') == filename:
                s3_url = pdf.get('url')
                break
        
        if s3_url:
            logger.info(f"Found S3 URL for {filename}: {s3_url}")
        else:
            logger.warning(f"No S3 URL found for {filename}")
        
        # Get the PDF content using the S3 URL if available
        pdf_content = await pdf_service.get_pdf_content(filename, s3_url=s3_url)
        if not pdf_content:
            # Try with 'pdfs/' prefix
            pdf_content = await pdf_service.get_pdf_content(f"pdfs/{filename}", s3_url=s3_url)
            
        if not pdf_content:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Return just the content string, not the dictionary
        return pdf_content.get("content", "")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving PDF content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exists")
async def check_pdf_exists(filename: str):
    """Check if a PDF exists."""
    try:
        # First, check if the PDF is in the list
        pdfs = await pdf_service.list_pdfs()
        found = False
        s3_url = None
        
        for pdf in pdfs:
            if pdf.get('filename') == filename or pdf.get('filename').endswith(f"/{filename}"):
                found = True
                s3_url = pdf.get('url')
                break
        
        # Then, check if the file exists locally
        local_exists = False
        possible_paths = [
            os.path.join(pdf_service.pdf_storage_dir, filename),
            filename,
            os.path.join(".", filename),
            os.path.join("backend", pdf_service.pdf_storage_dir, filename)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                local_exists = True
                break
        
        # Check if the S3 URL is accessible
        s3_accessible = False
        if s3_url:
            try:
                response = requests.head(s3_url)
                s3_accessible = response.status_code == 200
            except Exception:
                s3_accessible = False
        
        return {
            "exists": found,
            "in_list": found,
            "local_exists": local_exists,
            "s3_url": s3_url,
            "s3_accessible": s3_accessible
        }
    except Exception as e:
        logger.error(f"Error checking PDF existence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/s3-list")
async def debug_s3_list():
    """Debug endpoint to list all files in the S3 bucket."""
    try:
        # Use the settings from get_settings()
        settings = get_settings()
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        response = s3_client.list_objects_v2(
            Bucket=settings.S3_BUCKET_NAME
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
        
        return {
            "bucket": settings.S3_BUCKET_NAME,
            "file_count": len(files),
            "files": files
        }
    except Exception as e:
        logger.error(f"Error listing S3 files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 