import PyPDF2
from pathlib import Path
from typing import List, Dict, Optional
import json
import logging
from models.pdf_model import PDFContent
from config import get_settings
from redis_client import redis_client
from services.s3_service import s3_service
import tempfile

settings = get_settings()
logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self):
        self.upload_dir = Path(settings.PDF_UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
        self.chunk_size = 1000  # characters per chunk

    async def process_pdf(self, file: bytes, filename: str) -> PDFContent:
        """Process PDF file and store its content."""
        try:
            # Create a temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file)
                temp_path = temp_file.name

            # Extract text content
            content = ""
            pages = 0
            with open(temp_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pages = len(pdf_reader.pages)
                for page in pdf_reader.pages:
                    content += page.extract_text()

            # Upload to S3
            s3_key = f"pdfs/{filename}"
            s3_url = await s3_service.upload_file(temp_path, s3_key)

            # Create chunks for processing
            chunks = self._create_chunks(content)

            # Create PDF content object
            pdf_content = PDFContent(
                filename=filename,
                content=content,
                pages=pages,
                file_path=s3_key,  # Store the S3 key instead of URL
                s3_url=s3_url,  # Store the presigned URL
                chunks=chunks
            )

            # Store in Redis
            await self._store_pdf_content(pdf_content)

            # Clean up temporary file
            Path(temp_path).unlink()

            return pdf_content

        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {str(e)}")
            raise

    def _create_chunks(self, content: str) -> List[str]:
        """Split content into chunks for processing."""
        words = content.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > self.chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    async def _store_pdf_content(self, pdf_content: PDFContent):
        """Store PDF content in Redis."""
        try:
            key = f"pdf:{pdf_content.filename}"
            data = pdf_content.model_dump_json()
            redis_client.redis_client.set(key, data)
        except Exception as e:
            logger.error(f"Error storing PDF content in Redis: {str(e)}")
            raise

    async def get_pdf_content(self, filename: str) -> Optional[PDFContent]:
        """Retrieve PDF content from Redis."""
        try:
            key = f"pdf:{filename}"
            data = redis_client.redis_client.get(key)
            if data:
                return PDFContent.model_validate_json(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving PDF content from Redis: {str(e)}")
            raise

    async def list_pdfs(self) -> List[Dict]:
        """List all processed PDFs."""
        try:
            pdfs = []
            for key in redis_client.redis_client.keys("pdf:*"):
                data = redis_client.redis_client.get(key)
                if data:
                    pdf_content = PDFContent.model_validate_json(data)
                    # Generate a fresh presigned URL
                    s3_url = await s3_service.get_file_url(pdf_content.filename)
                    pdfs.append({
                        "filename": pdf_content.filename,
                        "pages": pdf_content.pages,
                        "created_at": pdf_content.created_at.isoformat(),
                        "s3_url": s3_url
                    })
            return pdfs
        except Exception as e:
            logger.error(f"Error listing PDFs: {str(e)}")
            raise

    async def delete_pdf(self, filename: str) -> bool:
        """Delete PDF from both S3 and Redis."""
        try:
            # Delete from S3
            await s3_service.delete_file(filename)
            
            # Delete from Redis
            key = f"pdf:{filename}"
            redis_client.redis_client.delete(key)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting PDF {filename}: {str(e)}")
            return False

pdf_service = PDFService() 