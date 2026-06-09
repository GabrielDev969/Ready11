.PHONY: help setup run migrate css test messages compile check docker-up docker-down clean

PYTHON := python
MANAGE := $(PYTHON) manage.py

help:
	@echo "Ready11 development commands:"
	@echo "  make setup        Install dependencies and build CSS"
	@echo "  make run          Start the development server"
	@echo "  make migrate      Apply all schema migrations (shared + tenant)"
	@echo "  make css          Watch and rebuild Tailwind CSS"
	@echo "  make test         Run the test suite"
	@echo "  make messages     Extract translatable strings"
	@echo "  make compile      Compile .po translation files"
	@echo "  make check        Run Django deployment checks"
	@echo "  make docker-up    Start PostgreSQL + Redis services"
	@echo "  make docker-down  Stop Docker services"
	@echo "  make clean        Remove compiled/generated files"

setup:
	pip install -r requirements.txt
	npm install
	npm run build

run:
	$(MANAGE) runserver

migrate:
	$(MANAGE) migrate_schemas --shared --noinput
	$(MANAGE) setup_public_tenant
	$(MANAGE) migrate_schemas --tenant --noinput

css:
	npx tailwindcss -i ./input.css -o ./static/css/output.css --watch

test:
	$(MANAGE) test

messages:
	$(MANAGE) makemessages -l pt_BR --ignore=venv --ignore=node_modules

compile:
	$(MANAGE) compilemessages

check:
	$(MANAGE) check --deploy

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf staticfiles/
