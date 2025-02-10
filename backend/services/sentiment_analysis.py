import json
import re
from transformers import pipeline
from backend.models.product import Product

class SentimentAnalysis:
  def __init__(self):
    self.sentiment_pipeline = pipeline("sentiment-analysis")

  def extract_product_names(self, products_list: list[Product]):
    products = []
    for product in products_list:
      brand_name = product.brand_name
      product_name = product.product_name
      product_full_name = f"{brand_name} {product_name}".strip() # Combine and remove extra spaces

      if brand_name.lower() not in ["unknown", "n/a"]:
        products.append(product_full_name)
    return products
