# Ready11

📖 Also available in [English](README.md)

Projeto **base para sistemas SaaS B2B**: Django 6 + PostgreSQL com **multi-tenancy isolado por schema** (`django-tenants`), contas globais, controle de acesso por cargos (RBAC), onboarding por convite, notificações em tempo real (WebSocket), log de auditoria, proteção contra força bruta e **internacionalização** (inglês + português). CI/CD com GitHub Actions incluído.

> Este guia foi escrito para quem **acabou de clonar o repositório** e nunca rodou o projeto antes.

> 🚀 **Iniciando um novo projeto a partir deste template?** Veja [docs/TEMPLATE_USAGE.md](docs/TEMPLATE_USAGE.md) — crie o repositório pelo GitHub Template, rode `python scripts/bootstrap.py MeuProjeto` e siga os passos impressos.

---

## Sumário

- [Usar como template](docs/TEMPLATE_USAGE.md)
- [Stack](#stack)
- [Pré-requisitos](#pré-requisitos)
- [Setup rápido (Makefile)](#setup-rápido-makefile)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Opção A — Rodar localmente](#opção-a--rodar-localmente-recomendada-para-desenvolvimento)
- [Opção B — Rodar tudo em Docker](#opção-b--rodar-tudo-em-docker)
- [Primeiro workspace (multi-tenancy)](#primeiro-workspace-multi-tenancy)
- [Fluxo de desenvolvimento do dia-a-dia](#fluxo-de-desenvolvimento-do-dia-a-dia)
- [Quando você faz uma alteração](#quando-você-faz-uma-alteração)
- [Referência de comandos](#referência-de-comandos)
- [Estrutura do projeto](#estrutura-do-projeto)
- [CI/CD](#cicd)
- [Checklist de produção](#checklist-de-produção)
- [Solução de problemas](#solução-de-problemas)

---

## Stack

| Componente          | Tecnologia                                        |
|---------------------|---------------------------------------------------|
| Linguagem           | Python 3.12                                       |
| Framework           | Django 6.0                                        |
| Multi-tenancy       | django-tenants (schema por tenant)                |
| Banco de dados      | PostgreSQL 17                                     |
| Tempo real          | Django Channels + Redis (WebSocket)               |
| Segurança           | django-axes (força bruta) + HSTS + CSRF           |
| Monitoramento       | Sentry (opcional, via `SENTRY_DSN`)               |
| Métricas            | Prometheus + Grafana ([docs](docs/OBSERVABILITY.md)) |
| Front-end           | Django Templates + Tailwind CSS v3                |
| i18n                | Inglês (fonte) + pt-BR (auto-detecção)            |
| Servidor (prod)     | Daphne (ASGI) / Gunicorn                          |
| Arquivos estáticos  | WhiteNoise (comprimido + manifest em prod)        |
| Cache               | Redis (`django.core.cache.backends.redis`)        |
| Log de auditoria    | App `audit` customizado (schema público)          |
| Design system       | GSS Design System (classes de componentes Tailwind)|
| Lint                | Ruff                                              |
| Convenção de commit | Conventional Commits (commitlint)                 |
| CI/CD               | GitHub Actions (lint, testes, segurança, coverage)|
| Container           | Docker / Docker Compose                           |

---

## Pré-requisitos

### Para todos
- **Git** — https://git-scm.com/downloads
- **Docker Desktop** (roda PostgreSQL + Redis) — https://www.docker.com/products/docker-desktop/

### Para rodar localmente (Opção A)
- **Python 3.12** — https://www.python.org/downloads/
  - Windows: marque **"Add Python to PATH"** na instalação
  - macOS: `brew install python@3.12`
- **Node.js 18+** (Tailwind CSS) — https://nodejs.org/
- **GNU gettext** (compilar traduções i18n)
  - macOS: `brew install gettext`
  - Windows: já incluso no Git for Windows

---

## Conceitos-chave

Três ideias que vão poupar tempo de quem está chegando agora:

**Workspaces (tenants)** — toda empresa que se cadastra recebe seu próprio **schema isolado no PostgreSQL**. Os dados da empresa A e da empresa B nunca se misturam no banco. O `django-tenants` roteia cada request para o schema correto com base no subdomínio (`acme.seudominio.com` → schema `acme`). O schema `public` guarda os dados compartilhados: usuários, logs de auditoria, notificações.

**Cargos e permissões (RBAC)** — cada workspace gerencia seus próprios cargos. Um cargo carrega uma lista de strings de permissão (ex.: `roles.edit`, `users.invite`). Cada membro do workspace tem exatamente um cargo. O cargo `Owner` é um cargo de sistema — não pode ser editado nem deletado. Todos os outros cargos são totalmente customizáveis.

**Cadastro apenas por convite** — novos workspaces e novos membros entram por links de convite. Não existe página de auto-cadastro. Um superusuário cria um **convite gênesis** (pelo Django admin, sem workspace selecionado) para provisionar uma nova empresa. Depois de entrar, o dono do workspace convida o time em `/team/`.

---

## Setup rápido (Makefile)

A forma mais rápida de rodar depois de clonar:

```bash
# 1. Suba o banco + Redis
make docker-up

# 2. Crie o venv e instale as dependências
python3 -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
make setup                      # pip install + npm install + build CSS

# 3. Copie o arquivo de ambiente
cp .env.example .env            # Windows: Copy-Item .env.example .env
# Abra o .env e confirme que DEBUG=True (os demais padrões já funcionam)

# 4. Aplique as migrações e crie o tenant público
make migrate

# 5. Crie um superusuário dev (admin@example.com / Admin1234!)
make seed

# 6. Suba o servidor
make run
```

Acesse: **http://127.0.0.1:8000**

> **Os hooks Git são instalados automaticamente** quando o `npm install` roda. Nenhum passo extra necessário.
> Para habilitar também as verificações de arquivo mais profundas (ruff, whitespace, etc.):
> ```bash
> make hooks    # instala os pre-commit hooks
> ```

---

## Variáveis de ambiente

O projeto lê toda a configuração de variáveis de ambiente e carrega o `.env` automaticamente via `python-dotenv`.

```bash
cp .env.example .env
```

Variáveis mais importantes:

| Variável          | Descrição                                                        | Padrão / Exemplo                               |
|-------------------|------------------------------------------------------------------|------------------------------------------------|
| `DEBUG`           | Modo debug do Django. Nunca `True` em produção.                  | `True` (dev)                                   |
| `SECRET_KEY`      | Obrigatório quando `DEBUG=False`.                                | *(obrigatório em prod)*                        |
| `DATABASE_URL`    | URL do PostgreSQL. Vazia em dev usa o banco do docker-compose.   | `postgres://postgres:postgres@127.0.0.1:5432/ready_db` |
| `REDIS_URL`       | Redis para Channels + cache. Opcional em dev com processo único. | `redis://localhost:6379/0`                     |
| `PUBLIC_DOMAIN`   | Domínio base para subdomínios dos tenants.                       | `localhost`                                    |
| `SENTRY_DSN`      | DSN do projeto no Sentry. Vazio desativa.                        | *(opcional)*                                   |
| `LOG_FORMAT`      | `text` (dev) ou `json` (prod/CloudWatch/Loki).                   | `text`                                         |
| `AUDIT_CLEANUP_ENABLED` | Roda o scheduler embutido de limpeza do audit log. Defina `False` se agendar `cleanup_audit_logs` externamente. | `True` |
| `NOTIFICATION_CLEANUP_ENABLED` | Roda o scheduler embutido de limpeza de notificações. | `True`                        |

> Em produção (`DEBUG=False`), `SECRET_KEY` e `DATABASE_URL` são **obrigatórias** — a aplicação se recusa a subir sem elas.

---

## Opção A — Rodar localmente (recomendada para desenvolvimento)

PostgreSQL + Redis rodam no Docker; o Django roda na sua máquina (rápido, com auto-reload).

### macOS / Linux

```bash
cd Ready11
make docker-up

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Abra o .env e defina DEBUG=True — os outros padrões já funcionam.

npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

python manage.py compilemessages
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant
python manage.py seed           # cria admin@example.com / Admin1234!

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
# Abra o .env e defina DEBUG=True

npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

python manage.py compilemessages
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant
python manage.py seed

python manage.py runserver
```

> Se o PowerShell bloquear a ativação do venv: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

## Opção B — Rodar tudo em Docker

```bash
make docker-up
docker build -t ready11-app .
docker run --rm -p 8000:8000 \
  --network ready11_default \
  -e DATABASE_URL="postgres://postgres:postgres@django_postgres_db:5432/ready_db" \
  -e SECRET_KEY="chave-de-producao-troque-aqui" \
  -e DEBUG="False" \
  -e ALLOWED_HOSTS="127.0.0.1,localhost" \
  ready11-app
```

O `entrypoint.sh` roda as migrações, coleta os arquivos estáticos e inicia o Gunicorn automaticamente.

---

## Primeiro workspace (multi-tenancy)

A entrada é **apenas por convite**. Para criar o primeiro workspace:

1. Logue no `/admin` com o superusuário criado pelo `make seed`.
2. Em **Workspace invites**, crie um convite **sem workspace** (convite "gênesis"). O link aparece no console do servidor.
3. Abra o link, preencha o nome e o **nome da empresa** — o backend cria um **schema isolado no PostgreSQL** e um subdomínio (`empresa.localhost`).
4. O dono acessa o workspace no subdomínio e convida o time em **/team/**.

> **Subdomínios em dev:** navegadores resolvem `*.localhost` para `127.0.0.1` automaticamente, ex.: `http://acme.localhost:8000/home/`. O `ALLOWED_HOSTS` já inclui `.localhost`.

---

## Fluxo de desenvolvimento do dia-a-dia

### Git hooks

Os hooks são gerenciados pelo **husky** e instalados automaticamente quando o `npm install` roda. Nenhum passo manual necessário.

| Hook | Quando roda | O que faz |
|---|---|---|
| `pre-commit` | todo `git commit` | Roda os checks do `pre-commit` (ruff, whitespace, etc.) se instalado; cai no `ruff check .` diretamente se não |
| `commit-msg` | todo `git commit` | Valida o formato da mensagem com commitlint |

Para habilitar também o suite completo de pre-commit (ruff + whitespace + YAML):
```bash
make hooks    # roda: pre-commit install
```

Para rodar todos os checks de arquivo manualmente sem commitar:
```bash
pre-commit run --all-files
```

### Rodando testes

```bash
make test           # roda o suite de testes completo
make coverage       # roda os testes + exibe o relatório de cobertura
```

Os testes usam `TestCase` do Django e conectam a um banco PostgreSQL de teste real (criado e destruído automaticamente). Garanta que `make docker-up` está rodando.

### Visualizando emails no dev

Suba o Mailpit (incluído no `docker-compose.yml`):
```bash
make docker-up
```

No seu `.env`:
```
EMAIL_HOST=localhost
EMAIL_PORT=1025
```

Acesse **http://localhost:8025** para ver todos os emails enviados pela aplicação (convites, redefinição de senha, etc.).

### Lint

```bash
make lint           # ruff check .
```

O Ruff também é executado no CI. Configure as regras em `ruff.toml`.

### Convenção de commit

Os commits devem seguir o padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/):

```
<tipo>(<escopo>): <descrição>

feat: adicionar exportação de workspace
fix: corrigir data de expiração do convite
docs: atualizar passos de setup no README
refactor: extrair verificação de permissão para decorator
test: adicionar cobertura para o serviço de audit log
chore: atualizar Django para 6.1
```

Tipos permitidos: `feat` `fix` `docs` `style` `refactor` `test` `chore` `perf` `ci` `build` `revert`

Os hooks de pre-commit avisam se o formato estiver errado. O CI também valida os commits nos pull requests.

---

## Quando você faz uma alteração

### Adicionou ou alterou um model

```bash
python manage.py makemigrations
make migrate        # aplica no schema público + todos os schemas de tenant
```

> Models em `SHARED_APPS` (como `audit`, `users`, `notifications`) ficam no schema público.
> Models em `TENANT_APPS` ficam no schema de cada empresa.

### Alterou um template ou componente de UI

O projeto usa o **GSS Design System** — um conjunto de classes de componentes baseadas em Tailwind (`gss-btn`, `gss-card`, `gss-pill`, `gss-input`, etc.) definidas em `input.css` sob `@layer components`. Cores e tokens de fonte ficam em `tailwind.config.js`. A documentação de referência está em `design-system/`.

Após editar templates ou `input.css`, reconstrua o CSS:
```bash
make css          # modo watch — reconstrói a cada salvamento
# ou uma vez:
npx tailwindcss -i input.css -o static/css/output.css --minify
```

> **Regra para pills:** sempre use a classe base junto com a variante de cor: `gss-pill gss-pill-neutral`. A classe de cor sozinha (`gss-pill-neutral`) não produz o formato de pill.

### Adicionou uma nova string traduzível

```bash
make messages       # extrai novas strings → locale/pt_BR/LC_MESSAGES/django.po
```

Abra `locale/pt_BR/LC_MESSAGES/django.po`, encontre as entradas novas (com `msgstr` vazio) e adicione as traduções em pt-BR. Depois:

```bash
make compile        # compila .po → .mo (necessário para as strings aparecerem)
```

> **Regra:** strings-fonte sempre em inglês. O português vai só no arquivo `.po`.

### Adicionou uma nova dependência Python

```bash
pip install <pacote>
pip freeze | grep <pacote>    # copie a versão exata pinada
# Adicione manualmente ao requirements.txt (mantenha a ordem alfabética)
```

Para ferramentas de dev/teste:
```bash
# Adicione ao requirements-dev.txt em vez do requirements.txt
```

### Criou um novo app Django

Todos os apps ficam dentro de `apps/`. Crie o app lá e atualize o `AppConfig.name`:

```bash
cd apps
python ../manage.py startapp meuapp
```

Depois edite `apps/meuapp/apps.py`:
```python
class MeuappConfig(AppConfig):
    name = 'apps.meuapp'   # ← obrigatório incluir o prefixo "apps."
```

E em `Ready11/settings.py`, adicione em `SHARED_APPS` (dados compartilhados entre todos os tenants) ou `TENANT_APPS` (isolado por workspace):
```python
SHARED_APPS = (
    ...
    'apps.meuapp',
)
```

Por fim:
1. Rode `python manage.py makemigrations meuapp` (o Django usa o `app_label` — a última parte — como alvo da migration)
2. Adicione um include de URL em `Ready11/urls.py` ou no urlconf de tenant
3. Escreva testes em `apps/meuapp/tests.py`

### Após fazer pull das alterações do time

```bash
git pull
pip install -r requirements.txt     # instala novas dependências
make migrate                         # aplica novas migrações
make compile                         # recompila traduções se o .po mudou
make css                             # reconstrói o CSS se os templates mudaram
```

---

## Referência de comandos

### Atalhos do Makefile

| Comando            | O que faz                                                 |
|--------------------|-----------------------------------------------------------|
| `make setup`       | Instala dependências Python + Node e gera o CSS           |
| `make run`         | Sobe o servidor de desenvolvimento                        |
| `make migrate`     | Aplica todas as migrações (público + tenant)              |
| `make seed`        | Cria superusuário dev (`admin@example.com`)               |
| `make test`        | Roda o suite de testes                                    |
| `make coverage`    | Roda testes e exibe relatório de cobertura                |
| `make lint`        | Executa o Ruff                                            |
| `make messages`    | Extrai strings traduzíveis (pt-BR)                        |
| `make compile`     | Compila arquivos `.po` → `.mo`                            |
| `make css`         | Observa e reconstrói o Tailwind CSS                       |
| `make check`       | Verificação de segurança do Django para deploy            |
| `make docker-up`   | Sobe PostgreSQL, Redis, Mailpit, Prometheus e Grafana     |
| `make docker-down` | Para os serviços Docker                                   |
| `make clean`       | Remove `.pyc`, `__pycache__`, `staticfiles/`              |

### Comandos Django

| Comando                                          | O que faz                                         |
|--------------------------------------------------|---------------------------------------------------|
| `python manage.py runserver`                     | Servidor de desenvolvimento                       |
| `python manage.py migrate_schemas --shared`      | Migra o schema público                            |
| `python manage.py migrate_schemas --tenant`      | Migra todos os schemas de tenant                  |
| `python manage.py setup_public_tenant`           | Cria/atualiza o tenant público (idempotente)      |
| `python manage.py seed`                          | Cria superusuário dev                             |
| `python manage.py makemigrations`                | Gera arquivos de migração a partir dos models     |
| `python manage.py makemessages -l pt_BR`         | Extrai strings para tradução                      |
| `python manage.py compilemessages`               | Compila `.po` → `.mo`                             |
| `python manage.py cleanup_audit_logs`            | Apaga logs de auditoria com mais de 90 dias       |
| `python manage.py cleanup_notifications`         | Apaga notificações antigas                        |
| `python manage.py check --deploy`                | Verifica configuração de produção                 |
| `python manage.py shell`                         | Shell Python com contexto do Django               |

---

## Estrutura do projeto

```
Ready11/
├── Ready11/                  # Pacote de configuração (settings, urls, asgi)
├── apps/                     # Todos os apps Django ficam aqui
│   ├── core/                 # Landing pública, health check, páginas de erro, robots.txt
│   │   └── middleware.py     # RequestLogging, PublicOnly, WorkspaceTZ, UserLanguage
│   ├── users/                # Model de usuário global, auth, cadastro, redefinição de senha, 2FA
│   ├── tenants/              # Workspaces, domínios, RBAC, membros, convites
│   ├── notifications/        # Notificações in-app (WebSocket + Redis)
│   └── audit/                # Log de auditoria do workspace (schema público)
├── templates/                # Templates Django organizados por app
│   ├── users/                # login, cadastro, redefinição de senha, templates de email
│   ├── tenants/              # workspace, team, cargos, convite
│   ├── audit/                # listagem do log de auditoria
│   ├── notifications/        # partials de notificação
│   ├── partials/             # sidebar, header, nav
│   ├── 404.html, 403.html    # páginas de erro customizadas
│   └── 500.html              # página de erro standalone (sem acesso ao banco)
├── locale/pt_BR/             # Traduções em português do Brasil
├── static/                   # Arquivos estáticos fonte
├── design-system/            # Referência do GSS Design System (tokens, docs dos componentes)
├── input.css                 # Entry point do Tailwind CSS (classes de componentes em @layer components)
├── tailwind.config.js        # Configuração do Tailwind (tokens de cor GSS, fontes, sombras)
├── manage.py
├── requirements.txt          # Dependências Python de produção
├── requirements-dev.txt      # Dependências de dev/testes (ruff, coverage, bandit…)
├── Dockerfile
├── docker-compose.yml        # PostgreSQL + Redis + Mailpit
├── entrypoint.sh             # Entrypoint do container (migrações → Gunicorn)
├── Makefile                  # Atalhos de desenvolvimento
├── ruff.toml                 # Configuração do Ruff
├── commitlint.config.js      # Regras do Conventional Commits
├── .pre-commit-config.yaml   # Hooks de pre-commit (ruff, whitespace, yaml…)
├── .github/workflows/ci.yml  # CI: lint, commitlint, teste+coverage, pip-audit, segurança
├── .env.example
├── .dockerignore
└── .gitignore
```

---

## CI/CD

Cada push para `main` e cada pull request executa estes jobs do GitHub Actions:

| Job                | Quando        | O que verifica                                              |
|--------------------|---------------|-------------------------------------------------------------|
| `lint`             | push + PR     | Ruff (estilo) + Bandit (SAST — varredura de segurança)      |
| `commitlint`       | PR apenas     | Todos os commits seguem o formato Conventional Commits      |
| `test`             | push + PR     | Suite de testes + cobertura ≥ 60% + upload do `coverage.xml` |
| `dependency-audit` | push + PR     | `pip-audit` — nenhum CVE conhecido no `requirements.txt`    |
| `security-check`   | push + PR     | `manage.py check --deploy` com `DEBUG=False`                |

O job de testes sobe um container real de PostgreSQL 17. O relatório de cobertura é salvo como artefato em cada execução.

---

## Checklist de produção

Antes de receber usuários reais:

- [ ] `DEBUG=False` + `SECRET_KEY` forte definida. Rode `make check` — sem avisos.
- [ ] `DATABASE_URL` apontando para o PostgreSQL de produção.
- [ ] `PUBLIC_DOMAIN` com o domínio real + registro DNS **curinga** (`*.seudominio.com`) para cada subdomínio de tenant resolver.
- [ ] `REDIS_URL` configurado — obrigatório para as notificações em tempo real funcionarem com múltiplas réplicas.
- [ ] SMTP configurado (`EMAIL_*`) — caso contrário convites e redefinição de senha não chegam.
- [ ] `SENTRY_DSN` configurado para monitoramento de erros.
- [ ] `LOG_FORMAT=json` para logs estruturados (CloudWatch, Grafana Loki, Datadog).
- [ ] HTTPS terminado pelo seu proxy reverso (Nginx/Traefik/Easypanel). A aplicação já força HSTS e cookies seguros quando `DEBUG=False`.
- [ ] Os jobs de limpeza rodam automaticamente pelos schedulers embutidos (`AUDIT_CLEANUP_ENABLED=True` e `NOTIFICATION_CLEANUP_ENABLED=True`). Para usar um cron externo, defina ambos como `False` e agende `manage.py cleanup_audit_logs` e `manage.py cleanup_notifications`.
- [ ] Migrações no deploy: o `entrypoint.sh` roda `migrate_schemas --shared` + `--tenant` — o schema de cada empresa é migrado. Isso escala linearmente com a quantidade de tenants.

### Notas de escala
- **Provisionamento de tenant é síncrono hoje** — a criação do schema roda dentro do request HTTP. Funciona bem em baixo volume; mova para task em background quando o volume crescer.
- **Um schema por tenant** funciona muito bem até a casa dos milhares. Muito além disso, migrações por deploy e `pg_dump` ficam pesados.
- Para carga HTTP alta você pode separar os workers HTTP do processo de WebSocket; a base entrega um único `daphne` servindo os dois.

---

## Solução de problemas

**`could not connect to server` (PostgreSQL)**
Rode `make docker-up` e confirme que o container `django_postgres_db` está rodando (`docker ps`).

**`port 5432 is already allocated`**
Pare o PostgreSQL conflitante ou mude o mapeamento de porta no `docker-compose.yml` (ex.: `"5433:5432"`) e atualize a `DATABASE_URL`.

**`Missing staticfiles manifest entry for 'css/output.css'`**
Gere o CSS primeiro: `npx tailwindcss -i input.css -o static/css/output.css --minify`. Isso só ocorre com `DEBUG=False` — em dev e nos testes do CI o storage simples é usado automaticamente.

**`docker: command not found`**
Abra o **Docker Desktop** e aguarde iniciar completamente antes de rodar qualquer comando `docker`.

**`'python' não é reconhecido` (Windows)**
Reinstale o Python com **"Add Python to PATH"** marcado, ou use o launcher `py` (`py -m venv venv`).

**`ImproperlyConfigured: SECRET_KEY required when DEBUG=False`**
Defina `SECRET_KEY` e `DATABASE_URL` no `.env`, ou use `DEBUG=True` para desenvolvimento local.

**Emails não aparecem no Mailpit**
Verifique que `EMAIL_HOST=localhost` e `EMAIL_PORT=1025` estão no `.env` e que o container do Mailpit está rodando (`docker ps | grep mailpit`). Acesse **http://localhost:8025**.

**Subdomínio do workspace não funciona (ex: `acme.localhost:8000`)**
Verifique que `ALLOWED_HOSTS` inclui `.localhost`. No Chrome/Firefox, subdomínios de `localhost` funcionam nativamente — sem necessidade de editar o `/etc/hosts`.
