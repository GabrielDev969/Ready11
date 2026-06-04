#!/bin/sh

# Falhar o script se qualquer comando falhar
set -e

echo "--> Rodando as migrações do banco de dados..."
python manage.py migrate --noinput

echo "--> Iniciando o servidor Gunicorn..."
# Executa o Gunicorn substituindo o processo do shell (essencial para o Docker gerenciar os sinais de parada)
exec gunicorn --bind 0.0.0.0:8000 --workers 3 Ready11.wsgi:application