import os

ROLE = os.environ.get("ROLE", "frontend")
SERVICE = os.environ.get("SERVICE_NAME", ROLE)
APP_VERSION = os.environ.get("APP_VERSION", "dev")
GIT_COMMIT = os.environ.get("GIT_COMMIT", "unknown")
PORT = int(os.environ.get("PORT", "8080"))
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")

INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://inventory:8080")
CHECKOUT_URL = os.environ.get("CHECKOUT_URL", "http://checkout:8080")
PAYMENTS_URL = os.environ.get("PAYMENTS_URL", "http://payments:8080")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://payment-gateway:8080")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend:8080")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
HTTP_TIMEOUT_S = float(os.environ.get("HTTP_TIMEOUT_S", "5"))
