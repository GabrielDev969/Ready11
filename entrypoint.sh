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

echo "--> Iniciando o servidor Daphne (ASGI: HTTP + WebSocket)..."
# Daphne serve HTTP e WebSocket (Channels) no mesmo processo. Em produção com
# múltiplas réplicas, defina REDIS_URL para o channel layer compartilhado.
# RUN_CLEANUP_SCHEDULER=1 liga o agendador de limpeza de notificações embutido.
export RUN_CLEANUP_SCHEDULER=1
exec daphne -b 0.0.0.0 -p 8000 Ready11.asgi:application
