import importlib

import uvicorn
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from shop.config import APP_VERSION, PORT, ROLE, SERVICE
from shop.observability import log

role = importlib.import_module(f"shop.roles.{ROLE}")
from shop.web import app  # noqa: E402

FastAPIInstrumentor.instrument_app(app, excluded_urls="metrics,healthz,readyz")

if __name__ == "__main__":
    if ROLE in ("inventory", "checkout", "promotions"):
        from shop import db
        db.verify_on_startup()
    if ROLE == "synthetics":
        role.start()
    log.info(f"{SERVICE} v{APP_VERSION} starting on :{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
