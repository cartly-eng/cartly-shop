import os

import httpx
from cartly_commons.http import timed_call
from fastapi import HTTPException

from shop.config import GATEWAY_URL, SERVICE
from shop.observability import DOWNSTREAM, PAYMENT_RETRIES, log, tracer
from shop.web import app, http

GATEWAY_TIMEOUT_S = float(os.environ.get("GATEWAY_TIMEOUT_S", "3"))
GATEWAY_RETRIES = int(os.environ.get("GATEWAY_RETRIES", "3"))


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.post("/charge")
def charge(body: dict, dry_run: bool = False):
    last_error = None
    for attempt in range(1, GATEWAY_RETRIES + 1):
        try:
            with tracer.start_as_current_span("acquirer.authorize") as span:
                span.set_attribute("payment.attempt", attempt)
                with timed_call(DOWNSTREAM, SERVICE, "payment-gateway", timeout_exc=(httpx.TimeoutException,)):
                    r = http.post(f"{GATEWAY_URL}/v1/authorize", json=body, timeout=GATEWAY_TIMEOUT_S)
                r.raise_for_status()
                return {"payment_id": r.json()["authorization_id"], "dry_run": dry_run}
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            last_error = e
            PAYMENT_RETRIES.inc()
            log.warning(f"acquirer authorize failed attempt={attempt}/{GATEWAY_RETRIES}: {type(e).__name__}",
                        extra={"attempt": attempt, "error": type(e).__name__})
    log.error(f"payment declined after {GATEWAY_RETRIES} attempts: acquirer unavailable ({last_error!r})")
    raise HTTPException(status_code=503, detail="payment acquirer unavailable")
