from fastapi import APIRouter, Depends
from backend.models.subreddit import Subreddit
from backend.models.submission import SubmissionCreate
from backend.models.comment import Comment
from backend.dependencies import get_reddit_service
from backend.services.reddit_service import RedditService

router = APIRouter(prefix="/subreddits", tags=["Reddit"])

@router.get("/{subreddit_name}", response_model=Subreddit)
async def subreddit_info(
  subreddit_name: str,
  reddit_service: RedditService = Depends(get_reddit_service)
):
  subreddit = await reddit_service.subreddit_info(subreddit_name)
  return subreddit

@router.get("/{subreddit_name}/search/{search_term}", response_model=list[SubmissionCreate])
async def fetch_subreddit_submissions(
  subreddit_name: str,
  search_term: str,
  reddit_service: RedditService = Depends(get_reddit_service)
):
  submissions = await reddit_service.fetch_subreddit_submissions(subreddit_name, search_term)
  return submissions

@router.get("/submissions/{submission_id}/comments", response_model=list[Comment])
async def submission_comments(
  submission_id: str,
  reddit_service: RedditService = Depends(get_reddit_service)
):
  comments = await reddit_service.submission_comments(submission_id)
  return comments