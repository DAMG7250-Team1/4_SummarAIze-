from fastapi import APIRouter, HTTPException
from typing import Dict
import logging
from models.pdf_model import QuestionRequest, SummaryRequest
from models.llm_model import QuestionResponse, SummaryResponse
from services.pdf_service import pdf_service
from services.llm_service import llm_service
from redis_client import redis_client
import json
import litellm
import openai
import requests
from config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

settings = get_settings()

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate the cost of API usage based on token counts."""
    # Define pricing for different models (per 1000 tokens)
    pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gemini-pro": {"input": 0.00125, "output": 0.00375},
        "claude-3": {"input": 0.015, "output": 0.075},
        "deepseek-chat": {"input": 0.0005, "output": 0.0015},
        "grok-1": {"input": 0.0005, "output": 0.0015},
    }
    
    # Get pricing for the model or use default pricing
    model_pricing = pricing.get(model, {"input": 0.01, "output": 0.02})
    
    # Calculate cost
    input_cost = (input_tokens / 1000) * model_pricing["input"]
    output_cost = (output_tokens / 1000) * model_pricing["output"]
    
    return input_cost + output_cost

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_pdf(request: SummaryRequest):
    """Generate a summary of a PDF."""
    try:
        # Get PDF content
        pdf_content = await pdf_service.get_pdf_content(request.filename, s3_url=request.s3_url if hasattr(request, 's3_url') else None)
        if not pdf_content:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Extract the content string from the dictionary
        content_text = pdf_content.get("content", "")
        if not content_text:
            raise HTTPException(status_code=400, detail="PDF content is empty")
        
        # Generate summary using the selected model
        prompt = f"""Please summarize the following text in a concise manner, 
        not exceeding {request.max_length} characters:
        
        {content_text}
        
        Summary:"""
        
        # Use the appropriate model
        model = request.model
        available_models = ["gpt-3.5-turbo", "gemini-pro"]  # Currently available models
        
        # Try the selected model first, then fall back to other available models if needed
        summary = None
        input_tokens = 0
        output_tokens = 0
        used_model = None
        
        # If the selected model is not available, try to use an available one
        if model not in available_models:
            logger.warning(f"Model {model} not available. Will try available models.")
            models_to_try = available_models
        else:
            models_to_try = [model] + [m for m in available_models if m != model]
        
        # Try each model in order until one works
        for try_model in models_to_try:
            try:
                logger.info(f"Attempting to use model: {try_model}")
                
                if try_model == "gpt-3.5-turbo":
                    # Use OpenAI
                    client = openai.OpenAI()
                    response = client.chat.completions.create(
                        model=try_model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=request.max_length // 4
                    )
                    summary = response.choices[0].message.content
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    used_model = try_model
                    break
                    
                elif try_model == "gemini-pro":
                    try:
                        # First try the Python client
                        import google.generativeai as genai
                        
                        logger.info(f"Using API key from settings: {settings.GOOGLE_API_KEY[:5]}...{settings.GOOGLE_API_KEY[-5:] if len(settings.GOOGLE_API_KEY) > 10 else ''}")
                        
                        # Configure the Gemini API
                        genai.configure(api_key=settings.GOOGLE_API_KEY)
                        logger.info("Successfully configured Google Generative AI API")
                        
                        # Try different model names
                        model_names = ["gemini-pro", "gemini-1.0-pro", "gemini-2.0-flash"]
                        gemini_success = False
                        
                        for model_name in model_names:
                            try:
                                logger.info(f"Trying Gemini model name: {model_name}")
                                model = genai.GenerativeModel(model_name=model_name)
                                response = model.generate_content(prompt)
                                summary = response.text
                                logger.info(f"Successfully generated content with Gemini model: {model_name}")
                                input_tokens = len(prompt) // 4  # Rough estimate
                                output_tokens = len(summary) // 4  # Rough estimate
                                used_model = try_model
                                gemini_success = True
                                break
                            except Exception as model_name_error:
                                logger.error(f"Error with Gemini model name {model_name}: {str(model_name_error)}")
                        
                        if gemini_success:
                            break
                            
                        # If Python client fails, try REST API directly
                        if not gemini_success:
                            logger.info("Trying Gemini REST API directly")
                            import requests
                            import json
                            
                            api_key = settings.GOOGLE_API_KEY
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                            
                            headers = {
                                "Content-Type": "application/json"
                            }
                            
                            data = {
                                "contents": [
                                    {
                                        "parts": [
                                            {
                                                "text": prompt
                                            }
                                        ]
                                    }
                                ],
                                "generationConfig": {
                                    "temperature": 0.7,
                                    "topP": 0.95,
                                    "topK": 40,
                                    "maxOutputTokens": request.max_length // 4
                                }
                            }
                            
                            response = requests.post(url, headers=headers, data=json.dumps(data))
                            logger.info(f"Gemini REST API response status: {response.status_code}")
                            
                            if response.status_code == 200:
                                result = response.json()
                                logger.info("Successfully parsed Gemini REST API response")
                                summary = result["candidates"][0]["content"]["parts"][0]["text"]
                                # Estimate tokens
                                input_tokens = len(prompt) // 4
                                output_tokens = len(summary) // 4
                                used_model = try_model
                                break
                            else:
                                logger.error(f"Gemini REST API error: {response.status_code} - {response.text}")
                                continue
                            
                    except ImportError:
                        logger.error("Google Generative AI package not installed. Run: pip install google-generativeai")
                        continue
                    except Exception as gemini_error:
                        logger.error(f"Error using Gemini model: {str(gemini_error)}")
                        logger.exception(gemini_error)  # Log the full traceback
                        continue
            
            except Exception as model_error:
                logger.warning(f"Error using model {try_model}: {str(model_error)}")
                continue
        
        # If no model worked, raise an error
        if summary is None:
            raise HTTPException(
                status_code=503, 
                detail="All available language models failed. Please try again later."
            )
        
        # Calculate cost based on model
        cost = calculate_cost(used_model, input_tokens, output_tokens)
        
        # Return response
        return SummaryResponse(
            filename=request.filename,
            summary=summary,
            model=used_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error summarizing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Answer a question about a PDF."""
    try:
        # Get PDF content
        pdf_content = await pdf_service.get_pdf_content(request.filename, s3_url=request.s3_url if hasattr(request, 's3_url') else None)
        if not pdf_content:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Extract the content string from the dictionary
        content_text = pdf_content.get("content", "")
        if not content_text:
            raise HTTPException(status_code=400, detail="PDF content is empty")
        
        # Create prompt for question answering
        prompt = f"""Please answer the following question based only on the provided content.
        If the answer cannot be found in the content, state that clearly.
        
        Content:
        {content_text}
        
        Question: {request.question}
        
        Answer:"""
        
        # Use the appropriate model
        model = request.model
        available_models = ["gpt-3.5-turbo", "gemini-pro"]  # Currently available models
        
        # Try the selected model first, then fall back to other available models if needed
        answer = None
        input_tokens = 0
        output_tokens = 0
        used_model = None
        
        # If the selected model is not available, try to use an available one
        if model not in available_models:
            logger.warning(f"Model {model} not available. Will try available models.")
            models_to_try = available_models
        else:
            models_to_try = [model] + [m for m in available_models if m != model]
        
        # Try each model in order until one works
        for try_model in models_to_try:
            try:
                logger.info(f"Attempting to use model: {try_model}")
                
                if try_model == "gpt-3.5-turbo":
                    # Use OpenAI
                    client = openai.OpenAI()
                    response = client.chat.completions.create(
                        model=try_model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500  # Reasonable limit for answers
                    )
                    answer = response.choices[0].message.content
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    used_model = try_model
                    break
                    
                elif try_model == "gemini-pro":
                    try:
                        # First try the Python client
                        import google.generativeai as genai
                        
                        logger.info(f"Using API key from settings: {settings.GOOGLE_API_KEY[:5]}...{settings.GOOGLE_API_KEY[-5:] if len(settings.GOOGLE_API_KEY) > 10 else ''}")
                        
                        # Configure the Gemini API
                        genai.configure(api_key=settings.GOOGLE_API_KEY)
                        logger.info("Successfully configured Google Generative AI API")
                        
                        # Try different model names
                        model_names = ["gemini-pro", "gemini-1.0-pro", "gemini-2.0-flash"]
                        gemini_success = False
                        
                        for model_name in model_names:
                            try:
                                logger.info(f"Trying Gemini model name: {model_name}")
                                model = genai.GenerativeModel(model_name=model_name)
                                response = model.generate_content(prompt)
                                answer = response.text
                                logger.info(f"Successfully generated content with Gemini model: {model_name}")
                                input_tokens = len(prompt) // 4  # Rough estimate
                                output_tokens = len(answer) // 4  # Rough estimate
                                used_model = try_model
                                gemini_success = True
                                break
                            except Exception as model_name_error:
                                logger.error(f"Error with Gemini model name {model_name}: {str(model_name_error)}")
                        
                        if gemini_success:
                            break
                            
                        # If Python client fails, try REST API directly
                        if not gemini_success:
                            logger.info("Trying Gemini REST API directly")
                            import requests
                            import json
                            
                            api_key = settings.GOOGLE_API_KEY
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                            
                            headers = {
                                "Content-Type": "application/json"
                            }
                            
                            data = {
                                "contents": [
                                    {
                                        "parts": [
                                            {
                                                "text": prompt
                                            }
                                        ]
                                    }
                                ],
                                "generationConfig": {
                                    "temperature": 0.7,
                                    "topP": 0.95,
                                    "topK": 40,
                                    "maxOutputTokens": 500
                                }
                            }
                            
                            response = requests.post(url, headers=headers, data=json.dumps(data))
                            logger.info(f"Gemini REST API response status: {response.status_code}")
                            
                            if response.status_code == 200:
                                result = response.json()
                                logger.info("Successfully parsed Gemini REST API response")
                                answer = result["candidates"][0]["content"]["parts"][0]["text"]
                                # Estimate tokens
                                input_tokens = len(prompt) // 4
                                output_tokens = len(answer) // 4
                                used_model = try_model
                                break
                            else:
                                logger.error(f"Gemini REST API error: {response.status_code} - {response.text}")
                                continue
                            
                    except ImportError:
                        logger.error("Google Generative AI package not installed. Run: pip install google-generativeai")
                        continue
                    except Exception as gemini_error:
                        logger.error(f"Error using Gemini model: {str(gemini_error)}")
                        logger.exception(gemini_error)  # Log the full traceback
                        continue
            
            except Exception as model_error:
                logger.warning(f"Error using model {try_model}: {str(model_error)}")
                continue
        
        # If no model worked, raise an error
        if answer is None:
            raise HTTPException(
                status_code=503, 
                detail="All available language models failed. Please try again later."
            )
        
        # Calculate cost based on model
        cost = calculate_cost(used_model, input_tokens, output_tokens)
        
        # Return response
        return QuestionResponse(
            filename=request.filename,
            question=request.question,
            answer=answer,
            model=used_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 