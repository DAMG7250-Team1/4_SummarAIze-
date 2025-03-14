import boto3
from botocore.exceptions import ClientError
import logging
from config import get_settings
from typing import Optional, BinaryIO
from pathlib import Path
import os

settings = get_settings()
logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client('s3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        logger.info(f"Initialized S3 service with bucket: {self.bucket_name}")

    def upload_file(self, file_path: str, s3_key: str) -> str:
        try:
            logger.info(f"Uploading {file_path} to S3 bucket {self.bucket_name} with key {s3_key}")
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            url = self.generate_presigned_url(s3_key)
            logger.info(f"Successfully uploaded file. Generated URL: {url}")
            return url
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
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

    def generate_presigned_url(self, s3_key: str) -> str:
        try:
            url = self.s3_client.generate_presigned_url('get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=3600
            )
            return url
        except Exception as e:
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