from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI


def add_cors_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Adjust this to your allowed origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
