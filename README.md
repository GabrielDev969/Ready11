# Ready11

Projeto Django 6 com banco de dados PostgreSQL, pronto para rodar localmente (com PostgreSQL via Docker) ou totalmente dentro de containers Docker.

Este guia foi escrito para quem **acabou de clonar o repositório** e nunca rodou o projeto antes. Há instruções separadas para **Windows** e **macOS**.

---

## Sumário

- [Stack do projeto](#stack-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Opção A — Rodar localmente (recomendada para desenvolvimento)](#opção-a--rodar-localmente-recomendada-para-desenvolvimento)
  - [macOS](#macos)
  - [Windows](#windows)
- [Opção B — Rodar tudo em Docker](#opção-b--rodar-tudo-em-docker)
- [Comandos úteis do Django](#comandos-úteis-do-django)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Solução de problemas (FAQ)](#solução-de-problemas-faq)

---

## Stack do projeto

| Componente         | Versão / Tecnologia     |
|--------------------|-------------------------|
| Linguagem          | Python 3.12             |
| Framework          | Django 6.0              |
| Banco de dados     | PostgreSQL 17           |
| Servidor (prod)    | Gunicorn                |
| Arquivos estáticos | WhiteNoise              |
| Container          | Docker / Docker Compose |

Dependências Python completas em [`requirements.txt`](requirements.txt).

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

> ⚠️ **Importante:** este projeto **não** carrega o arquivo `.env` automaticamente (não usa `python-dotenv`). O `.env` serve como referência e é usado pela infraestrutura de deploy. No desenvolvimento local, você vai **definir as variáveis diretamente no terminal** (mostrado nos passos abaixo).

Crie seu próprio `.env` a partir do exemplo (opcional, para guardar seus valores):

**macOS / Linux:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Variáveis disponíveis:

| Variável        | Descrição                                                        | Exemplo                                                |
|-----------------|------------------------------------------------------------------|--------------------------------------------------------|
| `DATABASE_URL`  | URL de conexão com o PostgreSQL. Se vazia, usa o fallback local. | `postgres://postgres:postgres@127.0.0.1:5432/ready_db` |
| `DEBUG`         | Modo debug do Django (`True`/`False`).                           | `True`                                                 |
| `SECRET_KEY`    | Chave secreta do Django.                                         | `troque-esta-chave`                                    |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula.                         | `127.0.0.1,localhost`                                  |

> 💡 O `docker-compose.yml` cria o banco com nome **`ready_db`**, usuário **`postgres`** e senha **`postgres`**. Por isso, ao rodar localmente, use:
> `DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/ready_db`

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

# 4. Instale as dependências
pip install --upgrade pip
pip install -r requirements.txt

# 5. Defina as variáveis de ambiente (válidas para a sessão atual do terminal)
export DATABASE_URL="postgres://postgres:postgres@127.0.0.1:5432/ready_db"
export SECRET_KEY="chave-de-desenvolvimento-troque-aqui"
export DEBUG="True"
export ALLOWED_HOSTS="127.0.0.1,localhost"

# 6. Aplique as migrações do banco
python manage.py migrate

# 7. (Opcional) Crie um usuário administrador
python manage.py createsuperuser

# 8. Suba o servidor de desenvolvimento
python manage.py runserver
```

Acesse: **http://127.0.0.1:8000** • Admin: **http://127.0.0.1:8000/admin**

> Para reativar o ambiente virtual numa nova sessão: `source venv/bin/activate`
> Lembre-se de **redefinir os `export`** acima sempre que abrir um novo terminal (ou coloque-os num script).

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

# 4. Instale as dependências
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Defina as variáveis de ambiente (válidas para a sessão atual do terminal)
$env:DATABASE_URL  = "postgres://postgres:postgres@127.0.0.1:5432/ready_db"
$env:SECRET_KEY    = "chave-de-desenvolvimento-troque-aqui"
$env:DEBUG         = "True"
$env:ALLOWED_HOSTS = "127.0.0.1,localhost"

# 6. Aplique as migrações do banco
python manage.py migrate

# 7. (Opcional) Crie um usuário administrador
python manage.py createsuperuser

# 8. Suba o servidor de desenvolvimento
python manage.py runserver
```

Acesse: **http://127.0.0.1:8000** • Admin: **http://127.0.0.1:8000/admin**

> **Se o PowerShell bloquear a ativação do venv** com erro *"execution of scripts is disabled"*, rode uma vez:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Depois tente ativar novamente.

> **Usando o Prompt de Comando (CMD) em vez do PowerShell?** Os comandos mudam:
> - Ativar venv: `venv\Scripts\activate.bat`
> - Definir variável: `set DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/ready_db`

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
> O [`entrypoint.sh`](entrypoint.sh) roda automaticamente `migrate` e inicia o **Gunicorn** ao subir o container.

Acesse: **http://127.0.0.1:8000**

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

> Rode com o `venv` ativado e as variáveis de ambiente definidas.

| Comando                            | O que faz                                              |
|------------------------------------|--------------------------------------------------------|
| `python manage.py runserver`       | Sobe o servidor de desenvolvimento.                    |
| `python manage.py migrate`         | Aplica as migrações ao banco.                          |
| `python manage.py makemigrations`  | Cria novas migrações a partir de mudanças nos models.  |
| `python manage.py createsuperuser` | Cria um usuário administrador.                         |
| `python manage.py collectstatic`   | Coleta arquivos estáticos em `staticfiles/`.           |
| `python manage.py shell`           | Abre um shell Python com o contexto do Django.         |

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
├── Ready11/                 # Pacote de configuração do Django
│   ├── settings.py          # Configurações (lê variáveis de ambiente)
│   ├── urls.py              # Rotas (atualmente: /admin)
│   ├── wsgi.py              # Entrada WSGI (Gunicorn)
│   └── asgi.py              # Entrada ASGI
├── manage.py                # CLI administrativa do Django
├── requirements.txt         # Dependências Python
├── Dockerfile               # Imagem da aplicação (Python + Gunicorn)
├── docker-compose.yml       # Serviço do PostgreSQL
├── entrypoint.sh            # migrate + Gunicorn ao subir o container
├── .env.example             # Modelo de variáveis de ambiente
├── .dockerignore
└── .gitignore
```

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

**As variáveis de ambiente "somem" ao abrir um novo terminal**
É esperado: `export` (macOS) e `$env:` (Windows) valem apenas para a sessão atual. Redefina-as ao abrir um novo terminal, ou crie um script para carregá-las.
