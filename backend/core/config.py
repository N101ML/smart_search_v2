import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
  OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
  REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
  REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
  REDDIT_USER_AGENT = os.environ["REDDIT_USER_AGENT"]

  DB_USER = os.environ["PG_USER"]
  DB_PASSWORD = os.environ["PG_PASSWORD"]
  DB_HOST = os.environ["PG_HOST"]
  DB_PORT = os.environ["PG_PORT"]
  DB_NAME = os.environ["PG_DATABASE"]

  DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

  # Redis configuration
  REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

  # CORS origins
  ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(',')