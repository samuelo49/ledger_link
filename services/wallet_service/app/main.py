from fastapi import FastAPI


def create_app() -> FastAPI:
    return FastAPI(title="Wallet Service", version="0.1.0")
