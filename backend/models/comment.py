from pydantic import BaseModel

class Comment(BaseModel):
  id: str
  body: str
  replies: list["Comment"] = []
  score: int