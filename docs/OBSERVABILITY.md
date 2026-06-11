# Observability: Prometheus + Grafana

Ready11 ships a complete metrics pipeline: the Django app exposes Prometheus
metrics via [django-prometheus](https://github.com/django-commons/django-prometheus),
a Prometheus container scrapes them, and Grafana renders a provisioned
dashboard. Sentry (see `.env.example`) remains the tool for *error details and
stack traces*; Prometheus/Grafana cover *rates, latency and trends*.

## Quick start (development)

```bash
make docker-up    # starts postgres, redis, mailpit, prometheus and grafana
make run          # the Django app must be running for Prometheus to scrape it
```

| Service    | URL                          | Notes                                   |
|------------|------------------------------|-----------------------------------------|
| Metrics    | http://lvh.me:8000/metrics   | Raw Prometheus exposition from Django    |
| Prometheus | http://localhost:9090        | Query UI; check Status → Targets         |
| Grafana    | http://localhost:3000        | Dashboard **Ready11 → Django — Overview**. Anonymous viewing enabled; admin login `admin` / `admin` (or `GRAFANA_ADMIN_PASSWORD`) |

The dashboard auto-refreshes every 10 s and shows:

- **Requests/s, latency p50/p95/p99** (overall and per view)
- **Errors**: responses by status class (2xx/3xx/4xx/5xx), unhandled exceptions by type
- **Database**: query duration p95, new connections/s, db errors
- **Runtime**: process memory

## How it works

- `django_prometheus` is in `SHARED_APPS`; `PrometheusBeforeMiddleware` is the
  first middleware after tenant routing and `PrometheusAfterMiddleware` is the
  last one, so the latency histograms cover the whole middleware stack.
- The database engine keeps `django_tenants.postgresql_backend`, but
  `ORIGINAL_BACKEND = 'django_prometheus.db.backends.postgresql'` makes
  django-tenants wrap the instrumented postgres backend — tenant routing and
  `django_db_*` metrics compose cleanly.
- `GET /metrics` is served by `apps.core.views.metrics`. The dev Prometheus
  container reaches the host's `runserver` via `host.docker.internal`
  (registered as an auxiliary public-tenant domain by `setup_public_tenant`).
- Grafana provisioning lives in `docker/grafana/`: the datasource and the
  dashboard JSON are mounted read-only, so the stack is reproducible from a
  fresh clone with zero clicks.

## Production checklist

1. **Protect the endpoint**: set `METRICS_TOKEN` in the app environment and
   mirror it in `docker/prometheus/prometheus.yml`:

   ```yaml
   scrape_configs:
     - job_name: django
       authorization:
         type: Bearer
         credentials: <same token>
   ```

   Alternatively keep `/metrics` reachable only from the internal network.
2. **Point the scrape target at the app container/service** instead of
   `host.docker.internal:8000` (e.g. `app:8000` on the compose network, or the
   pod/service address in Kubernetes).
3. **Change the Grafana admin password** (`GRAFANA_ADMIN_PASSWORD`) and
   consider disabling anonymous access (`GF_AUTH_ANONYMOUS_ENABLED=false`).
4. **Retention/storage**: the `prometheus_data` volume defaults to 15 days of
   retention. Tune with `--storage.tsdb.retention.time` if you need more.

## Adding metrics for your business apps

`django-prometheus` exports model operation counters automatically if your
model inherits its mixin:

```python
from django_prometheus.models import ExportModelOperationsMixin

class Order(ExportModelOperationsMixin('order'), models.Model):
    ...
```

For custom counters/histograms, use `prometheus_client` directly in your
services layer:

```python
from prometheus_client import Counter

orders_created = Counter('ready11_orders_created_total', 'Orders created')

def create_order(...):
    ...
    orders_created.inc()
```

Then add a panel to `docker/grafana/dashboards/django-overview.json` (or a new
dashboard JSON in the same folder — it is picked up automatically).
