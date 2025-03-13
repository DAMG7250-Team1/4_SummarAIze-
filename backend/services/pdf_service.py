import PyPDF2
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import logging
from models.pdf_model import PDFContent, PDFListItem
from config import get_settings
from redis_client import redis_client
from services.s3_service import s3_service
import tempfile
import boto3
import requests
import io
import os

settings = get_settings()
logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self):
        self.settings = get_settings()
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.settings.AWS_REGION
        )
        self.bucket_name = self.settings.S3_BUCKET_NAME
        self.upload_dir = Path(settings.PDF_UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
        self.chunk_size = 1000  # characters per chunk
        self.pdf_storage_dir = "pdfs"  # Default storage directory

    async def process_pdf(self, file: bytes, filename: str) -> PDFContent:
        """Process PDF file and store its content."""
        try:
            # Create a temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file)
                temp_path = temp_file.name

            # Extract text content
            content = ""
            page_texts = []  # Store text from each page
            with open(temp_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    content += page_text
                    page_texts.append(page_text)  # Add each page's text to the list

            # Upload to S3
            s3_key = f"pdfs/{filename}"
            s3_url = await s3_service.upload_file(temp_path, s3_key)

            # Create chunks for processing
            chunks = self._create_chunks(content)

            # Create PDF content object
            pdf_content = PDFContent(
                filename=filename,
                content=content,
                pages=page_texts,  # Use the list of page texts
                file_path=s3_key,
                s3_url=s3_url,
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
            redis_client.set(key, data)
        except Exception as e:
            logger.error(f"Error storing PDF content in Redis: {str(e)}")
            raise

    async def get_pdf_content(self, filename: str, s3_url: str = None) -> Optional[Dict[str, Any]]:
        """Get the content of a PDF file."""
        try:
            logger.info(f"Getting content for PDF: {filename}, S3 URL: {s3_url}")
            
            # First try to get from Redis cache
            try:
                key = f"pdf:{filename}"
                # Check if redis_client.get is a coroutine
                if hasattr(redis_client.get, "__await__"):
                    cached_content = await redis_client.get(key)
                else:
                    cached_content = redis_client.get(key)
                
                if cached_content:
                    pdf_data = json.loads(cached_content)
                    if 'content' in pdf_data:
                        logger.info(f"Found PDF content in Redis cache for {filename}")
                        return {"content": pdf_data['content']}
            except Exception as redis_error:
                logger.warning(f"Redis error: {str(redis_error)}")
            
            # If S3 URL is provided, try to download from S3
            if s3_url:
                try:
                    logger.info(f"Downloading PDF from S3 URL: {s3_url}")
                    response = requests.get(s3_url)
                    if response.status_code == 200:
                        # Process the PDF content
                        pdf_content = self._extract_text_from_pdf(io.BytesIO(response.content))
                        logger.info(f"Successfully extracted {len(pdf_content)} characters from PDF")
                        return {"content": pdf_content}
                    else:
                        logger.error(f"Failed to download PDF from S3 URL: {response.status_code}")
                except Exception as s3_error:
                    logger.error(f"Error downloading from S3 URL: {str(s3_error)}")
            
            # Try direct S3 download with different key formats
            s3_keys_to_try = [
                filename,
                f"pdfs/{filename}",
                f"{filename.replace(' ', '%20')}"
            ]
            
            for s3_key in s3_keys_to_try:
                try:
                    logger.info(f"Trying direct S3 download with key: {s3_key}")
                    pdf_bytes = await self.download_from_s3(s3_key)
                    if pdf_bytes:
                        pdf_content = self._extract_text_from_pdf(io.BytesIO(pdf_bytes))
                        logger.info(f"Successfully extracted {len(pdf_content)} characters from PDF")
                        return {"content": pdf_content}
                except Exception as s3_error:
                    logger.error(f"Error with direct S3 download: {str(s3_error)}")
            
            # If no S3 download worked, try local storage
            try:
                # Try different possible paths
                possible_paths = [
                    os.path.join(self.pdf_storage_dir, filename),
                    filename,
                    os.path.join(".", filename),
                    os.path.join("backend", self.pdf_storage_dir, filename),
                    os.path.join(str(self.upload_dir), filename)
                ]
                
                for path in possible_paths:
                    logger.info(f"Trying path: {path}")
                    if os.path.exists(path):
                        logger.info(f"Found PDF at path: {path}")
                        with open(path, 'rb') as f:
                            pdf_content = self._extract_text_from_pdf(f)
                        return {"content": pdf_content}
            except Exception as local_error:
                logger.error(f"Error reading local PDF: {str(local_error)}")
            
            # If we get here, the PDF was not found
            logger.error(f"PDF not found: {filename}")
            return None
        except Exception as e:
            logger.error(f"Error getting PDF content: {str(e)}")
            return None

    def _extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from a PDF file."""
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    async def list_pdfs(self) -> List[Dict[str, Any]]:
        """List all processed PDFs."""
        try:
            # Get PDFs from S3
            s3_pdfs = await self._list_s3_pdfs()
            
            # Get PDFs from local storage
            local_pdfs = await self._list_local_pdfs()
            
            # Combine the lists, avoiding duplicates
            all_pdfs = {}
            for pdf in s3_pdfs + local_pdfs:
                filename = pdf.get('filename')
                if filename not in all_pdfs:
                    all_pdfs[filename] = pdf
                else:
                    # If the PDF is in both lists, merge the information
                    all_pdfs[filename].update(pdf)
            
            return list(all_pdfs.values())
        except Exception as e:
            logger.error(f"Error listing PDFs: {str(e)}")
            return []

    async def delete_pdf(self, filename: str) -> bool:
        """Delete PDF from both S3 and Redis."""
        try:
            # Delete from S3
            await s3_service.delete_file(filename)
            
            # Delete from Redis
            key = f"pdf:{filename}"
            redis_client.delete(key)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting PDF {filename}: {str(e)}")
            return False

    async def get_pdf_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a PDF file."""
        try:
            # Get the list of PDFs
            pdfs = await self.list_pdfs()
            
            # Find the PDF in the list
            for pdf in pdfs:
                if pdf.get('filename') == filename or pdf.get('filename').endswith(f"/{filename}"):
                    return pdf
            
            return None
        except Exception as e:
            logger.error(f"Error getting PDF metadata: {str(e)}")
            return None

    async def _list_s3_pdfs(self) -> List[Dict[str, Any]]:
        """List PDFs stored in S3."""
        try:
            pdfs = []
            # List objects in the S3 bucket with the prefix 'pdfs/'
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='pdfs/'
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.pdf'):
                        # Generate a pre-signed URL for the PDF
                        url = self.s3_client.generate_presigned_url(
                            'get_object',
                            Params={
                                'Bucket': self.bucket_name,
                                'Key': key
                            },
                            ExpiresIn=3600  # URL expires in 1 hour
                        )
                        
                        pdfs.append({
                            'filename': key,
                            'url': url
                        })
            
            return pdfs
        except Exception as e:
            logger.error(f"Error listing S3 PDFs: {str(e)}")
            return []

    async def _list_local_pdfs(self) -> List[Dict[str, Any]]:
        """List PDFs stored locally."""
        try:
            pdfs = []
            # Check the upload directory for PDFs
            for path in self.upload_dir.glob('*.pdf'):
                pdfs.append({
                    'filename': path.name,
                    'url': None  # No URL for local files
                })
            
            return pdfs
        except Exception as e:
            logger.error(f"Error listing local PDFs: {str(e)}")
            return []

    async def download_from_s3(self, key: str) -> Optional[bytes]:
        """Download a file directly from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            return None

# Create a singleton instance
pdf_service = PDFService() 