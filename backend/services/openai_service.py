import logging
from backend.config import Config
from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)
# Configure openai api key
openai = OpenAI(api_key=Config.OPENAI_API_KEY)

class SubjectPhrasesRequest(BaseModel):
  included_words: list[str]
  excluded_words: list[str]

class OpenAIService:
  def __init__(self):
    self.client = OpenAI()

  async def chat(self, user_message: str, model: str, system_prompt: str = "You are a helpful assistant") -> str:
    try:
      response = self.client.chat.completions.create(
        model=model,
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_message}
        ]
      )
      return response.choices[0].message.content
    except Exception as e:
      logger.error(f"Error fetching response: {e}")
      return "Sorry, I'm having trouble understanding you right now."
    
  async def find_subject_phrases(self, query: str) -> dict:
    completion = self.client.beta.chat.completions.parse(
      model="gpt-4o-2024-08-06",
      messages=[
          {"role": "system", "content": "Given a search query provide a comprehensive list of phrases that should be included (because they are relevant to the query) and excluded (because they are not related at all). Please respond in the provided format"},
          {"role": "user", "content": f"{query}"},
      ],
      response_format=SubjectPhrasesRequest,
    )
    return completion.choices[0].message.parsed