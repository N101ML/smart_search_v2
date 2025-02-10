from pydantic import BaseModel
from typing import Optional, List

class Product(BaseModel):
  brand_name: str
  product_name: str

class ProductWithScore(BaseModel):
  product: Product
  score: float

class ProductList(BaseModel):
  products: List[ProductWithScore]