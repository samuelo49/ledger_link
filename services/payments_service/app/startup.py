from __future__ import annotations

from fastapi import FastAPI
from loguru import logger
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from .settings import payments_settings


def setup_instrumentation(app: FastAPI) -> None:
    if trace.get_tracer_provider() and not isinstance(trace.get_tracer_provider(), trace.NoOpTracerProvider):
        return
    settings = payments_settings()
    resource = Resource(attributes={SERVICE_NAME: settings.service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317")))
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    app.state.tracer_provider = tracer_provider
    logger.info("📈 OpenTelemetry instrumentation configured for Payments Service.")
