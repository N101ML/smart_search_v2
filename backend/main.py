from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
import logging
import redis.asyncio as aioredis
from fastapi.middleware.cors import CORSMiddleware
from backend.models.subreddit import Subreddit
from backend.models.submission import SubmissionCreate
from backend.models.comment import Comment
from backend.models.product_search_request import ProductSearchRequest
from backend.models.product import Product, ProductList, ProductWithScore
from backend.services.reddit_service import RedditService
from backend.services.openai_service import OpenAIService, SubjectPhrasesRequest
from backend.services.sentiment_analysis import SentimentAnalysis
from enum import Enum
from typing import Annotated, Dict, List, Optional, Tuple
from transformers import pipeline
import asyncio

# setup and config
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
  "http://localhost:3000"
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"]
)

DB_USER = os.environ["PG_USER"]
DB_PASSWORD = os.environ["PG_PASSWORD"]
DB_HOST = os.environ["PG_HOST"]
DB_PORT = os.environ["PG_PORT"]
DB_NAME = os.environ["PG_DATABASE"]

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_db_connection():
  try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Database connection successful")
    return conn
  except Exception as e:
    print(f"Error connecting to the database: {e}")
    raise

def chunk_list(first, chunk_size):
  for i in range(0, len(first), chunk_size):
    yield first[i:i + chunk_size]

async def get_reddit_service():
  redis = aioredis.from_url("redis://localhost")
  return RedditService(redis)

async def get_openai_service():
  return OpenAIService()

@app.on_event("startup")
async def startup():
  global redis
  redis = aioredis.from_url("redis://localhost:6379")


@app.get("/")
async def root():
  return {"message": "Hello Searchbot!"}

@app.get("/subreddits/{subreddit_name}", response_model=Subreddit)
async def subreddit_info(
  subreddit_name: str,
  reddit_service: RedditService = Depends(get_reddit_service)
):
  subreddit = await reddit_service.subreddit_info(subreddit_name)
  return subreddit

@app.get("/subreddits/{subreddit_name}/search/{search_term}", response_model=list[SubmissionCreate])
async def fetch_subreddit_submissions(
  subreddit_name: str,
  search_term: str,
  reddit_service: RedditService = Depends(get_reddit_service)
):
  submissions = await reddit_service.fetch_subreddit_submissions(subreddit_name, search_term)
  return submissions

@app.get("/submissions/{submission_id}/comments", response_model=list[Comment])
async def submission_comments(
  submission_id: str,
  reddit_service: RedditService = Depends(get_reddit_service)
):
  comments = await reddit_service.submission_comments(submission_id)
  return comments

## OpenAI Chat API

@app.get("/chat/openai/{model}/{user_message}", response_model=str)
async def chat(
  model: str,
  user_message: str,
  system_prompt: Annotated[str | None, Query()] = None,
  openai_service: OpenAIService = Depends(get_openai_service)
):
  return await openai_service.chat(user_message, model, system_prompt if system_prompt else "You are a helpful assistant")

@app.post("/search", response_model=ProductList)
async def search(
    search_request: ProductSearchRequest,
    reddit_service: RedditService = Depends(get_reddit_service),
    openai_service: OpenAIService = Depends(get_openai_service),
):
    try:
      ## Logger ##
      logger.info(f"Received search request: {search_request}")

      # returns list of comment objects
      top_comments = await reddit_service.fetch_top_submission_comments(search_request)
      logger.info(f"Fetched {len(top_comments)} top comments")


      ner_pipeline = pipeline("ner", grouped_entities=True, device=0) # initialize pipeline
      filtered_comments = await reddit_service.filter_comments(
          top_comments, ner_pipeline
      )
      logger.info(f"Filtered comments: {len(filtered_comments)}")

      # returns a list of Products
      products_list = await reddit_service.find_products_from_comments(filtered_comments, search_request.product_category)
      logger.info(f"Found products: {products_list}")

      # use query to find find subject phrases
      # returns SubjectPhrasesRequest object
      subject_phrases_request_obj = await openai_service.find_subject_phrases(search_request.product_category)
      logger.info(f"Subject phrases: {subject_phrases_request_obj}")

      cleaned_products_list = []
      # clean products_list against subject phrases - returns a list of Products
      for product in products_list:
        if product.brand_name in subject_phrases_request_obj.excluded_words or product.product_name in subject_phrases_request_obj.excluded_words:
          continue
        elif product.product_name.lower() == f"{search_request.product_category.lower()}":
          continue
        else:
          cleaned_products_list.append(product)
      logger.info(f"Cleaned products list: {cleaned_products_list}")


      sentiment_pipeline = pipeline(task="sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
      # sentiment results from comments
      sentiment_results = sentiment_pipeline([comment.body for comment in filtered_comments], truncation=True, max_length=512)
      logger.info(f"Sentiment results: {len(sentiment_results)}")

      product_sentiments: Dict[Tuple[str, str], List[float]] = {}
      for product in cleaned_products_list:
        product_sentiments[(product.brand_name, product.product_name)] = []

      for i, comment in enumerate(filtered_comments):
        for product in cleaned_products_list:
          if product.brand_name.lower() in comment.body.lower() or product.product_name.lower() in comment.body.lower():
            sentiment = sentiment_results[i]['label']
            score = sentiment_results[i]['score']
            if sentiment == 'POSITIVE':
              sentiment_score = score
            else:
              sentiment_score = -score
            
            product_sentiments[(product.brand_name, product.product_name)].append(sentiment_score)

      product_avg_sentiment: Dict[Tuple[str, str], float] = {}
      # unpack tuple key

      for (brand_name, product_name), scores in product_sentiments.items():
        try:
          product_avg_sentiment[(brand_name, product_name)] = sum(scores) / len(scores) if scores else 0
        except ZeroDivisionError:
          product_avg_sentiment[(brand_name, product_name)] = 0

      # returns a list of Product objects
      ranked_products = sorted(product_avg_sentiment.items(), key=lambda item: item[1], reverse=True)
      logger.info(f"Ranked Products: {ranked_products}")

      product_list_with_scores: List[ProductWithScore] = []
      for (brand_name, product_name), score in ranked_products:
        product = Product(brand_name=brand_name, product_name=product_name)
        product_with_score = ProductWithScore(product=product, score=score)
        product_list_with_scores.append(product_with_score)

      logger.info(f"Returning ProductList: {product_list_with_scores}")

      return ProductList(products=product_list_with_scores)
    
    except Exception as e:
      print(f"Error during search: {e}")
      raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")