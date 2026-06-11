# Deploying to Easypanel

Step-by-step guide to run Ready11 (or a project bootstrapped from it) on
[Easypanel](https://easypanel.io). Easypanel builds the app from the repo's
`Dockerfile`, provides PostgreSQL/Redis as managed services, and its built-in
Traefik proxy terminates TLS (the app's `SECURE_PROXY_SSL_HEADER` already
trusts `X-Forwarded-Proto`) and proxies WebSockets natively.

## 1. Create the project and backing services

In Easypanel, create a project (e.g. `ready11`) and add:

**PostgreSQL** (service name `db`)
- Image: PostgreSQL **17**
- Note the generated credentials. The internal hostname is
  `<project>_db` (e.g. `ready11_db`).

**Redis** (service name `redis`)
- Required in production: it backs the Channels layer (real-time
  notifications) and the cache. Internal hostname `<project>_redis`.

## 2. Create the app service

Add an **App** service (name `app`):

- **Source**: connect the GitHub repository, branch `main`.
- **Build**: Dockerfile (auto-detected at the repo root).
- **Port**: `8000`.
- **Deploy → Health check** (optional but recommended): path `/healthz/`.
- Enable **auto-deploy on push** so merging to `main` redeploys.

The container entrypoint runs the multi-tenant migrations
(`migrate_schemas --shared` → `setup_public_tenant` → `migrate_schemas
--tenant`), `collectstatic`, then Daphne (HTTP + WebSocket on one port).

> **Replicas**: keep **1 replica**. The entrypoint runs migrations on boot and
> the in-process cleanup schedulers assume a single instance. To scale out,
> move migrations to a release step, set `RUN_CLEANUP_SCHEDULER` on only one
> instance (or use the `cleanup_*` management commands via cron), and make
> sure `REDIS_URL` is set so all replicas share the channel layer.

## 3. Environment variables

In the app service → Environment, set:

```env
DEBUG=False
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(64))">

# Domain (see step 4)
PUBLIC_DOMAIN=app.yourdomain.com
ALLOWED_HOSTS=app.yourdomain.com,.app.yourdomain.com

# Backing services (internal hostnames; check the credentials Easypanel generated)
DATABASE_URL=postgres://postgres:<password>@ready11_db:5432/<database>
REDIS_URL=redis://default:<password>@ready11_redis:6379/0

# Email — real SMTP (Resend, SES, Mailgun, Brevo…)
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587
EMAIL_HOST_USER=<user>
EMAIL_HOST_PASSWORD=<password>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@yourdomain.com

# Observability
LOG_FORMAT=json
SENTRY_DSN=<optional>
METRICS_TOKEN=<generate another secret — protects GET /metrics>
```

`CSRF_TRUSTED_ORIGINS` is derived automatically from `PUBLIC_DOMAIN`
(`https://PUBLIC_DOMAIN` + `https://*.PUBLIC_DOMAIN`).

## 4. Domains — the wildcard is the critical part

Each workspace lives on a subdomain (`acme.app.yourdomain.com`), so both the
apex of your app and the wildcard must reach the service:

**DNS** (at your DNS provider):

| Record | Name                 | Value            |
|--------|----------------------|------------------|
| A      | `app`                | server IP        |
| A      | `*.app`              | server IP        |

**Easypanel → app service → Domains**: add both `app.yourdomain.com` **and**
`*.app.yourdomain.com`, pointing to port 8000.

**TLS for the wildcard**: Let's Encrypt only issues wildcard certificates via
the **DNS-01 challenge** — the default HTTP challenge covers single names
only. Two working setups:

- **Cloudflare in front (simplest)**: proxy both records (orange cloud) and
  set SSL mode to **Full (strict)** with a Cloudflare **Origin Certificate**
  installed in Easypanel for `*.app.yourdomain.com`. Cloudflare's edge
  certificate covers the wildcard for visitors.
- **DNS-01 on the server**: configure Traefik's Let's Encrypt resolver with
  your DNS provider's API credentials so it can issue `*.app.yourdomain.com`
  directly. (Easypanel exposes Traefik config under Settings → Traefik.)

Quick test after setup: `https://app.yourdomain.com` (landing) and
`https://anything.app.yourdomain.com` (should 404/redirect to login with a
valid certificate — the subdomain only resolves to a workspace after one is
provisioned).

## 5. First access

1. Open a console on the app service (Easypanel → app → Console) and create
   the superuser:
   ```bash
   python manage.py createsuperuser
   ```
2. Log in at `https://app.yourdomain.com/admin/`, create a **Workspace
   invite** with no workspace selected (genesis invite) — the link is printed
   to the service logs.
3. Open the link, fill in name/company, and the first workspace + subdomain
   is provisioned.

## 6. Monitoring (optional but recommended)

Add two more services to the project:

**Prometheus** (App service from image `prom/prometheus:v3.8.0`)
- Mount a config file (Easypanel → Mounts → File) at
  `/etc/prometheus/prometheus.yml`, based on `docker/prometheus/prometheus.yml`
  with the production target:
  ```yaml
  scrape_configs:
    - job_name: django
      metrics_path: /metrics
      authorization:
        type: Bearer
        credentials: <same value as METRICS_TOKEN>
      static_configs:
        - targets: ['ready11_app:8000']
  ```
- No public domain needed — keep it internal.

**Grafana** (App service from image `grafana/grafana:12.4.0`)
- Env: `GF_SECURITY_ADMIN_PASSWORD=<strong password>` (and leave anonymous
  access disabled — don't copy the dev compose flags).
- Add a domain (e.g. `grafana.yourdomain.com`) if you want it reachable.
- Point its Prometheus datasource at `http://ready11_prometheus:9090` and
  import `docker/grafana/dashboards/django-overview.json` (Dashboards →
  Import), or mount the provisioning folders like the dev compose does.

Sentry (via `SENTRY_DSN`) complements this with per-error stack traces.

## 7. Production checklist recap

- [ ] `DEBUG=False`, strong `SECRET_KEY`, real `PUBLIC_DOMAIN`/`ALLOWED_HOSTS`
- [ ] `DATABASE_URL` and `REDIS_URL` pointing at the project services
- [ ] Real SMTP configured (invites and password reset depend on it)
- [ ] Wildcard DNS **and** wildcard TLS working
- [ ] `METRICS_TOKEN` set; Prometheus scraping with the bearer token
- [ ] Grafana with strong admin password, anonymous access off
- [ ] PostgreSQL backups scheduled (Easypanel → db service → Backups)
- [ ] GitHub branch protection on `main` (husky only guards locally)
- [ ] Sentry DSN (recommended)
