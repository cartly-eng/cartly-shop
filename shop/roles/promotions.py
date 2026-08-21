"""Flash-sale promotions: picks products with the most free stock and places promo holds on it."""
from fastapi import HTTPException

from shop import db
from shop.observability import PROMO_CLAIMS, log
from shop.web import app


@app.get("/readyz")
def readyz():
    with db.conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1")
    return {"status": "ready"}


@app.get("/promotions/flash-sale")
@app.get("/api/promotions/flash-sale")
def flash_sale():
    """Products eligible for the running flash sale: most free stock across all locations."""
    with db.conn() as c, c.cursor() as cur:
        cur.execute("""
            SELECT s.sku, p.name, p.price_cents, p.currency,
                   sum(s.qty - s.reserved - s.promo_hold) AS free_stock,
                   count(*) FILTER (WHERE s.qty - s.reserved - s.promo_hold > 20) AS locations
              FROM stock_levels s JOIN products p USING (sku)
             WHERE s.updated_at > now() - interval '90 days'
             GROUP BY s.sku, p.name, p.price_cents, p.currency
            HAVING sum(s.qty - s.reserved - s.promo_hold) > 1000
             ORDER BY free_stock DESC
             LIMIT 12""")
        cols = [d[0] for d in cur.description]
        items = [dict(zip(cols, r)) for r in cur.fetchall()]
    for i in items:
        i["deal_price_cents"] = int(i["price_cents"] * 0.7)
    return {"campaign": "flash-sale", "items": items}


@app.post("/promotions/flash-sale/claim")
@app.post("/api/promotions/flash-sale/claim")
def claim(body: dict):
    sku = body["sku"]
    with db.conn() as c, c.cursor() as cur:
        cur.execute("""
            UPDATE stock_levels SET promo_hold = promo_hold + 1, updated_at = now()
             WHERE sku = %s AND location_id IN (
                   SELECT location_id FROM stock_levels WHERE sku = %s
                    ORDER BY qty - reserved - promo_hold DESC LIMIT 25)""", (sku, sku))
        held = cur.rowcount
    if not held:
        PROMO_CLAIMS.labels("unavailable").inc()
        raise HTTPException(status_code=409, detail="deal no longer available")
    PROMO_CLAIMS.labels("held").inc()
    log.info(f"flash-sale hold placed sku={sku} locations={held}", extra={"sku": sku})
    return {"sku": sku, "held_locations": held}
