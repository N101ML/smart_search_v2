from typing import Generator, List, Any

def chunk_list(lst: List[Any], chunk_size: int):
  """Chunk giant comment lists up so it's easier to batch to OpenAI"""
  for i in range(0, len(lst), chunk_size):
    yield lst[i:i + chunk_size]