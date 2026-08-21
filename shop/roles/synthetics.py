"""Synthetic monitoring: steady browse/buy traffic plus journey probes exported as metrics."""
import random
import threading
import time

import httpx

from shop.config import FRONTEND_URL, PAYMENTS_URL, PROMOTIONS_URL
from shop.observability import SYNTHETIC_LATENCY, SYNTHETIC_OK, log
from shop.web import app  # noqa: F401  (serves /metrics)

client = httpx.Client(timeout=20.0)
skus = []


def refresh_skus():
    global skus
    try:
        skus = [p["sku"] for p in client.get(f"{FRONTEND_URL}/api/products").json()["products"]]
    except Exception as e:
        log.warning(f"synthetics could not load catalog: {e!r}")


def browse():
    while True:
        try:
            client.get(f"{FRONTEND_URL}/" if random.random() < 0.3 else f"{FRONTEND_URL}/api/products")
            if random.random() < 0.2:
                client.get(f"{FRONTEND_URL}/api/orders/recent")
        except Exception:
            pass
        time.sleep(random.uniform(0.3, 1.0))


def buy():
    while True:
        if not skus:
            refresh_skus()
        if skus:
            try:
                client.post(f"{FRONTEND_URL}/api/checkout", json={"sku": random.choice(skus), "qty": 1})
            except Exception:
                pass
        time.sleep(random.uniform(0.8, 2.0))


def promotions():
    while True:
        try:
            deals = client.get(f"{PROMOTIONS_URL}/promotions/flash-sale").json().get("items", [])
            if deals and random.random() < 0.5:
                client.post(f"{PROMOTIONS_URL}/promotions/flash-sale/claim", json={"sku": random.choice(deals)["sku"]})
        except Exception:
            pass
        time.sleep(random.uniform(4, 8))


def journey(name, fn):
    while True:
        start = time.perf_counter()
        try:
            ok = fn()
        except Exception:
            ok = False
        SYNTHETIC_OK.labels(name).set(1 if ok else 0)
        SYNTHETIC_LATENCY.labels(name).set(time.perf_counter() - start)
        time.sleep(15)


def checkout_journey():
    refresh_skus()
    return bool(skus) and client.post(f"{FRONTEND_URL}/api/checkout",
                                      json={"sku": random.choice(skus), "qty": 1}).status_code == 200


def payments_journey():
    return client.post(f"{PAYMENTS_URL}/charge?dry_run=true", json={"amount_cents": 100, "currency": "USD"}).status_code == 200


def start():
    for _ in range(3):
        threading.Thread(target=browse, daemon=True).start()
    for _ in range(2):
        threading.Thread(target=buy, daemon=True).start()
    threading.Thread(target=promotions, daemon=True).start()
    threading.Thread(target=journey, args=("checkout", checkout_journey), daemon=True).start()
    threading.Thread(target=journey, args=("payment_authorize", payments_journey), daemon=True).start()
    log.info("synthetic checks started")
