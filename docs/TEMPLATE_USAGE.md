# Using Ready11 as a template

Ready11 is meant to be the starting point for new B2B SaaS projects. This guide covers how to spin up a new project from it and what to customize afterwards.

## 1. Create the new repository

**Option A — GitHub Template (recommended).** Mark this repository as a template once (GitHub → Settings → check **Template repository**). Then either click **Use this template** on the repo page or run:

```bash
gh repo create my-project --template GabrielDev969/Ready11 --private --clone
cd my-project
```

**Option B — Plain clone.**

```bash
git clone https://github.com/GabrielDev969/Ready11.git my-project
cd my-project
rm -rf .git && git init && git add -A && git commit -m "chore: import Ready11 template"
```

## 2. Rename the project

Run the bootstrap script with your project name (a valid Python identifier — it becomes the Django package name):

```bash
python scripts/bootstrap.py MyProject          # or: make rename name=MyProject
```

Use `--dry-run` first to preview which files change. The script replaces every `Ready11`/`ready11` token in tracked files (settings, CI, Docker, templates, translations), renames the docker/database identifiers (`ready_db` → `myproject_db`, etc.) and runs `git mv Ready11 MyProject`. It refuses to run on a dirty working tree so the rename lands as a single reviewable commit.

Then follow the steps the script prints:

```bash
npm install                       # refresh package-lock.json with the new name
cp .env.example .env              # review PUBLIC_DOMAIN and secrets
make setup && make docker-up && make migrate && make seed
make messages && make compile     # refresh pt-BR translations for the new brand
git add -A && git commit -m "chore: bootstrap MyProject from Ready11 template"
```

Delete `scripts/bootstrap.py` once you are happy with the result.

## 3. What to customize

| Area | Where |
|------|-------|
| Domain & env | `.env` (`PUBLIC_DOMAIN`, `ALLOWED_HOSTS`, SMTP, Sentry) — see `.env.example` |
| Branding / landing page | `templates/core/landing.html`, `templates/base.html` |
| Design tokens (colors, fonts, spacing) | `tailwind.config.js` + `input.css` (`@layer components`) |
| Translations | `locale/pt_BR/` — run `make messages` / `make compile` after editing strings |
| README | Rewrite `README.md` / `README.pt-br.md` badges, links and description |
| GitHub settings | Enable branch protection on `main` (the husky pre-push hook only guards locally) |

## 4. Where your business code goes

The template ships with the SaaS plumbing (users, tenants, RBAC, notifications, audit) and an **empty `TENANT_APPS`** section waiting for your domain models.

- **Per-tenant data** (the product itself — each workspace sees only its own rows): create the app under `apps/` and add it to `TENANT_APPS` in `<Project>/settings.py` (look for the `# Your business apps go here` comment). Tables are created inside every tenant schema.
- **Global/cross-tenant data** (billing plans, platform settings): add the app to `SHARED_APPS` instead. Tables live in the `public` schema.

Creating a new app:

```bash
mkdir -p apps/orders
python manage.py startapp orders apps/orders
```

Then edit `apps/orders/apps.py` so Django resolves the dotted path:

```python
class OrdersConfig(AppConfig):
    name = 'apps.orders'
```

Add `'apps.orders'` to `TENANT_APPS` (or `SHARED_APPS`), create migrations and apply them to every schema:

```bash
python manage.py makemigrations orders
make migrate    # runs migrate_schemas --shared and --tenant
```

Conventions to keep:

- Business logic lives in `apps/<app>/services.py`; views stay thin (see `apps/tenants/services.py`).
- User-facing strings are written in English and wrapped in `gettext` / `{% trans %}`; pt-BR comes from `make messages` + `make compile`.
- Views that touch tenant data use the `@tenant_permission_required('perm.string')` decorator from `apps/tenants/decorators.py`.
- Record relevant actions with `apps.audit.services.log_action()`.
