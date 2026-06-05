# ==========================================
# Estágio 1: Build do CSS (Tailwind via Node)
# ==========================================
FROM node:20-slim AS css-builder

WORKDIR /app

# Instala as dependências de build do front-end (Tailwind, PostCSS, autoprefixer)
COPY package.json package-lock.json* ./
RUN npm install

# O Tailwind precisa varrer os templates para saber quais classes manter
COPY tailwind.config.js input.css ./
COPY templates ./templates

# Gera o CSS final minificado em static/css/output.css
RUN npx tailwindcss -i ./input.css -o ./static/css/output.css --minify


# ==========================================
# Estágio 2: Aplicação Python/Django
# ==========================================
FROM python:3.12-slim

# Impede que o Python grave arquivos .pyc no disco e força o output direto para o terminal (logs em tempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Instala dependências mínimas do SO: curl (HEALTHCHECK) e gettext (compilemessages/i18n)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copia primeiro o arquivo de dependências para aproveitar o cache de camadas do Docker
COPY requirements.txt /app/

# Atualiza o pip e instala as dependências do projeto
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia todo o restante do código do projeto para o container
COPY . /app/

# Traz o CSS compilado do estágio de build do Node
COPY --from=css-builder /app/static/css/output.css /app/static/css/output.css

# O Django exige uma SECRET_KEY válida para rodar o collectstatic. Injetamos valores
# fictícios apenas para compilar os estáticos durante o build (DEBUG=True evita exigir DATABASE_URL).
RUN SECRET_KEY=build-time-dummy-key \
    DEBUG=True \
    python manage.py collectstatic --noinput

# Compila as traduções (.po -> .mo) durante o build
RUN SECRET_KEY=build-time-dummy-key DEBUG=True \
    python manage.py compilemessages

# Dá permissão de execução para o script de inicialização
RUN chmod +x /app/entrypoint.sh

# Expõe a porta padrão que configuramos no Gunicorn
EXPOSE 8000

# Verificação de saúde do container (usa o endpoint /healthz/)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz/ || exit 1

# Define o script que gerenciará a inicialização do container
ENTRYPOINT ["/app/entrypoint.sh"]
