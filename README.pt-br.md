# Ready11

📖 Also available in [English](README.md)

Projeto **base para sistemas SaaS B2B**: Django 6 + PostgreSQL com **multi-tenancy isolado por schema** (`django-tenants`), contas globais, controle de acesso por cargos (RBAC), onboarding por convite, proteção contra força bruta (`django-axes`) e **internacionalização** (inglês + português do Brasil, com auto-detecção). Roda localmente (PostgreSQL via Docker) ou totalmente em containers.

Este guia foi escrito para quem **acabou de clonar o repositório** e nunca rodou o projeto antes. Há instruções separadas para **Windows** e **macOS**.

> A página inicial (`/`) é uma landing de apresentação que também resume a instalação.

---

## Sumário

- [Stack do projeto](#stack-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Opção A — Rodar localmente (recomendada para desenvolvimento)](#opção-a--rodar-localmente-recomendada-para-desenvolvimento)
  - [macOS](#macos)
  - [Windows](#windows)
- [Opção B — Rodar tudo em Docker](#opção-b--rodar-tudo-em-docker)
- [Multi-tenancy: criando o primeiro workspace](#multi-tenancy-criando-o-primeiro-workspace)
- [Comandos úteis do Django](#comandos-úteis-do-django)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Solução de problemas (FAQ)](#solução-de-problemas-faq)

---

## Stack do projeto

| Componente         | Versão / Tecnologia        |
|--------------------|----------------------------|
| Linguagem          | Python 3.12                |
| Framework          | Django 6.0                 |
| Multi-tenancy      | django-tenants (por schema)|
| Banco de dados     | PostgreSQL 17              |
| Segurança          | django-axes (anti força bruta) |
| Front-end          | Django Templates + Tailwind CSS v3 |
| i18n               | en + pt-BR (auto-detecção) |
| Servidor (prod)    | Gunicorn                   |
| Arquivos estáticos | WhiteNoise (manifest)      |
| Container          | Docker / Docker Compose    |

Dependências Python completas em [`requirements.txt`](requirements.txt) e de front-end em [`package.json`](package.json).

---

## Pré-requisitos

Antes de começar, instale:

### Para todos
- **Git** — https://git-scm.com/downloads
- **Docker Desktop** (necessário para subir o banco PostgreSQL) — https://www.docker.com/products/docker-desktop/

### Para rodar localmente (Opção A)
- **Python 3.12** — https://www.python.org/downloads/
  - **Windows:** durante a instalação, marque a opção **"Add Python to PATH"**.
  - **macOS:** recomendado instalar via [Homebrew](https://brew.sh): `brew install python@3.12`
- **Node.js 18+** (para compilar o CSS com Tailwind) — https://nodejs.org/
- **GNU gettext** (para compilar as traduções i18n)
  - **macOS:** `brew install gettext`
  - **Windows:** já incluso no Git for Windows, ou instale o pacote gettext.

> Para verificar o que já está instalado:
> ```bash
> git --version
> docker --version
> python --version   # no Windows costuma ser: python
> python3 --version  # no macOS/Linux costuma ser: python3
> ```

---

## Variáveis de ambiente

O projeto lê a configuração a partir de **variáveis de ambiente**. Existe um arquivo de exemplo: [`.env.example`](.env.example).

> O projeto carrega o arquivo `.env` automaticamente (via `python-dotenv`), então para o desenvolvimento local basta copiar o exemplo — não é preciso exportar variáveis na mão.

Crie seu próprio `.env` a partir do exemplo:

**macOS / Linux:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Variáveis mais relevantes (veja `.env.example` para a lista completa):

| Variável        | Descrição                                                        | Exemplo                                                |
|-----------------|------------------------------------------------------------------|--------------------------------------------------------|
| `DATABASE_URL`  | URL de conexão com o PostgreSQL. Vazia em dev usa o fallback local; obrigatória em produção. | `postgres://postgres:postgres@127.0.0.1:5432/ready_db` |
| `DEBUG`         | Modo debug do Django. Padrão `False` (seguro para produção).     | `True`                                                 |
| `SECRET_KEY`    | Chave secreta do Django. Obrigatória quando `DEBUG=False`.       | `troque-esta-chave`                                    |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula.                         | `127.0.0.1,localhost,.localhost`                       |
| `PUBLIC_DOMAIN` | Domínio base usado para montar os subdomínios dos tenants.       | `localhost`                                            |

> ⚠️ Em produção (`DEBUG=False`), `SECRET_KEY` e `DATABASE_URL` são **obrigatórias** — a aplicação se recusa a subir sem elas.
>
> 💡 O `docker-compose.yml` cria o banco com nome **`ready_db`**, usuário/senha **`postgres`/`postgres`**. O `.env.example` padrão já bate com isso.

---

## Opção A — Rodar localmente (recomendada para desenvolvimento)

Nesta opção, o **PostgreSQL roda em Docker** e a **aplicação Django roda na sua máquina** (mais rápido para desenvolver, com recarregamento automático).

### macOS

```bash
# 1. Entre na pasta do projeto (após clonar)
cd Ready11

# 2. Suba o banco de dados PostgreSQL em segundo plano
docker compose up -d

# 3. Crie e ative um ambiente virtual Python
python3 -m venv venv
source venv/bin/activate

# 4. Instale as dependências Python
pip install --upgrade pip
pip install -r requirements.txt

# 5. Crie seu .env (carregado automaticamente pelo Django)
cp .env.example .env
# Para dev local, os valores padrão já funcionam (DEBUG=True usa o Postgres do docker-compose).

# 6. Compile o CSS do Tailwind
npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

# 7. Compile as traduções (en + pt-BR)
python manage.py compilemessages

# 8. Aplique as migrações do schema público e crie o tenant público
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant

# 9. (Opcional) Crie um superusuário para o /admin
python manage.py createsuperuser

# 10. Suba o servidor de desenvolvimento
python manage.py runserver
```

Acesse: **http://127.0.0.1:8000** (landing) • Admin: **http://127.0.0.1:8000/admin**

> Para reativar o ambiente virtual numa nova sessão: `source venv/bin/activate`
> O arquivo `.env` é carregado automaticamente — não é preciso exportar variáveis manualmente.

---

### Windows

Use o **PowerShell** (recomendado).

```powershell
# 1. Entre na pasta do projeto (após clonar)
cd Ready11

# 2. Suba o banco de dados PostgreSQL em segundo plano
docker compose up -d

# 3. Crie e ative um ambiente virtual Python
python -m venv venv
.\venv\Scripts\Activate.ps1

# 4. Instale as dependências Python
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Crie seu .env (carregado automaticamente pelo Django)
Copy-Item .env.example .env
# Para dev local, os valores padrão já funcionam (DEBUG=True usa o Postgres do docker-compose).

# 6. Compile o CSS do Tailwind
npm install
npx tailwindcss -i input.css -o static/css/output.css --minify

# 7. Compile as traduções (en + pt-BR)
python manage.py compilemessages

# 8. Aplique as migrações do schema público e crie o tenant público
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant

# 9. (Opcional) Crie um superusuário para o /admin
python manage.py createsuperuser

# 10. Suba o servidor de desenvolvimento
python manage.py runserver
```

Acesse: **http://127.0.0.1:8000** (landing) • Admin: **http://127.0.0.1:8000/admin**

> **Se o PowerShell bloquear a ativação do venv** com erro *"execution of scripts is disabled"*, rode uma vez:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Depois tente ativar novamente.

> **Usando o Prompt de Comando (CMD) em vez do PowerShell?** Ativar o venv: `venv\Scripts\activate.bat`

---

## Opção B — Rodar tudo em Docker

Nesta opção você sobe o banco com Docker Compose e roda a aplicação a partir da imagem Docker (usando Gunicorn, como em produção).

> O `docker-compose.yml` deste projeto sobe **apenas o banco de dados**. Para a aplicação, construímos a imagem a partir do [`Dockerfile`](Dockerfile) e a conectamos à mesma rede do banco.

```bash
# 1. Suba o banco de dados
docker compose up -d

# 2. Construa a imagem da aplicação
docker build -t ready11-app .

# 3. Rode o container da aplicação conectado à rede do compose
#    (descubra o nome da rede com: docker network ls | grep ready)
docker run --rm -p 8000:8000 \
  --network ready11_default \
  -e DATABASE_URL="postgres://postgres:postgres@django_postgres_db:5432/ready_db" \
  -e SECRET_KEY="chave-de-producao-troque-aqui" \
  -e DEBUG="False" \
  -e ALLOWED_HOSTS="127.0.0.1,localhost" \
  ready11-app
```

> **Por que `django_postgres_db` no host?** Dentro da rede do Docker, os containers se enxergam pelo nome. O container do banco se chama `django_postgres_db` (definido no `docker-compose.yml`).
>
> O [`entrypoint.sh`](entrypoint.sh) roda automaticamente as migrações (`migrate_schemas --shared`), garante o tenant público, coleta os estáticos e inicia o **Gunicorn**. O `Dockerfile` compila o CSS (Tailwind) e as traduções (`compilemessages`) durante o build.

Acesse: **http://127.0.0.1:8000**

---

## Multi-tenancy: criando o primeiro workspace

A entrada é **apenas por convite**. Para criar a primeira empresa (workspace):

1. Crie um superusuário e acesse o `/admin`.
2. Em **Workspace invites**, crie um convite **sem workspace** (convite "gênesis"). O link aparece no console do servidor.
3. Abra o link, preencha nome e **Nome da Empresa** — o backend cria um **schema isolado** no PostgreSQL e um subdomínio (`empresa.localhost`).
4. O dono acessa o workspace no subdomínio e convida a equipe em **/team/**.

> **Subdomínios em dev:** navegadores resolvem `*.localhost` para `127.0.0.1` automaticamente (ex.: `http://minhaempresa.localhost:8000/home/`). O `ALLOWED_HOSTS` já inclui `.localhost`.

> **Idioma:** o site detecta o idioma do navegador (inglês ou português) e tem um seletor no topo. A fonte das mensagens é em inglês; o pt-BR vem das traduções em `locale/`.

Para criar um superusuário com a aplicação em Docker:
```bash
docker run --rm -it \
  --network ready11_default \
  -e DATABASE_URL="postgres://postgres:postgres@django_postgres_db:5432/ready_db" \
  -e SECRET_KEY="qualquer-coisa" \
  ready11-app python manage.py createsuperuser
```

---

## Comandos úteis do Django

> Rode com o `venv` ativado (o `.env` é carregado automaticamente).

| Comando                                      | O que faz                                              |
|----------------------------------------------|--------------------------------------------------------|
| `python manage.py runserver`                 | Sobe o servidor de desenvolvimento.                    |
| `python manage.py migrate_schemas --shared`  | Aplica as migrações no schema público (compartilhado). |
| `python manage.py migrate_schemas --tenant`  | Aplica as migrações nos schemas de tenants.            |
| `python manage.py setup_public_tenant`       | Cria o tenant/domínio público (idempotente).           |
| `python manage.py makemigrations`            | Cria novas migrações a partir de mudanças nos models.  |
| `python manage.py createsuperuser`           | Cria um usuário administrador.                          |
| `python manage.py makemessages -l pt_BR`     | Extrai/atualiza as strings para tradução.              |
| `python manage.py compilemessages`           | Compila as traduções (`.po` → `.mo`).                  |
| `npx tailwindcss -i input.css -o static/css/output.css` | Recompila o CSS do Tailwind.                |
| `python manage.py shell`                     | Abre um shell Python com o contexto do Django.         |

Comandos úteis do Docker:

| Comando                     | O que faz                                          |
|-----------------------------|----------------------------------------------------|
| `docker compose up -d`      | Sobe o banco em segundo plano.                     |
| `docker compose down`       | Para os containers (mantém os dados).              |
| `docker compose down -v`    | Para os containers **e apaga os dados** do banco.  |
| `docker compose logs -f db` | Acompanha os logs do banco em tempo real.          |
| `docker ps`                 | Lista os containers em execução.                   |

---

## Estrutura do projeto

```
Ready11/
├── Ready11/                 # Pacote de configuração do Django (settings, urls, wsgi, asgi)
├── core/                    # Landing page pública + health check
├── users/                   # Usuário global customizado, auth, cadastro, login
├── tenants/                 # Multi-tenancy: workspaces, domínios, cargos, membros, convites
├── templates/               # Templates Django (Tailwind), organizados por app
├── locale/pt_BR/            # Traduções em português do Brasil
├── static/ , input.css , tailwind.config.js   # Front-end (Tailwind)
├── manage.py                # CLI administrativa do Django
├── requirements.txt         # Dependências Python
├── package.json             # Dependências de front-end
├── Dockerfile               # Imagem da aplicação (build do CSS em Node + Python/Gunicorn)
├── docker-compose.yml       # Serviço do PostgreSQL
├── entrypoint.sh            # migrações + Gunicorn ao subir o container
├── .env.example             # Modelo de variáveis de ambiente
├── .dockerignore
└── .gitignore
```

---

## Checklist de produção (SaaS multi-tenant)

A arquitetura é **um schema por tenant** (cada empresa tem seu próprio schema no
PostgreSQL), adequada para dezenas a milhares de empresas. Antes de colocar empresas
reais em produção, garanta o seguinte:

- [ ] **`DEBUG=False`** e um **`SECRET_KEY`** forte definido (a aplicação se recusa a
      subir sem isso). Rode `python manage.py check --deploy` — não deve apontar problemas.
- [ ] **`DATABASE_URL`** apontando para o PostgreSQL de produção.
- [ ] **`PUBLIC_DOMAIN`** com seu domínio real; DNS com registro **curinga**
      (`*.seudominio.com`) para cada subdomínio de tenant resolver. O
      `CSRF_TRUSTED_ORIGINS` é derivado dele (ou defina explicitamente).
- [ ] **`REDIS_URL` é obrigatório quando houver mais de uma réplica do servidor.**
      As notificações em tempo real usam Channels; com o layer in-memory, um toast só
      chega a quem está no *mesmo* processo. Com várias réplicas, defina `REDIS_URL`
      para compartilhar o channel layer do WebSocket. (Processo único / dev: in-memory
      basta.)
- [ ] **E-mail**: configure SMTP (`EMAIL_BACKEND` + `EMAIL_*`) para os e-mails de
      verificação e convite saírem de verdade (em dev usa o backend de console).
- [ ] **Migrações no deploy**: o `entrypoint.sh` roda `migrate_schemas --shared` e
      `--tenant`, então o schema de toda empresa é migrado. Isso escala linearmente com
      o número de tenants — muitos tenants = deploys mais longos.
- [ ] **Limpeza de notificações**: roda automaticamente pelo agendador embutido
      (`NOTIFICATION_CLEANUP_ENABLED`, ligado por padrão), coordenado entre réplicas por
      um lock no Redis. Para usar agendador externo, defina
      `NOTIFICATION_CLEANUP_ENABLED=False` e agende `manage.py cleanup_notifications` no cron.
- [ ] **HTTPS** terminado pelo seu proxy reverso (Easypanel/Nginx). A aplicação já
      define HSTS, cookies seguros e confia no `X-Forwarded-Proto`.

### Notas de escala (quando o volume crescer)
- **O provisionamento do tenant é síncrono** hoje: criar uma empresa roda a criação do
  schema + migrações de tenant dentro do request. Tranquilo em baixo volume de
  cadastros; mover para uma task em background quando necessário.
- **Um schema por tenant** funciona muito bem até a casa dos milhares. Muito além disso,
  migrações por deploy e `pg_dump` ficam pesados — revisite a estratégia de tenancy nessa
  hora.
- Para carga alta de HTTP, dá para separar o HTTP (workers WSGI/uvicorn) do processo de
  WebSocket; a base entrega um único `daphne` servindo os dois.

---

## Solução de problemas (FAQ)

**`django.db.utils.OperationalError: could not connect to server`**
O banco não está no ar ou a `DATABASE_URL` está incorreta. Verifique se o `docker compose up -d` rodou e se o container `django_postgres_db` está ativo (`docker ps`).

**`port 5432 is already allocated` / porta em uso**
Já existe um PostgreSQL na porta 5432 (outro container ou instalação local). Pare o serviço conflitante ou altere o mapeamento de porta no `docker-compose.yml` (ex.: `"5433:5432"`) e ajuste a `DATABASE_URL`.

**`docker: command not found` ou erro de conexão com o Docker**
Abra o **Docker Desktop** e aguarde ele iniciar completamente antes de rodar os comandos.

**`'python' não é reconhecido` (Windows)**
Reinstale o Python marcando **"Add Python to PATH"**, ou use o launcher `py` (ex.: `py -m venv venv`).

**O comando `docker compose` não funciona, mas `docker-compose` sim**
Versões antigas usam o hífen. Substitua `docker compose` por `docker-compose` nos comandos.

**`ImproperlyConfigured: SECRET_KEY ... required when DEBUG=False`**
Você está rodando em modo produção sem as variáveis obrigatórias. Defina `SECRET_KEY` e `DATABASE_URL`, ou use `DEBUG=True` para desenvolvimento local.
