from fastapi import FastAPI

from src.websocket.transcription import app_socketio
from src.settings.cors import add_cors_middleware
from src.settings.env import load_env

load_env()

app = FastAPI()
add_cors_middleware(app)

@app.get("/")
def read_root():
    return {"Hello": "World"}

app.mount("/socket.io", app_socketio)