import os


def load_env():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./google-cloud-key.json"