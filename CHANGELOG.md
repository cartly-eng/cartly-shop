# Changelog

## 2.4.5
- inventory: reservations take stock from the location with the most free stock.
- web: `/healthz` is served on the event loop.

## 2.4.4
- db: requests wait up to `DB_POOL_TIMEOUT_S` (30s) for a pooled connection instead of failing with `PoolError` (backport).

## 2.4.3
- promotions: flash-sale service (`/promotions/flash-sale`, `/promotions/flash-sale/claim`) with promo holds on `stock_levels`.
- inventory: per-location stock in `stock_levels`; `/products/{sku}/availability`; reservations update a location row.
- all: DB sessions set `application_name` to the service name.

## 2.4.2
- deps: cartly-pycommons 1.3.2 (request_id in logs, timeout classification).

## 2.4.1
- checkout: add EUR to the pricing v2 tax table (fixes `KeyError('EUR')` on EUR checkouts).

## 2.4.0
- checkout: pricing engine v2 with per-currency tax tables.

## 2.3.0
- Initial import of storefront, inventory, checkout, payments, gateway, synthetics.
