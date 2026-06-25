import os

from shop import db
from shop.config import INVENTORY_URL, PAYMENTS_URL
from shop.observability import ORDERS, log, tracer
from shop.web import app, call_json

PRICING_ENGINE = os.environ.get("PRICING_ENGINE", "v2")
# v2: per-currency tax tables
TAX_TABLE_V2 = {"USD": 0.0725, "INR": 0.18, "GBP": 0.20, "EUR": 0.19}



@app.get("/readyz")
def readyz():
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1")
    return {"status": "ready"}


def price_with_tax(item):
    subtotal = item["price_cents"] * item["qty"]
    if PRICING_ENGINE == "v2":
        with tracer.start_as_current_span("pricing.v2.compute_tax") as span:
            span.set_attribute("pricing.currency", item["currency"])
            return int(subtotal * (1 + TAX_TABLE_V2[item["currency"]]))
    return int(subtotal * 1.08)


@app.post("/checkout")
def checkout(body: dict):
    sku, qty = body["sku"], int(body.get("qty", 1))
    item = call_json("POST", f"{INVENTORY_URL}/reserve", "inventory", json={"sku": sku, "qty": qty})
    total = price_with_tax(item)
    charge = call_json("POST", f"{PAYMENTS_URL}/charge", "payments",
                       json={"amount_cents": total, "currency": item["currency"]},
                       timeout=float(os.environ.get("PAYMENTS_TIMEOUT_S", "12")))
    with db.conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO orders (sku, qty, total_cents, currency, payment_id, status) "
                    "VALUES (%s, %s, %s, %s, %s, 'placed') RETURNING id",
                    (sku, qty, total, item["currency"], charge["payment_id"]))
        order_id = cur.fetchone()[0]
    ORDERS.labels("placed").inc()
    log.info(f"order placed order_id={order_id} sku={sku} total_cents={total}", extra={"order_id": order_id, "sku": sku})
    return {"order_id": order_id, "total_cents": total, "currency": item["currency"]}


@app.get("/orders/recent")
def recent_orders():
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT id, sku, qty, total_cents, currency, status, created_at FROM orders ORDER BY id DESC LIMIT 10")
        cols = [d[0] for d in cur.description]
        return {"orders": [dict(zip(cols, [str(v) if k == "created_at" else v for k, v in zip(cols, r)]))
                           for r in cur.fetchall()]}
