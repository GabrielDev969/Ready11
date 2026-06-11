# Ready11

📖 Também disponível em [Português](README.pt-br.md)

A **base project for B2B SaaS systems**: Django 6 + PostgreSQL with **schema-isolated multi-tenancy** (`django-tenants`), global accounts, role-based access control (RBAC), invite-only onboarding, real-time notifications (WebSocket), audit log, brute-force protection and **i18n** (English + Brazilian Portuguese). CI/CD with GitHub Actions included.

> This guide is for someone who **just cloned the repository** and has never run the project before.

> 🚀 **Starting a new project from this template?** See [docs/TEMPLATE_USAGE.md](docs/TEMPLATE_USAGE.md) — create the repo from the GitHub Template, run `python scripts/bootstrap.py MyProject` and follow the printed steps.

---

## Table of contents

- [Using as a template](docs/TEMPLATE_USAGE.md)
- [Stack](#stack)
- [Prerequisites](#prerequisites)
- [Quick start (Makefile)](#quick-start-makefile)
- [Environment variables](#environment-variables)
- [Option A — Run locally](#option-a--run-locally-recommended-for-development)
- [Option B — Run everything in Docker](#option-b--run-everything-in-docker)
- [First workspace (multi-tenancy)](#first-workspace-multi-tenancy)
- [Day-to-day workflow](#day-to-day-workflow)
- [When you make changes](#when-you-make-changes)
- [Commands reference](#commands-reference)
- [Project structure](#project-structure)
- [CI/CD](#cicd)
- [Production checklist](#production-checklist)
- [Troubleshooting](#troubleshooting)

---

## Stack

| Component           | Technology                                      |
|---------------------|-------------------------------------------------|
| Language            | Python 3.12                                     |
| Framework           | Django 6.0                                      |
| Multi-tenancy       | django-tenants (schema per tenant)              |
| Database            | PostgreSQL 17                                   |
| Real-time           | Django Channels + Redis (WebSocket)             |
| Security            | django-axes (brute-force) + HSTS + CSRF         |
| Error monitoring    | Sentry (optional, via `SENTRY_DSN`)             |
| Metrics             | Prometheus + Grafana ([docs](docs/OBSERVABILITY.md)) |
| Front-end           | Django Templates + Tailwind CSS v3              |
| i18n                | English (source) + pt-BR (auto-detected)        |
| Server (prod)       | Daphne (ASGI) / Gunicorn                        |
| Static files        | WhiteNoise (compressed + manifest in prod)      |
| Cache               | Redis (`django.core.cache.backends.redis`)      |
| Audit log           | Custom `audit` app (shared schema)              |
| Design system       | GSS Design System (Tailwind component classes)  |
| Linting             | Ruff                                            |
| Commit convention   | Conventional Commits (commitlint)               |
| CI/CD               | GitHub Actions (lint, test, security, coverage) |
| Container           | Docker / Docker Compose                         |

---

## Prerequisites

### For everyone
- **Git** — https://git-scm.com/downloads
- **Docker Desktop** (runs PostgreSQL + Redis) — https://www.docker.com/products/docker-desktop/

### To run locally (Option A)
- **Python 3.12** — https://www.python.org/downloads/
  - Windows: check **"Add Python to PATH"** during install
  - macOS: `brew install python@3.12`
- **Node.js 18+** (Tailwind CSS) — https://nodejs.org/
- **GNU gettext** (i18n translations)
  - macOS: `brew install gettext`
  - Windows: bundled with Git for Windows

---

## Key concepts

Three ideas that will save you time as a newcomer:

**Workspaces (tenants)** — every company that signs up gets its own **isolated PostgreSQL schema**. Data from company A and company B never mixes at the database level. `django-tenants` routes each request to the right schema based on the subdomain (`acme.yourdomain.com` → `acme` schema). The `public` schema holds shared data: users, audit logs, notifications.

**Roles & permissions (RBAC)** — each workspace manages its own roles. A role carries a list of permission strings (e.g. `roles.edit`, `users.invite`). Every workspace member has exactly one role. The `Owner` role is a system role — it cannot be edited or deleted. All other roles are fully customisable.

**Invite-only signup** — new workspaces and new members both enter through invite links. There is no self-service registration page. A superuser creates a **genesis invite** (from Django admin, with no workspace selected) to provision a new company. Once inside, workspace owners invite their team via `/team/`.

---

## Quick start (Makefile)

The fastest way to get running after cloning:

```bash
# 1. Start the database + Redis
make docker-up

# 2. Create venv and install all dependencies
python3 -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
make setup                      # pip install + npm install + build CSS

# 3. Copy the environment file
cp .env.example .env            # Windows: Copy-Item .env.example .env
# Edit .env and set at least: DEBUG=True (other defaults work out of the box)

# 4. Apply migrations and create the public tenant
make migrate

# 5. Create a dev superuser (admin@example.com / Admin1234!)
make seed

# 6. Start the server
make run
```

Open: **http://127.0.0.1:8000**

> **Git hooks install automatically** when `npm install` runs. No extra step needed.
> To also enable the deeper file-level checks (ruff, whitespace, etc.):
> ```bash
> make hooks    # installs pre-commit hooks
> ```

---

## Environment variables

The project reads all configuration from environment variables and loads `.env` automatically via `python-dotenv`.

```bash
cp .env.example .env
```

Most important variables:

| Variable          | Description                                                | Default / Example                              |
|-------------------|------------------------------------------------------------|------------------------------------------------|
| `DEBUG`           | Django debug mode. Never `True` in production.             | `True` (dev)                                   |
| `SECRET_KEY`      | Required when `DEBUG=False`. Generate with `python manage.py generate_secret_key`. | *(must set in prod)* |
| `DATABASE_URL`    | PostgreSQL URL. Empty in dev falls back to the docker-compose DB. | `postgres://postgres:postgres@127.0.0.1:5432/ready_db` |
| `REDIS_URL`       | Redis URL for Channels + cache. Optional in single-process dev. | `redis://localhost:6379/0` |
| `PUBLIC_DOMAIN`   | Base domain for tenant subdomains.                         | `localhost`                                    |
| `SENTRY_DSN`      | Sentry project DSN. Leave empty to disable.                | *(optional)*                                   |
| `LOG_FORMAT`      | `text` (dev) or `json` (production/CloudWatch/Loki).       | `text`                                         |
| `AUDIT_CLEANUP_ENABLED` | Run the built-in audit log cleanup scheduler. Set `False` if you schedule `cleanup_audit_logs` externally. | `True` |
| `NOTIFICATION_CLEANUP_ENABLED` | Run the built-in notification cleanup scheduler. | `True`                        |

> In production (`DEBUG=False`), `SECRET_KEY` and `DATABASE_URL` are **mandatory** — the app refuses to boot without them.

---

## Option A — Run locally (recommended for development)

PostgreSQL + Redis run in Docker; Django runs on your machine (fast, auto-reload).

### macOS / Linux

```bash
cd Ready11
make docker-up

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Open .env and set DEBUG=True — the other defaults work out of the box.

npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

python manage.py compilemessages
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant
python manage.py seed           # creates admin@example.com / Admin1234!

python manage.py runserver
```

### Windows (PowerShell)

```powershell
cd Ready11
make docker-up

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
# Open .env and set DEBUG=True

npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

python manage.py compilemessages
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant
python manage.py seed

python manage.py runserver
```

> If PowerShell blocks venv activation: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

## Option B — Run everything in Docker

```bash
make docker-up
docker build -t ready11-app .
docker run --rm -p 8000:8000 \
  --network ready11_default \
  -e DATABASE_URL="postgres://postgres:postgres@django_postgres_db:5432/ready_db" \
  -e SECRET_KEY="change-this-production-key" \
  -e DEBUG="False" \
  -e ALLOWED_HOSTS="127.0.0.1,localhost" \
  ready11-app
```

`entrypoint.sh` runs migrations, collects static files and starts Gunicorn automatically.

---

## First workspace (multi-tenancy)

Entry is **invite-only**. To create the first company workspace:

1. Log in to `/admin` with your superuser (`make seed` creates one).
2. Under **Workspace invites**, create an invite **with no workspace** (a "genesis" invite). The link is printed to the server console.
3. Open the link, fill in your name and **company name** — the backend creates an **isolated PostgreSQL schema** and a subdomain (`company.localhost`).
4. The workspace owner invites the team via **/team/**.

> **Subdomains in dev:** browsers resolve `*.localhost` to `127.0.0.1` automatically, e.g. `http://acme.localhost:8000/home/`. `ALLOWED_HOSTS` already includes `.localhost`.

---

## Day-to-day workflow

### Git hooks

Hooks are managed by **husky** and install automatically when `npm install` runs. No manual step required.

| Hook | Trigger | What it does |
|---|---|---|
| `pre-commit` | every `git commit` | Runs `pre-commit` checks (ruff, whitespace, etc.) if installed; falls back to `ruff check .` |
| `commit-msg` | every `git commit` | Validates the message format with commitlint |

To also enable the full pre-commit suite (ruff + whitespace + YAML checks):
```bash
make hooks    # runs: pre-commit install
```

To run all file checks manually without committing:
```bash
pre-commit run --all-files
```

### Running tests

```bash
make test           # run the full test suite
make coverage       # run tests + show coverage report
```

Tests use Django's built-in `TestCase`. They connect to a real PostgreSQL test database (created and destroyed automatically). Make sure `make docker-up` is running first.

### Viewing emails in dev

Start Mailpit (included in `docker-compose.yml`):
```bash
make docker-up
```

In your `.env`:
```
EMAIL_HOST=localhost
EMAIL_PORT=1025
```

Open **http://localhost:8025** to see all emails sent by the app (invites, password resets, etc.).

### Lint

```bash
make lint           # ruff check .
```

Ruff is also enforced in CI. Configure rules in `ruff.toml`.

### Commit convention

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

feat: add workspace export
fix: correct invite expiry date
docs: update README setup steps
refactor: extract permission check to decorator
test: add coverage for audit log service
chore: upgrade Django to 6.1
```

Allowed types: `feat` `fix` `docs` `style` `refactor` `test` `chore` `perf` `ci` `build` `revert`

Pre-commit hooks will warn you if the format is wrong. The CI also validates commits on pull requests.

---

## When you make changes

### Added or changed a model

```bash
python manage.py makemigrations
make migrate        # applies to shared schema + all tenant schemas
```

> Models in `SHARED_APPS` (like `audit`, `users`, `notifications`) live in the public schema.
> Models in `TENANT_APPS` live in each company's schema.

### Changed a template or UI component

The project uses the **GSS Design System** — a set of Tailwind-based component classes (`gss-btn`, `gss-card`, `gss-pill`, `gss-input`, etc.) defined in `input.css` under `@layer components`. Colours and font tokens live in `tailwind.config.js`. The reference documentation is in `design-system/`.

After editing templates or `input.css`, rebuild the CSS:
```bash
make css          # watch mode — rebuilds on every save
# or once:
npx tailwindcss -i input.css -o static/css/output.css --minify
```

> **Rule for pills:** always use both the base class and the colour variant together: `gss-pill gss-pill-neutral`. The colour-only class (`gss-pill-neutral`) does not produce the pill shape on its own.

### Added a new translatable string

```bash
make messages       # extracts new strings → locale/pt_BR/LC_MESSAGES/django.po
```

Open `locale/pt_BR/LC_MESSAGES/django.po`, find the new `msgid` entries (they have empty `msgstr`), and add the pt-BR translations. Then:

```bash
make compile        # compiles .po → .mo (required for the strings to show up)
```

> **Rule:** source strings always in English. Portuguese goes only in the `.po` file.

### Added a new dependency

```bash
pip install <package>
pip freeze | grep <package>    # copy the exact pinned version
# Manually add it to requirements.txt (keep alphabetical order)
```

For dev-only tools (testing, linting):
```bash
# Add to requirements-dev.txt instead
```

### Created a new app

All apps live inside `apps/`. Create the app there and update its `AppConfig.name`:

```bash
cd apps
python ../manage.py startapp myapp
```

Then edit `apps/myapp/apps.py`:
```python
class MyappConfig(AppConfig):
    name = 'apps.myapp'   # ← must include the "apps." prefix
```

And in `Ready11/settings.py`, add to `SHARED_APPS` (data shared across all tenants) or `TENANT_APPS` (isolated per workspace):
```python
SHARED_APPS = (
    ...
    'apps.myapp',
)
```

Finally:
1. Run `python manage.py makemigrations myapp` (Django uses the `app_label` — the last part — as the migration target)
2. Add a URL include in `Ready11/urls.py` or the tenant urlconf
3. Write tests in `apps/myapp/tests.py`

### After pulling changes from the team

```bash
git pull
pip install -r requirements.txt     # install any new dependencies
make migrate                         # apply new migrations
make compile                         # recompile translations if .po changed
make css                             # rebuild CSS if templates changed
```

---

## Commands reference

### Makefile shortcuts

| Command           | What it does                                      |
|-------------------|---------------------------------------------------|
| `make setup`      | Install Python + Node deps and build CSS          |
| `make run`        | Start the development server                      |
| `make migrate`    | Apply all migrations (shared + public + tenant)   |
| `make seed`       | Create dev superuser (`admin@example.com`)        |
| `make test`       | Run the test suite                                |
| `make coverage`   | Run tests and show coverage report                |
| `make lint`       | Run Ruff linter                                   |
| `make messages`   | Extract translatable strings (pt-BR)              |
| `make compile`    | Compile `.po` → `.mo` translation files           |
| `make css`        | Watch and rebuild Tailwind CSS                    |
| `make check`      | Django deployment security check                  |
| `make docker-up`  | Start PostgreSQL + Redis + Mailpit                |
| `make docker-down`| Stop Docker services                              |
| `make clean`      | Remove `.pyc`, `__pycache__`, `staticfiles/`      |

### Django management commands

| Command                                          | What it does                                      |
|--------------------------------------------------|---------------------------------------------------|
| `python manage.py runserver`                     | Dev server                                        |
| `python manage.py migrate_schemas --shared`      | Migrate public schema                             |
| `python manage.py migrate_schemas --tenant`      | Migrate all tenant schemas                        |
| `python manage.py setup_public_tenant`           | Create/update public tenant (idempotent)          |
| `python manage.py seed`                          | Create dev superuser                              |
| `python manage.py makemigrations`                | Create migration files from model changes         |
| `python manage.py makemessages -l pt_BR`         | Extract strings for translation                   |
| `python manage.py compilemessages`               | Compile `.po` → `.mo`                             |
| `python manage.py cleanup_audit_logs`            | Delete audit logs older than 90 days              |
| `python manage.py cleanup_notifications`         | Delete old notifications                          |
| `python manage.py check --deploy`                | Check production configuration                    |
| `python manage.py shell`                         | Django interactive shell                          |

---

## Project structure

```
Ready11/
├── Ready11/                  # Django config package (settings, urls, asgi)
├── apps/                     # All Django apps live here
│   ├── core/                 # Public landing page, health check, error pages, robots.txt
│   │   └── middleware.py     # RequestLogging, PublicOnly, WorkspaceTZ, UserLanguage
│   ├── users/                # Global user model, auth, registration, password reset, 2FA
│   ├── tenants/              # Workspaces, domains, RBAC, memberships, invites
│   ├── notifications/        # In-app notifications (WebSocket + Redis)
│   └── audit/                # Workspace audit log (shared schema)
├── templates/                # Django templates organized by app
│   ├── users/                # login, register, password reset, email templates
│   ├── tenants/              # workspace, team, roles, invite
│   ├── audit/                # audit log list
│   ├── notifications/        # notification partials
│   ├── partials/             # sidebar, header, nav
│   ├── 404.html, 403.html    # custom error pages
│   └── 500.html              # standalone error page (no DB access)
├── locale/pt_BR/             # Brazilian Portuguese translations
├── static/                   # Static source files
├── design-system/            # GSS Design System reference (tokens, component docs)
├── input.css                 # Tailwind CSS entry point (component classes under @layer components)
├── tailwind.config.js        # Tailwind configuration (GSS colour tokens, fonts, shadows)
├── manage.py
├── requirements.txt          # Production Python dependencies
├── requirements-dev.txt      # Dev/test dependencies (ruff, coverage, bandit…)
├── Dockerfile
├── docker-compose.yml        # PostgreSQL + Redis + Mailpit
├── entrypoint.sh             # Container entrypoint (migrations → Gunicorn)
├── Makefile                  # Development shortcuts
├── ruff.toml                 # Ruff linter configuration
├── commitlint.config.js      # Conventional Commits rules
├── .pre-commit-config.yaml   # Pre-commit hooks (ruff, whitespace, yaml…)
├── .github/workflows/ci.yml  # CI: lint, commitlint, test+coverage, pip-audit, security
├── .env.example
├── .dockerignore
└── .gitignore
```

---

## CI/CD

Every push to `main` and every pull request runs these GitHub Actions jobs:

| Job                | Triggers    | What it checks                                            |
|--------------------|-------------|-----------------------------------------------------------|
| `lint`             | push + PR   | Ruff (code style) + Bandit (SAST security scan)           |
| `commitlint`       | PR only     | All commits follow Conventional Commits format            |
| `test`             | push + PR   | Django test suite + coverage ≥ 60% + uploads `coverage.xml` |
| `dependency-audit` | push + PR   | `pip-audit` — no known CVEs in `requirements.txt`         |
| `security-check`   | push + PR   | `manage.py check --deploy` with `DEBUG=False`             |

The test job spins up a real PostgreSQL 17 container. The coverage report is uploaded as an artifact on every run.

---

## Production checklist

Before going live with real users:

- [ ] `DEBUG=False` + strong `SECRET_KEY` set. Run `make check` — no warnings.
- [ ] `DATABASE_URL` pointing to production PostgreSQL.
- [ ] `PUBLIC_DOMAIN` set to your real domain + DNS **wildcard** record (`*.yourdomain.com`).
- [ ] `REDIS_URL` set — required for real-time notifications to work across multiple server replicas.
- [ ] `EMAIL_*` SMTP configured — otherwise invites and password reset emails won't send.
- [ ] `SENTRY_DSN` set for error monitoring.
- [ ] `LOG_FORMAT=json` for structured logs (CloudWatch, Grafana Loki, Datadog).
- [ ] HTTPS terminated by your reverse proxy (Nginx/Traefik/Easypanel). The app enforces HSTS and secure cookies automatically when `DEBUG=False`.
- [ ] Cleanup jobs run automatically via built-in schedulers (`AUDIT_CLEANUP_ENABLED=True` and `NOTIFICATION_CLEANUP_ENABLED=True`). To hand off to an external cron instead, set both to `False` and schedule `manage.py cleanup_audit_logs` and `manage.py cleanup_notifications`.
- [ ] Migrations on deploy: `entrypoint.sh` runs `migrate_schemas --shared` + `--tenant` — every tenant schema is migrated. This scales linearly with tenant count.

### Scaling notes
- **Tenant provisioning is synchronous today** — schema creation runs in the HTTP request. Fine at low signup volume; move to a background task when volume grows.
- **Schema-per-tenant** works well into the low thousands. Far beyond that, per-deploy migrations and `pg_dump` become heavy.
- For high HTTP load you can split the HTTP workers from the WebSocket process; the base ships a single `daphne` serving both.

---

## Troubleshooting

**`could not connect to server` (PostgreSQL)**
Run `make docker-up` and confirm the `django_postgres_db` container is running (`docker ps`).

**`port 5432 is already allocated`**
Stop the conflicting PostgreSQL service, or change the port mapping in `docker-compose.yml` (e.g. `"5433:5432"`) and update `DATABASE_URL`.

**`Missing staticfiles manifest entry for 'css/output.css'`**
Build the CSS first: `npx tailwindcss -i input.css -o static/css/output.css --minify`. This only happens in production mode (`DEBUG=False`) — in dev and CI tests the plain static storage is used automatically.

**`docker: command not found`**
Open **Docker Desktop** and wait for it to fully start before running any `docker` commands.

**`'python' is not recognized` (Windows)**
Reinstall Python with **"Add Python to PATH"** checked, or use the `py` launcher (`py -m venv venv`).

**`ImproperlyConfigured: SECRET_KEY required when DEBUG=False`**
Set `SECRET_KEY` and `DATABASE_URL` in `.env`, or set `DEBUG=True` for local development.

**`ValueError: Missing staticfiles manifest` in tests**
Tests set `DEBUG=True` automatically; with that, the plain `StaticFilesStorage` is used (no manifest needed). If you see this error in tests, confirm `DEBUG=True` is set in the CI environment.
