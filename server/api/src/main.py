from fastapi import FastAPI

from src.websocket.transcription import app_socketio

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

app.mount("/socket.io", app_socketio)