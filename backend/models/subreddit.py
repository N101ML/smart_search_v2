from pydantic import BaseModel
from typing import Optional

class Subreddit(BaseModel):
  id: str
  name: str
  display_name: str
  created_utc: int
  subscribers: int
  over_18: bool