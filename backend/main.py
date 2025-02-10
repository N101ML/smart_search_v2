# fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from backend.core.config import Config
from backend.core.logger import logger

from backend.api.endpoints.reddit import router as reddit_router
from backend.api.endpoints.chat import router as chat_router
from backend.api.endpoints.search import router as search_router

app = FastAPI(title="Smart-search")

app.add_middleware(
  CORSMiddleware,
  allow_origins=Config.ALLOWED_ORIGINS,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
  app.state.redis = aioredis.from_url(Config.REDIS_URL)
  logger.info("Application startup: Redis connection initialized.")

@app.on_event("shutdown")
async def shutdown_even():
  await app.state.redis.close()
  logger.info("Application shutdown: Redis connection closed.")

@app.get("/")
async def root():
  return {"message": "Hello Searchbot!"}

app.include_router(reddit_router)
app.include_router(chat_router)
app.include_router(search_router)