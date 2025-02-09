import os
from dotenv import load_dotenv

def load_env():
    load_dotenv()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH", "./google-cloud-key.json")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

def get_env_value(key: str, default: str = None) -> str:
    """
    環境変数の値を取得する

    Args:
        key (str): 環境変数のキー
        default (str, optional): デフォルト値

    Returns:
        str: 環境変数の値
    """
    return os.getenv(key, default)