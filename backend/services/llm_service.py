from typing import Dict, List, Optional
import logging
from litellm import completion
from services.pdf_service import pdf_service
from models.pdf_model import PDFContent
from config import get_settings
import litellm
import os

logger = logging.getLogger(__name__)
settings = get_settings()

# Debug logging for API key configuration
logger.info("Configuring LLM service...")

# Model mappings with explicit API keys
MODEL_MAPPINGS = {
    "gpt-4": {
        "provider": "together",
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "api_key": settings.OPENAI_API_KEY
    },
    "gemini-pro": {
        "provider": "google",
        "model": "gemini-pro",
        "api_key": settings.GOOGLE_API_KEY
    },
    "claude-3": {
        "provider": "anthropic",
        "model": "claude-3-opus-20240229",
        "api_key": settings.ANTHROPIC_API_KEY
    },
    "deepseek-chat": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "api_key": settings.DEEPSEEK_API_KEY
    },
    "grok-1": {
        "provider": "grok",
        "model": "grok-1",
        "api_key": settings.GROK_API_KEY
    }
}

class LLMService:
    def __init__(self):
        self.chunk_overlap = 200  # characters of overlap between chunks

    async def generate_summary(self, filename: str, model: str, max_length: int = 1000) -> Dict:
        """Generate a summary of the PDF content."""
        try:
            pdf_content = await pdf_service.get_pdf_content(filename)
            if not pdf_content:
                raise ValueError(f"PDF {filename} not found")

            # Create prompt for summarization
            prompt = self._create_summary_prompt(pdf_content.content, max_length)
            
            # Get model configuration
            model_config = MODEL_MAPPINGS.get(model, MODEL_MAPPINGS["gpt-4"])
            
            # Ensure we have an API key
            if not model_config["api_key"]:
                raise ValueError(f"No API key configured for model {model}")
            
            # Generate summary using LLM
            response = await completion(
                model=model_config["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_length,
                api_key=model_config["api_key"]
            )

            return {
                "summary": response.choices[0].message.content,
                "usage": response.usage
            }

        except Exception as e:
            logger.error(f"Error generating summary for {filename}: {str(e)}")
            raise

    async def answer_question(self, filename: str, question: str, model: str) -> Dict:
        """Answer a question about the PDF content."""
        try:
            pdf_content = await pdf_service.get_pdf_content(filename)
            if not pdf_content:
                raise ValueError(f"PDF {filename} not found")

            # Find relevant chunks for the question
            relevant_chunks = self._find_relevant_chunks(pdf_content.chunks, question)
            
            # Create prompt for question answering
            prompt = self._create_qa_prompt(question, relevant_chunks)
            
            # Get model configuration
            model_config = MODEL_MAPPINGS.get(model, MODEL_MAPPINGS["gpt-4"])
            
            # Ensure we have an API key
            if not model_config["api_key"]:
                raise ValueError(f"No API key configured for model {model}")
            
            # Generate answer using LLM
            response = await completion(
                model=model_config["model"],
                messages=[{"role": "user", "content": prompt}],
                api_key=model_config["api_key"]
            )

            return {
                "answer": response.choices[0].message.content,
                "usage": response.usage
            }

        except Exception as e:
            logger.error(f"Error answering question for {filename}: {str(e)}")
            raise

    def _create_summary_prompt(self, content: str, max_length: int) -> str:
        """Create a prompt for summarization."""
        return f"""Please provide a clear and concise summary of the following text. 
The summary should be no longer than {max_length} words and should capture the main points and key information:

{content}

Summary:"""

    def _create_qa_prompt(self, question: str, context: List[str]) -> str:
        """Create a prompt for question answering."""
        context_text = "\n".join(context)
        return f"""Based on the following context, please answer the question accurately and concisely. 
If the answer cannot be found in the context, please say so.

Context:
{context_text}

Question: {question}

Answer:"""

    def _find_relevant_chunks(self, chunks: List[str], question: str) -> List[str]:
        """Find chunks most relevant to the question."""
        # For now, return all chunks. In a production system,
        # you would implement semantic search or similarity matching here.
        return chunks

llm_service = LLMService() 