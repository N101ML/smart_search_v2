import redis.asyncio as aioreddis
from backend.core.config import Config
from backend.services.reddit_service import RedditService
from backend.services.openai_service import OpenAIService

async def get_reddit_service() -> RedditService:
  redis_client = aioreddis.from_url(Config.REDIS_URL)
  return RedditService(redis_client)

async def get_openai_service() -> OpenAIService:
  return OpenAIService()