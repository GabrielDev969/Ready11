# Imagem base oficial do Python estável e leve
FROM python:3.12-slim

# Impede que o Python grave arquivos .pyc no disco e força o output direto para o terminal (logs em tempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências mínimas do sistema operacional (como curl para healthchecks se necessário)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia primeiro o arquivo de dependências para aproveitar o cache de camadas do Docker
COPY requirements.txt /app/

# Atualiza o pip e instala as dependências do projeto
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia todo o restante do código do projeto para o container
COPY . /app/

# O Django exige uma SECRET_KEY e configurações válidas para rodar o collectstatic.
# Injetamos valores fictícios aqui apenas para compilar os estáticos durante o build da imagem,
# evitando que arquivos estáticos dependam de um banco de dados ativo neste momento.
RUN DATABASE_URL=postgres://dummy:dummy@localhost:5432/dummy \
    SECRET_KEY=build-time-dummy-key \
    DEBUG=False \
    python manage.py collectstatic --noinput

# Dá permissão de execução para o script de inicialização
RUN chmod +x /app/entrypoint.sh

# Expõe a porta padrão que configuramos no Gunicorn
EXPOSE 8000

# Define o script que gerenciará a inicialização do container
ENTRYPOINT ["/app/entrypoint.sh"]