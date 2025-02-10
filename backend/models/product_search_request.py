from fastapi import FastAPI
from pydantic import BaseModel

class ProductSearchRequest(BaseModel):
  product_category: str
  min_price: float
  max_price: float
  sites: list[str]
  retailers: list[str]