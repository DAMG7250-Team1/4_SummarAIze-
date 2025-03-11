import boto3
from botocore.exceptions import ClientError
import logging
from config import get_settings
from typing import Optional, BinaryIO
from pathlib import Path

settings = get_settings()
logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_file(self, file_path: str, object_name: str) -> str:
        """Upload a file to S3 bucket and return a presigned URL."""
        try:
            self.s3_client.upload_file(
                file_path, 
                self.bucket_name, 
                object_name,
                ExtraArgs={
                    'ContentType': 'application/pdf'
                }
            )
            # Generate a presigned URL that's valid for 7 days
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_name
                },
                ExpiresIn=604800  # 7 days in seconds
            )
            return url
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise

    async def download_file(self, object_name: str, file_path: str) -> bool:
        """Download a file from S3 bucket."""
        try:
            self.s3_client.download_file(self.bucket_name, object_name, file_path)
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            return False

    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from S3 bucket."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            return False

    async def generate_presigned_url(self, object_name: str, expiration=3600) -> str:
        """Generate a presigned URL for object download."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise

    async def get_file_url(self, filename: str) -> str:
        """Get a presigned URL for a file in S3."""
        s3_key = f"pdfs/{filename}"
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=604800  # 7 days in seconds
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise

s3_service = S3Service() 