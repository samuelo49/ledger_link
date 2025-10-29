from fastapi import FastAPI


def create_app() -> FastAPI:
    return FastAPI(title="Risk Service", version="0.1.0")
