import os


class Config:
  API_ID = int(os.environ.get("API_ID", "123456"))
  API_HASH = os.environ.get("API_HASH", "your_api_hash")
  BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
  MONGO_URL = os.environ.get("MONGO_URL", "your_mongodb_uri")
  
