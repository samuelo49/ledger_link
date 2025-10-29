"""Generate OpenAPI specs for all services."""

import importlib
import json
from pathlib import Path
from typing import Callable

from fastapi import FastAPI

SERVICES = {
    "api-gateway": "services.api_gateway.app:create_app",
    "identity-service": "services.identity_service.app:create_app",
}


def load_app(factory_path: str) -> FastAPI:
    module_path, factory_name = factory_path.split(":")
    module = importlib.import_module(module_path)
    factory: Callable[[], FastAPI] = getattr(module, factory_name)
    return factory()


def main() -> None:
    out_dir = Path("openapi")
    out_dir.mkdir(exist_ok=True)
    for name, dotted in SERVICES.items():
        app = load_app(dotted)
        schema = app.openapi()
        target = out_dir / f"{name}.json"
        target.write_text(json.dumps(schema, indent=2))
        print(f"Wrote {target}")


if __name__ == "__main__":
    main()
