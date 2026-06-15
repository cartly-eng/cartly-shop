from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from shop.config import APP_VERSION, CHECKOUT_URL, INVENTORY_URL
from shop.web import app, call_json


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.get("/api/products")
def api_products():
    return call_json("GET", f"{INVENTORY_URL}/products", "inventory")


@app.post("/api/checkout")
def api_checkout(body: dict):
    return call_json("POST", f"{CHECKOUT_URL}/checkout", "checkout", json=body, timeout=15.0)


@app.get("/api/orders/recent")
def api_recent():
    return call_json("GET", f"{CHECKOUT_URL}/orders/recent", "checkout")


@app.get("/", response_class=HTMLResponse)
def home():
    try:
        items = call_json("GET", f"{INVENTORY_URL}/products", "inventory")["products"]
        cards = "".join(
            f"<div class='card'><b>{p['name']}</b><small>{p['category']}</small>"
            f"<span>{p['price_cents'] / 100:.2f} {p['currency']}</span>"
            f"<button onclick=\"buy('{p['sku']}')\">Buy</button></div>" for p in items)
    except HTTPException as e:
        cards = f"<p class='err'>Catalog unavailable: {e.detail}</p>"
    return f"""<!doctype html><title>Cartly</title>
<style>body{{font-family:system-ui;margin:2rem auto;max-width:960px;padding:0 1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}}
.card{{border:1px solid #ddd;border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:4px}}
.err{{color:#b00}}#out{{margin-top:1rem;font-family:monospace}}</style>
<h1>Cartly <small style="font-size:.5em;color:#888">v{APP_VERSION}</small></h1>
<div class=grid>{cards}</div><pre id=out></pre>
<script>async function buy(sku){{const r=await fetch('/api/checkout',{{method:'POST',
headers:{{'content-type':'application/json'}},body:JSON.stringify({{sku,qty:1}})}});
document.getElementById('out').textContent=r.status+' '+await r.text();}}</script>"""
