from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import uvicorn
from routes import pdf_routes, llm_routes
from services.stream_consumer import stream_consumer
from services.pdf_service import pdf_service
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

app = FastAPI(
    title="PDF Summarization API",
    description="API for uploading, summarizing, and querying PDFs using various LLMs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Streamlit app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdf_routes.router, prefix="/api/pdf", tags=["PDF Operations"])
app.include_router(llm_routes.router, prefix="/api/llm", tags=["LLM Operations"])

@app.get("/")
async def root():
    return {"message": "Welcome to the PDF Summarization API"}

@app.on_event("startup")
async def startup_event():
    # Start the stream consumer as a background task
    asyncio.create_task(stream_consumer.start())

@app.on_event("shutdown")
def shutdown_event():
    # Stop the stream consumer
    stream_consumer.stop()

@app.get("/s3-test")
async def test_s3_retrieval(filename: str):
    try:
        # Try to get the file directly from S3
        s3_key = f"pdfs/{filename}"  # Adjust path as needed
        response = pdf_service.s3_client.get_object(
            Bucket=pdf_service.bucket_name,
            Key=s3_key
        )
        return {
            "status": "success",
            "content_type": response['ContentType'],
            "content_length": response['ContentLength'],
            "s3_key": s3_key
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "s3_key": s3_key
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)