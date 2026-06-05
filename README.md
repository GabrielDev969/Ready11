# Ready11

📖 Também disponível em [Português](README.pt-br.md)

A **base project for B2B SaaS systems**: Django 6 + PostgreSQL with **schema-isolated multi-tenancy** (`django-tenants`), global accounts, role-based access control (RBAC), invite-only onboarding, brute-force protection (`django-axes`) and **internationalization** (English + Brazilian Portuguese, auto-detected). Runs locally (PostgreSQL via Docker) or fully in containers.

This guide is written for someone who **just cloned the repository** and has never run the project before. There are separate instructions for **Windows** and **macOS**.

> The home page (`/`) is a presentation landing page that also summarizes installation.

---

## Table of contents

- [Stack](#stack)
- [Prerequisites](#prerequisites)
- [Environment variables](#environment-variables)
- [Option A — Run locally (recommended for development)](#option-a--run-locally-recommended-for-development)
  - [macOS](#macos)
  - [Windows](#windows)
- [Option B — Run everything in Docker](#option-b--run-everything-in-docker)
- [Multi-tenancy: creating the first workspace](#multi-tenancy-creating-the-first-workspace)
- [Useful Django commands](#useful-django-commands)
- [Project structure](#project-structure)
- [Troubleshooting (FAQ)](#troubleshooting-faq)

---

## Stack

| Component          | Version / Technology                |
|--------------------|-------------------------------------|
| Language           | Python 3.12                         |
| Framework          | Django 6.0                          |
| Multi-tenancy      | django-tenants (schema per tenant)  |
| Database           | PostgreSQL 17                       |
| Security           | django-axes (brute-force protection)|
| Front-end          | Django Templates + Tailwind CSS v3  |
| i18n               | en + pt-BR (auto-detected)          |
| Server (prod)      | Gunicorn                            |
| Static files       | WhiteNoise (manifest)               |
| Container          | Docker / Docker Compose             |

Full Python dependencies in [`requirements.txt`](requirements.txt); front-end dependencies in [`package.json`](package.json).

---

## Prerequisites

Before you start, install:

### For everyone
- **Git** — https://git-scm.com/downloads
- **Docker Desktop** (needed to run the PostgreSQL database) — https://www.docker.com/products/docker-desktop/

### To run locally (Option A)
- **Python 3.12** — https://www.python.org/downloads/
  - **Windows:** during installation, check **"Add Python to PATH"**.
  - **macOS:** recommended via [Homebrew](https://brew.sh): `brew install python@3.12`
- **Node.js 18+** (to compile the CSS with Tailwind) — https://nodejs.org/
- **GNU gettext** (to compile the i18n translations)
  - **macOS:** `brew install gettext`
  - **Windows:** bundled with Git for Windows, or install the gettext package.

> To check what's already installed:
> ```bash
> git --version
> docker --version
> python --version   # on Windows usually: python
> python3 --version  # on macOS/Linux usually: python3
> ```

---

## Environment variables

The project reads its configuration from **environment variables**. There's an example file: [`.env.example`](.env.example).

> The project loads the `.env` file automatically (via `python-dotenv`), so for local development you only need to copy the example — no need to export variables by hand.

Create your own `.env` from the example:

**macOS / Linux:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Most relevant variables (see `.env.example` for the full list):

| Variable        | Description                                                       | Example                                                |
|-----------------|-------------------------------------------------------------------|--------------------------------------------------------|
| `DATABASE_URL`  | PostgreSQL connection URL. If empty in dev, uses the local fallback. Required in production. | `postgres://postgres:postgres@127.0.0.1:5432/ready_db` |
| `DEBUG`         | Django debug mode. Defaults to `False` (production-safe).         | `True`                                                 |
| `SECRET_KEY`    | Django secret key. Required when `DEBUG=False`.                   | `change-me`                                            |
| `ALLOWED_HOSTS` | Allowed hosts, comma-separated.                                   | `127.0.0.1,localhost,.localhost`                       |
| `PUBLIC_DOMAIN` | Base domain used to build tenant subdomains.                      | `localhost`                                            |

> ⚠️ In production (`DEBUG=False`), `SECRET_KEY` and `DATABASE_URL` are **mandatory** — the app refuses to boot without them.
>
> 💡 `docker-compose.yml` creates the database named **`ready_db`** with user/password **`postgres`/`postgres`**. The default `.env.example` already matches this.

---

## Option A — Run locally (recommended for development)

Here **PostgreSQL runs in Docker** and the **Django app runs on your machine** (faster to develop, with auto-reload).

### macOS

```bash
# 1. Enter the project folder (after cloning)
cd Ready11

# 2. Start the PostgreSQL database in the background
docker compose up -d

# 3. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install the Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create your .env (loaded automatically by Django)
cp .env.example .env
# For local dev the defaults work out of the box (DEBUG=True uses the docker-compose Postgres).

# 6. Build the Tailwind CSS
npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

# 7. Compile the translations (en + pt-BR)
python manage.py compilemessages

# 8. Apply the shared-schema migrations and create the public tenant
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant

# 9. (Optional) Create a superuser for /admin
python manage.py createsuperuser

# 10. Start the development server
python manage.py runserver
```

Open: **http://127.0.0.1:8000** (landing) • Admin: **http://127.0.0.1:8000/admin**

> To re-activate the virtualenv in a new session: `source venv/bin/activate`
> The `.env` file is loaded automatically — no need to export variables manually.

---

### Windows

Use **PowerShell** (recommended).

```powershell
# 1. Enter the project folder (after cloning)
cd Ready11

# 2. Start the PostgreSQL database in the background
docker compose up -d

# 3. Create and activate a Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 4. Install the Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Create your .env (loaded automatically by Django)
Copy-Item .env.example .env
# For local dev the defaults work out of the box (DEBUG=True uses the docker-compose Postgres).

# 6. Build the Tailwind CSS
npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

# 7. Compile the translations (en + pt-BR)
python manage.py compilemessages

# 8. Apply the shared-schema migrations and create the public tenant
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant

# 9. (Optional) Create a superuser for /admin
python manage.py createsuperuser

# 10. Start the development server
python manage.py runserver
```

Open: **http://127.0.0.1:8000** (landing) • Admin: **http://127.0.0.1:8000/admin**

> **If PowerShell blocks the venv activation** with *"execution of scripts is disabled"*, run once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Then activate again.

> **Using Command Prompt (CMD) instead of PowerShell?** The commands differ:
> - Activate venv: `venv\Scripts\activate.bat`

---

## Option B — Run everything in Docker

Here you start the database with Docker Compose and run the app from the Docker image (using Gunicorn, like production).

> This project's `docker-compose.yml` only brings up the **database**. For the app we build the image from the [`Dockerfile`](Dockerfile) and connect it to the same network as the database.

```bash
# 1. Start the database
docker compose up -d

# 2. Build the application image
docker build -t ready11-app .

# 3. Run the app container connected to the compose network
#    (find the network name with: docker network ls | grep ready)
docker run --rm -p 8000:8000 \
  --network ready11_default \
  -e DATABASE_URL="postgres://postgres:postgres@django_postgres_db:5432/ready_db" \
  -e SECRET_KEY="change-this-production-key" \
  -e DEBUG="False" \
  -e ALLOWED_HOSTS="127.0.0.1,localhost" \
  ready11-app
```

> **Why `django_postgres_db` as the host?** Inside the Docker network, containers reach each other by name. The database container is named `django_postgres_db` (defined in `docker-compose.yml`).
>
> [`entrypoint.sh`](entrypoint.sh) automatically runs the migrations (`migrate_schemas --shared`), ensures the public tenant, collects static files and starts **Gunicorn**. The `Dockerfile` compiles the CSS (Tailwind) and the translations (`compilemessages`) at build time.

Open: **http://127.0.0.1:8000**

---

## Multi-tenancy: creating the first workspace

Entry is **invite-only**. To create the first company (workspace):

1. Create a superuser and open `/admin`.
2. Under **Workspace invites**, create an invite **with no workspace** (a "genesis" invite). The link is printed to the server console.
3. Open the link, fill in your name and **Company name** — the backend creates an **isolated schema** in PostgreSQL and a subdomain (`company.localhost`).
4. The owner accesses the workspace on the subdomain and invites the team under **/team/**.

> **Subdomains in dev:** browsers resolve `*.localhost` to `127.0.0.1` automatically (e.g. `http://mycompany.localhost:8000/home/`). `ALLOWED_HOSTS` already includes `.localhost`.

> **Language:** the site detects the browser language (English or Portuguese) and has a switcher in the header. Source strings are in English; pt-BR comes from the translations in `locale/`.

Create a superuser with the app running in Docker:
```bash
docker run --rm -it \
  --network ready11_default \
  -e DATABASE_URL="postgres://postgres:postgres@django_postgres_db:5432/ready_db" \
  -e SECRET_KEY="anything" \
  ready11-app python manage.py createsuperuser
```

---

## Useful Django commands

> Run with the `venv` active (the `.env` is loaded automatically).

| Command                                      | What it does                                          |
|----------------------------------------------|-------------------------------------------------------|
| `python manage.py runserver`                 | Starts the development server.                        |
| `python manage.py migrate_schemas --shared`  | Applies migrations to the public (shared) schema.     |
| `python manage.py migrate_schemas --tenant`  | Applies migrations to the tenant schemas.             |
| `python manage.py setup_public_tenant`       | Creates the public tenant/domain (idempotent).        |
| `python manage.py makemigrations`            | Creates new migrations from model changes.            |
| `python manage.py createsuperuser`           | Creates an admin user.                                |
| `python manage.py makemessages -l pt_BR`     | Extracts/updates strings for translation.             |
| `python manage.py compilemessages`           | Compiles the translations (`.po` → `.mo`).            |
| `npx tailwindcss -i input.css -o static/css/output.css` | Rebuilds the Tailwind CSS.                 |
| `python manage.py shell`                     | Opens a Python shell with the Django context.         |

Useful Docker commands:

| Command                     | What it does                                       |
|-----------------------------|----------------------------------------------------|
| `docker compose up -d`      | Starts the database in the background.             |
| `docker compose down`       | Stops the containers (keeps the data).             |
| `docker compose down -v`    | Stops the containers **and deletes** the DB data.  |
| `docker compose logs -f db` | Follows the database logs in real time.            |
| `docker ps`                 | Lists running containers.                          |

---

## Project structure

```
Ready11/
├── Ready11/                 # Django configuration package (settings, urls, wsgi, asgi)
├── core/                    # Public landing page + health check
├── users/                   # Global custom user, auth, registration, login
├── tenants/                 # Multi-tenancy: workspaces, domains, roles, memberships, invites
├── templates/               # Django templates (Tailwind), organized by app
├── locale/pt_BR/            # Brazilian Portuguese translations
├── static/ , input.css , tailwind.config.js   # Front-end (Tailwind)
├── manage.py                # Django admin CLI
├── requirements.txt         # Python dependencies
├── package.json             # Front-end dependencies
├── Dockerfile               # App image (Node CSS build + Python/Gunicorn)
├── docker-compose.yml       # PostgreSQL service
├── entrypoint.sh            # migrations + Gunicorn on container start
├── .env.example             # Environment variables template
├── .dockerignore
└── .gitignore
```

---

## Troubleshooting (FAQ)

**`django.db.utils.OperationalError: could not connect to server`**
The database isn't up or `DATABASE_URL` is wrong. Make sure `docker compose up -d` ran and the `django_postgres_db` container is active (`docker ps`).

**`port 5432 is already allocated`**
There's already a PostgreSQL on port 5432 (another container or local install). Stop the conflicting service or change the port mapping in `docker-compose.yml` (e.g. `"5433:5432"`) and adjust `DATABASE_URL`.

**`docker: command not found` or Docker connection error**
Open **Docker Desktop** and wait for it to fully start before running the commands.

**`'python' is not recognized` (Windows)**
Reinstall Python with **"Add Python to PATH"** checked, or use the `py` launcher (e.g. `py -m venv venv`).

**`docker compose` doesn't work, but `docker-compose` does**
Older versions use the hyphen. Replace `docker compose` with `docker-compose`.

**`ImproperlyConfigured: SECRET_KEY ... required when DEBUG=False`**
You're running in production mode without the required env vars. Set `SECRET_KEY` and `DATABASE_URL`, or set `DEBUG=True` for local development.
