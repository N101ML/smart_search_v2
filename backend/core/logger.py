import logging

def setup_logging():
  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger("backend")
  return logger

logger = setup_logging()