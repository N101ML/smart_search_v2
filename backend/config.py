import os
from dotenv import load_dotenv

# Explicitly load the .env file from the backend directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

class Config:
  OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
  REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
  REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
  REDDIT_USER_AGENT = os.environ["REDDIT_USER_AGENT"]