#!/bin/sh

# Falhar o script se qualquer comando falhar
set -e

echo "--> Rodando as migrações do schema publico (compartilhado)..."
python manage.py migrate_schemas --shared

echo "--> Garantindo que o tenant publico exista no banco..."
python manage.py setup_public_tenant

echo "--> Iniciando o servidor Gunicorn..."
# Executa o Gunicorn substituindo o processo do shell (essencial para o Docker gerenciar os sinais de parada)
exec gunicorn --bind 0.0.0.0:8000 --workers 3 Ready11.wsgi:application