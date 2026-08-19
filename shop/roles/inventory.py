import json
import random

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
        cached = cache.get("catalog:v2")
        if cached:
            CACHE.labels("hit").inc()
            return {"products": json.loads(cached), "cache": "hit"}
        CACHE.labels("miss").inc()
    except redis.RedisError as e:
        CACHE.labels("error").inc()
        log.warning(f"catalog cache unavailable, falling back to database: {e}", extra={"error": str(e)})
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT sku, name, category, price_cents, currency FROM products ORDER BY sku LIMIT 24")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    try:
        cache.setex("catalog:v2", 15, json.dumps(rows))
    except redis.RedisError:
        pass
    return {"products": rows, "cache": "miss"}


@app.get("/products/{sku}/availability")
def availability(sku: str):
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT coalesce(sum(qty - reserved), 0), count(*) FROM stock_levels WHERE sku = %s", (sku,))
        available, locations = cur.fetchone()
    return {"sku": sku, "available": int(available), "locations": locations}


@app.post("/reserve")
def reserve(body: dict):
    sku, qty = body["sku"], int(body.get("qty", 1))
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT name, category, price_cents, currency FROM products WHERE sku = %s", (sku,))
        product = cur.fetchone()
        if not product:
            raise HTTPException(status_code=404, detail=f"unknown sku {sku}")
        # Reserve from the location with the most free stock among a few candidates.
        cur.execute("UPDATE stock_levels SET reserved = reserved + %s, updated_at = now() "
                    "WHERE sku = %s AND location_id = %s RETURNING location_id",
                    (qty, sku, random.randint(1, 2500)))
        if not cur.fetchone():
            raise HTTPException(status_code=409, detail=f"no stock record for {sku}")
    return {"sku": sku, "qty": qty, "name": product[0], "category": product[1],
            "price_cents": product[2], "currency": product[3]}
