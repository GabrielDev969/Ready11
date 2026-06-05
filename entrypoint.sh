#!/bin/sh

# Falhar o script se qualquer comando falhar
set -e

echo "--> Aplicando migrações do schema público (compartilhado)..."
python manage.py migrate_schemas --shared --noinput

echo "--> Garantindo que o tenant público exista no banco..."
python manage.py setup_public_tenant

echo "--> Aplicando migrações dos schemas de tenants (clientes)..."
python manage.py migrate_schemas --tenant --noinput

echo "--> Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "--> Iniciando o servidor Gunicorn..."
# Executa o Gunicorn substituindo o processo do shell (essencial para o Docker gerenciar os sinais de parada)
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile - \
    Ready11.wsgi:application
