import logging
import asyncpraw
import asyncio
import hashlib
import json
import re
import redis.asyncio as aioredis
from backend.models.comment import Comment
from backend.config import Config
from backend.models.subreddit import Subreddit
from backend.models.submission import SubmissionBase
from backend.models.product_search_request import ProductSearchRequest
from backend.models.product import Product, ProductList
from pydantic import ValidationError
from fastapi import HTTPException
from openai import OpenAI
from transformers import pipeline
from typing import List, Dict

logger = logging.getLogger(__name__)
openai = OpenAI(api_key=Config.OPENAI_API_KEY)

class RedditService:
  def __init__(self, redis: aioredis.Redis):
    # initialize redis
    self.redis = redis

    self.client = asyncpraw.Reddit(
      client_id=Config.REDDIT_CLIENT_ID,
      client_secret=Config.REDDIT_CLIENT_SECRET,
      user_agent=Config.REDDIT_USER_AGENT
      )
     
  async def filter_comments(self, comments: List[Comment], ner_pipeline) -> List[Comment]:
    """
    Filters comments based on NER, preserving nested structure.
    """
    filtered_comments = []
    for comment in comments:
      # send comment body to pipeline
      entities = ner_pipeline(comment.body)
      keep_comment = any(e["entity_group"] in ["ORG", "MISC"] for e in entities)

      filtered_replies = []
      # Check for 'replies' and dictionary type.  RECURSIVE CALL WITH self.
      if comment.replies:
        filtered_replies = await self.filter_comments(comment.replies, ner_pipeline)

      # Keep comment if it passes the filter OR has filtered replies
      if keep_comment or filtered_replies:
        if filtered_replies:
            comment.replies = filtered_replies
        else:
            comment.replies = [] # Remove 'replies' if it's empty
        filtered_comments.append(comment)

    return filtered_comments
    
  async def subreddit_info(self, subreddit_name: str) -> Subreddit:
    try:
      praw_subreddit = await self.client.subreddit(subreddit_name)
      await praw_subreddit.load()
      subreddit = Subreddit(
        id=praw_subreddit.id,
        name=praw_subreddit.display_name,
        display_name=praw_subreddit.display_name,
        created_utc=praw_subreddit.created_utc,
        subscribers=praw_subreddit.subscribers,
        over_18=praw_subreddit.over18
      )
      return subreddit
    except Exception as e:
      logger.error(f"Error fetching subreddit: {e}")
      raise HTTPException(status_code=404, detail="Subreddit not found") from e
  
  async def fetch_subreddit_submissions(self, subreddit_name: str, search_term: str, limit=10) -> list[SubmissionBase]:
    submissions = []
    try:
      logger.info(f"Searching for term '{search_term}' in subreddit '{subreddit_name}' with limit {limit}")
      subreddit = await self.client.subreddit(subreddit_name)
      async for praw_submission in subreddit.search(search_term, limit=limit):
        submission = SubmissionBase(
          id=praw_submission.id,
          title=praw_submission.title,
          created_utc=praw_submission.created_utc,
          subreddit_name=praw_submission.name,
          score=praw_submission.score,
          upvote_ratio=praw_submission.upvote_ratio,
          over_18=praw_submission.over_18,
          num_comments=praw_submission.num_comments
        ) 
        submissions.append(submission)
      logger.info(f"Found {len(submissions)} submissions")
    except Exception as e:
      logger.error(f"Error fetching submissions: {e}")
    return submissions
  
  async def serialize_comment(self, praw_comment) -> Comment:
    # recursive function to serialize a PRAW comment
    replies = []
    if hasattr(praw_comment, "replies") and praw_comment.replies:
       # Use asyncio.gather to run serializations concurrently.
          replies = await asyncio.gather(*[
              self.serialize_comment(reply) for reply in praw_comment.replies if reply is not None
          ])
    return Comment(
      id=praw_comment.id,
      body=praw_comment.body,
      score=praw_comment.score,
      replies=replies
    )
  
  async def submission_comments(self, submission_id: str) -> list[Comment]:
    comments_list = []
    try:
      praw_submission = await self.client.submission(id=submission_id)
      await praw_submission.load()
      await praw_submission.comments.replace_more(limit=0)

      for praw_comment in praw_submission.comments.list():
        comment = await self.serialize_comment(praw_comment)
        comments_list.append(comment)
    except Exception as e:
      logger.error(f"Error fetching comments: {e}")
    return comments_list
  
  async def fetch_top_submission_comments(self, search_request: ProductSearchRequest) -> list[Comment]:
    subreddits = ["buyitforlife"]
    all_comments = []

    # Iterate through provided subreddits to grab top n submissions, iterate through each and add to all_comments
    for subreddit in subreddits:
      info = await self.subreddit_info(subreddit) # returns a subreddit object
      logger.info(f"Fetched info for {info.display_name}")

      submissions = await self.fetch_subreddit_submissions(subreddit, search_request.product_category) # returns a list of submission objects (10 in dev)
      logger.info(f"Fetched {len(submissions)} submissions from {subreddit}")

      # iterate through submissions to build comment trees
      for submission in submissions:
        comments = await self.submission_comments(submission.id)
        all_comments.extend(comments)
    
    # sort comments by score from high to low
    sorted_comments = sorted(all_comments, key=lambda c: getattr(c, "score", 0), reverse=True)
    return sorted_comments

  async def find_products_from_comments(self, comments: list[Comment], query: str) -> list[Product]:
    #caching
    cache_key = f"search:{hashlib.sha256(query.encode()).hexdigest()}"
    cached_result_raw = await self.redis.get(cache_key)
    if cached_result_raw:
      try:
        cached_result = json.loads(cached_result_raw)
        logger.info(f"Cache hit for query: {query}")
        # Validate cached data
        return [Product(**product) for product in cached_result]
      except (json.JSONDecodeError, ValidationError):
        logger.warning(f"Cache data invalid for key: {cache_key}, reprocessing.")

    logger.info(f"Cache miss for query: {query}. Processing via OpenAI.")   

    # setup for batching
    batch_size = 10
    all_products = [] # list of (evenutally) ProductWithScore objects
    for i in range(0, len(comments), batch_size):
      batch = comments[i:i + batch_size]
      products_list_batch = await self.batch_openai_call(batch) # a list of ProductWithScore objects
      all_products.extend(products_list_batch)

    # remove duplicates
    unique_products = []
    seen_products = set()
    for product_with_score in all_products:
      product = product_with_score.product
      product_tuple = (product.brand_name.lower(), product.product_name.lower())
      if product_tuple not in seen_products:
        seen_products.add(product_tuple)
        unique_products.append(product) 

    # Cache and return
    if unique_products:
      serialized_products = json.dumps([p.model_dump() for p in unique_products])
      await self.redis.set(cache_key, serialized_products, ex=3600)
    
    return unique_products

  async def batch_openai_call(self, comments_chunk: list[str]) -> list:
    # Convert Comment objects to their body texts
    comments_string = "\n".join([comment.body for comment in comments_chunk])

    try:
      completion = openai.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
          {"role": "system", "content": "You are a brand and product finding assistant. You will be given a list of comments and should return unique brand/product combinations as a valid JSON object."},
          {"role": "user", "content": f"""
      Instructions:
      - Extract the brand and product name from the comments. Do NOT allow for generic product names like "toaster". If there is no clear product name do not include the product.
      - Return *only* the extracted brand and product combinations in a valid JSON object in the following format:
        {{
          "products": [
          {{
            "brand_name": "Brand Name",
            "product_name": "Product Name"
          }},
          {{
            "brand_name": "Another brand",
            "product_name": "Another product"
          }}
          ]
        }}
      - Ensure the output contains *only* valid JSON and nothing else. The brand_name and product_name must be strings.

      Comments: 
      {comments_string}
      """}],
      response_format=ProductList
      )

      return completion.choices[0].message.parsed.products
    except Exception as e:
      logger.error(f"Error processing comments with OpenAI: {e}")
      return []