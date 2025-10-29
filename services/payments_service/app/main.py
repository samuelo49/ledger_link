from fastapi import FastAPI


def create_app() -> FastAPI:
    return FastAPI(title="Payments Service", version="0.1.0")
