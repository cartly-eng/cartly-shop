import random
import time
import uuid

from fastapi import HTTPException

from shop.observability import log
from shop.web import app

_profile = {"latency_ms": 0, "error_rate": 0.0}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.post("/internal/upstream-profile")
def set_upstream_profile(latency_ms: int = 0, error_rate: float = 0.0):
    _profile.update(latency_ms=latency_ms, error_rate=error_rate)
    return _profile


@app.post("/v1/authorize")
def authorize(body: dict):
    delay = random.uniform(0.04, 0.12)
    if _profile["latency_ms"]:
        extra = _profile["latency_ms"] / 1000 * random.uniform(0.7, 1.4)
        log.warning(f"issuing bank response slow: upstream acquirer latency {int(extra * 1000)}ms (bank=HDFC-ISS-02)")
        delay += extra
    time.sleep(delay)
    if random.random() < _profile["error_rate"]:
        raise HTTPException(status_code=502, detail="issuer unavailable")
    return {"authorization_id": f"auth_{uuid.uuid4().hex[:16]}", "approved": True}
