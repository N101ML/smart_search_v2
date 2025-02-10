# backend/core/database.py
import psycopg2
from psycopg2.extras import RealDictCursor
from backend.core.config import Config
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
  try:
    conn = psycopg2.connect(Config.DATABASE_URL)
    logger.info("Database connection successful")
    return conn
  except Exception as e:
    logger.error(f"Error connecting to the database: {e}")
    raise