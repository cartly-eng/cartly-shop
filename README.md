# cartly-shop

Cartly storefront services. One image, one Python package; `ROLE` selects the service.

| Role | Service | Talks to |
|---|---|---|
| `frontend` | storefront + `/api/*` | inventory, checkout |
| `inventory` | catalog, stock, reservations | Postgres, Redis |
| `checkout` | order placement, pricing | inventory, payments, Postgres |
| `payments` | card authorization | payment-gateway |
| `gateway` | acquirer integration edge | external acquirer |
| `synthetics` | synthetic journeys (checkout, card authorization) | frontend, payments |

All services: Prometheus metrics on `/metrics`, OTLP traces, JSON logs (`cartly-pycommons`).

## Release

1. Merge to `main` (CI runs tests).
2. Tag `vX.Y.Z` → CI builds `drdroidtest.azurecr.io/cartly/shop-service:vX.Y.Z`.
3. Promote by bumping the image tag for a service in [`cartly-deploy`](https://github.com/prateekkanurkar-cmd/cartly-deploy); ArgoCD syncs it.
