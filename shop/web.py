import logging
import random
import time

import httpx
from cartly_commons.http import timed_call
from cartly_commons.middleware import RequestContextMiddleware
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from shop.config import APP_VERSION, GIT_COMMIT, HTTP_TIMEOUT_S, SERVICE
from shop.observability import DOWNSTREAM, HTTP_LATENCY, HTTP_REQUESTS, log

SKIP_ROUTES = ("/metrics", "/healthz", "/readyz")

app = FastAPI(title=SERVICE)
# x-request-id propagation + response replay buffer for error reports (cartly-pycommons 1.4.0)
app.add_middleware(RequestContextMiddleware)
http = httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT_S))


@app.middleware("http")
async def observe(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    except Exception as exc:
        log.error(f"unhandled exception on {request.url.path}: {exc!r}", exc_info=exc, extra={"error": type(exc).__name__})
        return JSONResponse(status_code=500, content={"error": "internal server error", "detail": type(exc).__name__})
    finally:
        route = getattr(request.scope.get("route"), "path", request.url.path)
        if route not in SKIP_ROUTES:
            elapsed = time.perf_counter() - start
            HTTP_REQUESTS.labels(SERVICE, route, request.method, str(status)).inc()
            HTTP_LATENCY.labels(SERVICE, route).observe(elapsed)
            if status >= 500 or random.random() < 0.2:
                log.log(logging.ERROR if status >= 500 else logging.INFO, f"{request.method} {route} -> {status}",
                        extra={"route": route, "status": status, "duration_ms": round(elapsed * 1000, 1)})


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
async def healthz():  # event loop, so a saturated worker threadpool cannot fail liveness
    return {"status": "ok", "service": SERVICE, "version": APP_VERSION, "commit": GIT_COMMIT}


def call_json(method, url, target, **kwargs):
    with timed_call(DOWNSTREAM, SERVICE, target, timeout_exc=(httpx.TimeoutException,)):
        r = http.request(method, url, **kwargs)
    if r.status_code >= 500:
        raise HTTPException(status_code=502, detail=f"{target} returned {r.status_code}")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", r.text))
    return r.json()
