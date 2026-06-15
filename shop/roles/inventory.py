import json

import redis
from fastapi import HTTPException

from shop import db
from shop.config import REDIS_URL
from shop.observability import CACHE, log
from shop.web import app

cache = redis.Redis.from_url(REDIS_URL, socket_timeout=0.5, socket_connect_timeout=0.5)


@app.get("/readyz")
def readyz():
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1")
    return {"status": "ready"}


@app.get("/products")
def products():
    try:
        cached = cache.get("catalog:v1")
        if cached:
            CACHE.labels("hit").inc()
            return {"products": json.loads(cached), "cache": "hit"}
        CACHE.labels("miss").inc()
    except redis.RedisError as e:
        CACHE.labels("error").inc()
        log.warning(f"catalog cache unavailable, falling back to database: {e}", extra={"error": str(e)})
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT sku, name, category, price_cents, currency, stock FROM products ORDER BY sku LIMIT 24")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    try:
        cache.setex("catalog:v1", 15, json.dumps(rows))
    except redis.RedisError:
        pass
    return {"products": rows, "cache": "miss"}


@app.post("/reserve")
def reserve(body: dict):
    sku, qty = body["sku"], int(body.get("qty", 1))
    with db.conn() as c, c.cursor() as cur:
        cur.execute("UPDATE products SET stock = stock - %s WHERE sku = %s "
                    "RETURNING name, category, price_cents, currency", (qty, sku))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"unknown sku {sku}")
    return {"sku": sku, "qty": qty, "name": row[0], "category": row[1], "price_cents": row[2], "currency": row[3]}
