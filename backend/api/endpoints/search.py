from fastapi import APIRouter, Depends, HTTPException
from transformers import pipeline
from typing import Dict, List, Tuple
import logging

from backend.models.product_search_request import ProductSearchRequest
from backend.models.product import Product, ProductList, ProductWithScore
from backend.dependencies import get_reddit_service, get_openai_service
from backend.services.reddit_service import RedditService
from backend.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])

class SearchController:
  def __init__(self, reddit_service: RedditService, openai_service: OpenAIService):
    self.reddit_service = reddit_service
    self.openai_service = openai_service
    # pipelines
    self._ner_pipeline = None
    self._sentiment_pipeline = None

  @property
  def ner_pipeline(self):
    if not self._ner_pipeline:
      self._ner_pipeline = pipeline("ner", grouped_entities=True, device=0)
    return self._ner_pipeline
  
  @property
  def sentiment_pipeline(self):
    if not self._sentiment_pipeline:
      self._sentiment_pipeline = pipeline(
        task="sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
      )
    return self._sentiment_pipeline
  
  async def execute_search(self, search_request: ProductSearchRequest) -> ProductList:
    logger.info(f"Received search request: {search_request}")

    # Fetch and filter comments.
    top_comments = await self.reddit_service.fetch_top_submission_comments(search_request)
    logger.info(f"Fetched {len(top_comments)} top comments")
    filtered_comments = await self.reddit_service.filter_comments(top_comments, self.ner_pipeline)
    logger.info(f"Filtered comments: {len(filtered_comments)}")

    # Extract products from comments.
    products_list = await self.reddit_service.find_products_from_comments(filtered_comments, search_request.product_category)
    logger.info(f"Found products: {products_list}")

    # Retrieve subject phrases via OpenAI.
    subject_phrases = await self.openai_service.find_subject_phrases(search_request.product_category)
    logger.info(f"Subject phrases: {subject_phrases}")

    # Clean products list against subject phrases.
    cleaned_products = self.clean_products(products_list, subject_phrases, search_request.product_category)
    logger.info(f"Cleaned products list: {cleaned_products}")

    # 5. Perform sentiment analysis.
    product_sentiments = self.analyze_sentiments(filtered_comments, cleaned_products)
    # 6. Compute average sentiments.
    product_avg_sentiment = self.compute_average_sentiments(product_sentiments)
    # 7. Rank products.
    ranked_products = sorted(product_avg_sentiment.items(), key=lambda item: item[1], reverse=True)
    logger.info(f"Ranked Products: {ranked_products}")

    # Package result.
    product_list_with_scores = [
        ProductWithScore(product=Product(brand_name=brand, product_name=product), score=score)
        for (brand, product), score in ranked_products
    ]
    logger.info(f"Returning ProductList: {product_list_with_scores}")
    return ProductList(products=product_list_with_scores)
  
  def clean_products(self, products_list: List[Product], subject_phrases, category: str) -> List[Product]:
    cleaned = []
    for product in products_list:
      if (product.brand_name in subject_phrases.excluded_words or 
        product.product_name in subject_phrases.excluded_words):
        continue
      if product.product_name.lower() == category.lower():
        continue
      cleaned.append(product)
    return cleaned
  
  def analyze_sentiments(self, comments, products: List[Product]) -> Dict[Tuple[str, str], List[float]]:
    sentiment_results = self.sentiment_pipeline(
        [comment.body for comment in comments], truncation=True, max_length=512
    )
    logger.info(f"Sentiment results count: {len(sentiment_results)}")
    product_sentiments: Dict[Tuple[str, str], List[float]] = {
        (product.brand_name, product.product_name): [] for product in products
    }

    for i, comment in enumerate(comments):
      for product in products:
        if (product.brand_name.lower() in comment.body.lower() or 
          product.product_name.lower() in comment.body.lower()):
          sentiment = sentiment_results[i]['label']
          score = sentiment_results[i]['score']
          sentiment_score = score if sentiment == 'POSITIVE' else -score
          product_sentiments[(product.brand_name, product.product_name)].append(sentiment_score)
    return product_sentiments
  
  def compute_average_sentiments(self, sentiments: Dict[Tuple[str, str], List[float]]) -> Dict[Tuple[str, str], float]:
    avg_sentiments = {}
    for key, scores in sentiments.items():
      avg_sentiments[key] = sum(scores) / len(scores) if scores else 0
    return avg_sentiments
  
@router.post("/", response_model=ProductList)
async def search(
  search_request: ProductSearchRequest,
  reddit_service = Depends(get_reddit_service),
  openai_service = Depends(get_openai_service)
):
  controller = SearchController(reddit_service, openai_service)
  try:
    result = await controller.execute_search(search_request)
    return result
  except Exception as e:
    logger.exception("Error during search execution")
    raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")