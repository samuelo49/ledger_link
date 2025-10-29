from loguru import logger
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from fastapi import FastAPI

from .settings import identity_settings


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level="INFO",
        backtrace=False,
        diagnose=False,
        colorize=False,
        serialize=False,
    )


def setup_instrumentation(app: FastAPI) -> None:
    settings = identity_settings()
    resource = Resource(attributes={SERVICE_NAME: settings.service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint)))
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
