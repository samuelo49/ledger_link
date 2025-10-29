# Re-export the FastAPI application for ASGI servers.
from .main import create_app

app = create_app()
