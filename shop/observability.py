import os

from cartly_commons.logging import configure
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram

from shop.config import APP_VERSION, GIT_COMMIT, OTLP_ENDPOINT, SERVICE

log = configure(SERVICE, APP_VERSION)

_provider = TracerProvider(resource=Resource.create({
    "service.name": SERVICE,
    "service.version": APP_VERSION,
    "service.namespace": "shop",
    "deployment.environment": "production",
    "vcs.commit": GIT_COMMIT,
    "k8s.namespace.name": os.environ.get("POD_NAMESPACE", ""),
    "k8s.pod.name": os.environ.get("POD_NAME", ""),
}))
if OTLP_ENDPOINT:
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
trace.set_tracer_provider(_provider)
tracer = trace.get_tracer(SERVICE)
HTTPXClientInstrumentor().instrument()
Psycopg2Instrumentor().instrument(enable_commenter=False)
RedisInstrumentor().instrument()

HTTP_REQUESTS = Counter("shop_http_requests_total", "HTTP requests served", ["service", "route", "method", "status"])
HTTP_LATENCY = Histogram("shop_http_request_duration_seconds", "HTTP request latency", ["service", "route"],
                         buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, 16))
DOWNSTREAM = Histogram("shop_downstream_request_duration_seconds", "Outbound call latency",
                       ["service", "target", "outcome"], buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, 16))
ORDERS = Counter("shop_orders_total", "Orders placed", ["status"])
PAYMENT_RETRIES = Counter("shop_payment_gateway_retries_total", "Retries against the acquirer")
CACHE = Counter("shop_cache_requests_total", "Catalog cache lookups", ["result"])
DB_POOL_IN_USE = Gauge("shop_db_pool_connections_in_use", "Checked-out DB connections", ["service"])
SYNTHETIC_OK = Gauge("shop_synthetic_journey_success", "1 if the last synthetic journey passed", ["journey"])
SYNTHETIC_LATENCY = Gauge("shop_synthetic_journey_duration_seconds", "Duration of last synthetic journey", ["journey"])
BUILD_INFO = Gauge("shop_build_info", "Build info", ["service", "version", "commit"])
BUILD_INFO.labels(SERVICE, APP_VERSION, GIT_COMMIT[:12]).set(1)
