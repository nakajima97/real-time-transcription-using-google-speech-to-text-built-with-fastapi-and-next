import os
from dotenv import load_dotenv

def load_env():
    load_dotenv()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH", "./google-cloud-key.json")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path