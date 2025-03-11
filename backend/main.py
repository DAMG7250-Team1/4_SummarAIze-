from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routes import pdf_routes, llm_routes

app = FastAPI(
    title="LLM PDF Processing API",
    description="API for processing PDFs with various LLM models",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdf_routes.router, prefix="/api/pdf", tags=["PDF Operations"])
app.include_router(llm_routes.router, prefix="/api/llm", tags=["LLM Operations"])

@app.get("/")
async def root():
    return {"message": "Welcome to LLM PDF Processing API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 