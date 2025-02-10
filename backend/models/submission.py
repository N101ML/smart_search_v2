from pydantic import BaseModel

class SubmissionBase(BaseModel):
  id: str
  title: str
  created_utc: int
  subreddit_name: str
  score: int
  upvote_ratio: float
  over_18: bool
  num_comments: int


class SubmissionCreate(SubmissionBase):
  pass
