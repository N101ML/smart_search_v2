from fastapi import APIRouter, Depends, Query
from typing import Annotated
from backend.dependencies import get_openai_service
from backend.services.openai_service import OpenAIService

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/openai/{model}/{user_message}", response_model=str)
async def chat(
  model: str,
  user_message: str,
  system_prompt: Annotated[str | None, Query()] = None,
  openai_service: OpenAIService = Depends(get_openai_service)
):
  prompt = system_prompt if system_prompt else "You are a helpful assistant"
  return await openai_service.chat(user_message, model, system_prompt if system_prompt else "You are a helpful assistant")