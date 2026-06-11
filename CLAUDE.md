# CLAUDE.md

## What this is

Ready11 is a **B2B SaaS starter template** (Django 6 + PostgreSQL) meant to be forked via GitHub Template into new products. To start a new project from it, run `python scripts/bootstrap.py MyProject` — see `docs/TEMPLATE_USAGE.md`. The SaaS plumbing (auth, tenants, RBAC, notifications, audit) is done; product-specific apps get added later.

## Architecture

- **Multi-tenancy**: `django-tenants`, one PostgreSQL **schema per workspace**. `SHARED_APPS` (public schema: users, tenants, notifications, audit, core) vs `TENANT_APPS` (replicated per schema — business apps go here) in `Ready11/settings.py`. Requests are routed to a schema by subdomain (`Domain` model) under `PUBLIC_DOMAIN`.
- **Identity**: global `CustomUser` (email login, no username) in `apps/users/`. One user can belong to many workspaces via `WorkspaceMembership` (`apps/tenants/models.py`).
- **RBAC**: `Role.permissions` is a JSON array of strings (`users.invite`, `roles.edit`, …; umbrella perms like `users.manage` expand via `expand_permissions`). Views guard with `@tenant_permission_required('perm.string')` from `apps/tenants/decorators.py`, which also injects `request.tenant_membership`.
- **Onboarding is invite-only**: a *genesis* invite (created in Django admin with no workspace) provisions a new workspace via `create_workspace()` in `apps/tenants/services.py`; team invites add members to an existing workspace.
- **Services layer**: business logic lives in `apps/<app>/services.py`; views stay thin. Follow this for new code.
- **Realtime**: Django Channels + Redis (in-memory fallback in dev) pushes notifications over `ws/notifications/`.
- **Audit**: call `apps.audit.services.log_action()` for any state-changing user action.
- **Metrics**: `django-prometheus` exposes `GET /metrics` (optionally gated by `METRICS_TOKEN`); Prometheus (:9090) + Grafana (:3000, dashboard "Django — Overview") ship in docker-compose. DB metrics come from `ORIGINAL_BACKEND` pointing django-tenants at the instrumented postgres backend. See `docs/OBSERVABILITY.md`.
- **Cleanup schedulers**: notifications, audit logs and invites have retention purges. Pattern: a service function + management command (`cleanup_notifications`, `cleanup_audit_logs`, `cleanup_invites`) + optional in-process daemon scheduler (see `apps/notifications/scheduler.py` and `apps.py` guards). Copy that trio to add another.
- **Middleware order matters**: `TenantMainMiddleware` first, `AxesMiddleware` last (see `settings.py`).

## Commands

```
make setup       # pip install + npm install + npm run build (Tailwind)
make docker-up   # PostgreSQL 17 + Redis + Mailpit — REQUIRED before tests/runserver
make run         # runserver
make migrate     # migrate_schemas --shared, setup_public_tenant, migrate_schemas --tenant
make test        # Django test suite (real PostgreSQL)
make coverage    # coverage gate in CI is 45%
make lint        # ruff
make css         # Tailwind watch mode (npm run dev)
make messages && make compile   # i18n extract/compile (pt_BR)
make seed        # dev superuser admin@example.com
```

## Conventions

- **i18n**: all user-facing strings in **English**, wrapped in `gettext`/`gettext_lazy`/`{% trans %}`; pt-BR translations live in `locale/pt_BR/` (`make messages` + `make compile`).
- **Commits**: Conventional Commits enforced by commitlint. Direct pushes to `main` are blocked by a husky pre-push hook — work on feature branches.
- **Linting**: ruff (line length 120). Migrations and `settings.py` have relaxed rules (`ruff.toml`).
- **Tests**: plain Django `TestCase` in `apps/<app>/tests.py`. The custom `Ready11.test_runner.TenantAwareTestRunner` bootstraps the public tenant and a `testserver` domain — don't create it yourself. Creating a `Workspace` in a test builds a real PG schema (slow); keep workspace-creating tests to a minimum. Don't assert against `PUBLIC_DOMAIN`-derived literals — use `settings.TENANT_BASE_DOMAIN` (local `.env` may set `lvh.me`).

## Gotchas

- Use `migrate_schemas`, **never** plain `migrate` (multi-tenant).
- husky v9 has no `--version` flag — running `npx husky --version` creates a junk `--version/` directory at the repo root.
- `axes` is the first auth backend; tests/dev flows that authenticate must pass `request` to `authenticate()` (Django does this in views already).
- `design-system/` is gitignored (local reference only); the live design tokens are in `tailwind.config.js` + `input.css`.
- The Dockerfile builds CSS in a Node stage (`npm ci --ignore-scripts` — husky's prepare hook fails without `.git`).
