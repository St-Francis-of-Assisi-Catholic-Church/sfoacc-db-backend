# ─────────────────────────────────────────────────────────────
#  SFOACC Backend Makefile
# ─────────────────────────────────────────────────────────────

COMPOSE = docker compose

# ── Colours ──────────────────────────────────────────────────
RESET  := \033[0m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
CYAN   := \033[0;36m
RED    := \033[0;31m

.PHONY: help \
        dev dev-stop \
        build build-clean up down restart logs \
        setup ssl \
        migrate migrate-auto migrate-history migrate-rollback \
        init-db seed seed-rbac seed-parish superuser check-db \
        dump-db load-dump \
        sdk \
        shell bash \
        lint clean

# ── Default target ───────────────────────────────────────────
help:
	@echo ""
	@echo "$(CYAN)SFOACC Backend$(RESET)"
	@echo ""
	@echo "$(GREEN)Local development (no Docker):$(RESET)"
	@echo "  $(YELLOW)make dev$(RESET)                 Run uvicorn locally with hot-reload"
	@echo ""
	@echo "$(GREEN)Docker:$(RESET)"
	@echo "  $(YELLOW)make build$(RESET)               Build images with layer cache"
	@echo "  $(YELLOW)make build-clean$(RESET)         Build images from scratch (no cache)"
	@echo "  $(YELLOW)make up$(RESET)                  Start services (api, db, nginx, adminer)"
	@echo "  $(YELLOW)make down$(RESET)                Stop and remove containers"
	@echo "  $(YELLOW)make restart$(RESET)             down + up"
	@echo "  $(YELLOW)make logs$(RESET)                Tail logs (all services)"
	@echo "  $(YELLOW)make logs s=api$(RESET)          Tail logs for a specific service"
	@echo "  (API: http://localhost:8000  Docs: http://localhost:8000/api/v1/docs)"
	@echo ""
	@echo "$(GREEN)Setup:$(RESET)"
	@echo "  $(YELLOW)make setup$(RESET)               Full first-time setup (ssl → build → up → init-db → seed → superuser)"
	@echo "  $(YELLOW)make ssl$(RESET)                 Generate/refresh self-signed SSL certificates"
	@echo ""
	@echo "$(GREEN)Database:$(RESET)"
	@echo "  $(YELLOW)make migrate$(RESET)             Apply all pending Alembic migrations"
	@echo "  $(YELLOW)make migrate-auto m=\"msg\"$(RESET) Auto-generate a new migration"
	@echo "  $(YELLOW)make migrate-history$(RESET)     Show migration history"
	@echo "  $(YELLOW)make migrate-rollback$(RESET)    Rollback last migration"
	@echo "  $(YELLOW)make init-db$(RESET)             Run app init_db script inside container"
	@echo "  $(YELLOW)make seed$(RESET)                Seed reference data"
	@echo "  $(YELLOW)make seed-rbac$(RESET)           Seed RBAC roles and permissions"
	@echo "  $(YELLOW)make seed-parish$(RESET)         Seed default parish and stations"
	@echo "  $(YELLOW)make check-db$(RESET)            Test database connection"
	@echo "  $(YELLOW)make dump-db$(RESET)             Dump database to dumps/<timestamp>.sql"
	@echo "  $(YELLOW)make load-dump dump=<file>$(RESET) Load a dump into the database"
	@echo ""
	@echo "$(GREEN)Admin:$(RESET)"
	@echo "  $(YELLOW)make superuser$(RESET)           Create the first superuser"
	@echo ""
	@echo "$(GREEN)SDK:$(RESET)"
	@echo "  $(YELLOW)make sdk$(RESET)                 Regenerate sdk/types.ts from live OpenAPI schema"
	@echo ""
	@echo "$(GREEN)Dev tools:$(RESET)"
	@echo "  $(YELLOW)make shell$(RESET)               Open Python shell inside api container"
	@echo "  $(YELLOW)make bash$(RESET)                Open bash shell inside api container"
	@echo "  $(YELLOW)make lint$(RESET)                Run ruff linter"
	@echo "  $(YELLOW)make clean$(RESET)               Remove __pycache__ and .pyc files"
	@echo ""

# ── Local dev (no Docker) ────────────────────────────────────
dev:
	@echo "$(GREEN)Starting uvicorn with hot-reload...$(RESET)"
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-stop:
	@pkill -f "uvicorn app.main:app" 2>/dev/null && echo "$(GREEN)Stopped$(RESET)" || echo "$(YELLOW)Not running$(RESET)"

# ── Docker lifecycle ─────────────────────────────────────────
build:
	@echo "$(GREEN)Building images...$(RESET)"
	$(COMPOSE) down --remove-orphans
	$(COMPOSE) build

build-clean:
	@echo "$(GREEN)Building images from scratch (no cache)...$(RESET)"
	$(COMPOSE) down --remove-orphans
	$(COMPOSE) build --no-cache

up:
	@echo "$(GREEN)Starting services...$(RESET)"
	$(COMPOSE) up -d
	@echo ""
	@echo "$(CYAN)Services running:$(RESET)"
	@echo "  API:     http://localhost:8000"
	@echo "  Docs:    http://localhost:8000/api/v1/docs"
	@echo "  Health:  http://localhost:8000/api/v1/health"
	@echo "  Adminer: http://localhost:8888"

down:
	@echo "$(RED)Stopping services...$(RESET)"
	$(COMPOSE) down --remove-orphans

restart: down up

logs:
ifdef s
	$(COMPOSE) logs -f $(s)
else
	$(COMPOSE) logs -f
endif

# ── First-time setup ─────────────────────────────────────────
setup:
	$(MAKE) ssl
	$(MAKE) build
	$(MAKE) up
	$(MAKE) init-db
	$(MAKE) seed
	$(MAKE) seed-rbac
	$(MAKE) seed-parish
	$(MAKE) superuser
	@echo ""
	@echo "$(GREEN)Setup complete!$(RESET)"

ssl:
	@echo "$(GREEN)Generating SSL certificates...$(RESET)"
	@mkdir -p nginx/ssl nginx/logs
	@chmod +x scripts/generate_ssl.sh
	@./scripts/generate_ssl.sh

# ── Database / Alembic ───────────────────────────────────────
migrate:
	@echo "$(GREEN)Applying Alembic migrations...$(RESET)"
	$(COMPOSE) exec api alembic upgrade head

migrate-auto:
ifndef m
	$(error Usage: make migrate-auto m="your migration message")
endif
	@echo "$(GREEN)Generating migration: $(m)$(RESET)"
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

migrate-history:
	$(COMPOSE) exec api alembic history --verbose

migrate-rollback:
	@echo "$(YELLOW)Rolling back last migration...$(RESET)"
	$(COMPOSE) exec api alembic downgrade -1

init-db:
	@echo "$(GREEN)Initialising database...$(RESET)"
	$(COMPOSE) exec api python3 -m app.scripts.init_db

seed:
	@echo "$(GREEN)Seeding reference data...$(RESET)"
	$(COMPOSE) exec api python3 -m app.scripts.seed_sacraments
	$(COMPOSE) exec api python3 -m app.scripts.seed_church_communities --force
	$(COMPOSE) exec api python3 -m app.scripts.seed_place_of_worship
	$(COMPOSE) exec api python3 -m app.scripts.seed_church_societies
	$(COMPOSE) exec api python3 -m app.scripts.seed_languages
	@echo "$(GREEN)Seeding complete.$(RESET)"

seed-rbac:
	@echo "$(GREEN)Seeding RBAC roles and permissions...$(RESET)"
	$(COMPOSE) exec api python3 -m app.scripts.seed_rbac
	@echo "$(GREEN)RBAC seeding complete.$(RESET)"

seed-parish:
	@echo "$(GREEN)Seeding default parish and stations...$(RESET)"
	$(COMPOSE) exec api python3 -m app.scripts.seed_parish
	@echo "$(GREEN)Parish seeding complete.$(RESET)"

check-db:
	@echo "$(YELLOW)Checking database connection...$(RESET)"
	@$(COMPOSE) exec api python3 -c "\
from app.core.database import db; \
from sqlalchemy import text; \
s = db.session().__enter__(); \
s.execute(text('SELECT 1')); \
print('$(GREEN)Database connection OK$(RESET)')"

superuser:
	@echo "$(GREEN)Creating superuser...$(RESET)"
	$(COMPOSE) exec api python3 -m app.scripts.create_superuser

load-parishioners:
	@echo "$(GREEN)Loading parishioners from dump...$(RESET)"
	$(COMPOSE) cp dumps/app_dump_20260310_075402.sql api:/app/dumps/app_dump_20260310_075402.sql
	$(COMPOSE) exec api python3 /app/app/scripts/load_from_dump.py

# ── Dumps ────────────────────────────────────────────────────
dump-db:
	@mkdir -p dumps
	@set -a && . ./.env && set +a && \
	STAMP=$$(date +%Y%m%d_%H%M%S) && \
	FILE="dumps/dump_$${STAMP}.sql" && \
	echo "$(GREEN)Dumping database to $${FILE}...$(RESET)" && \
	PGPASSWORD=$$POSTGRES_PASSWORD pg_dump \
		-h $$POSTGRES_SERVER \
		-p $$POSTGRES_PORT \
		-U $$POSTGRES_USER \
		-d $$POSTGRES_DB \
		--no-owner --no-acl \
		-f "$${FILE}" && \
	echo "$(GREEN)Dump saved to $${FILE}$(RESET)"

load-dump:
ifndef dump
	$(error Usage: make load-dump dump=<filename>)
endif
	@test -f dumps/$(dump) || (echo "$(RED)Error: dumps/$(dump) not found$(RESET)" && exit 1)
	@echo "$(YELLOW)Loading dumps/$(dump) ...$(RESET)"
	$(COMPOSE) exec -T db sh -c \
		'PGPASSWORD=$$POSTGRES_PASSWORD psql -h localhost -U $$POSTGRES_USER -d $$POSTGRES_DB' \
		< dumps/$(dump)
	@echo "$(GREEN)Dump loaded successfully.$(RESET)"

# ── Shells ───────────────────────────────────────────────────
shell:
	$(COMPOSE) exec api python3

bash:
	$(COMPOSE) exec api /bin/bash

# ── SDK generation ───────────────────────────────────────────
sdk:
	@echo "$(GREEN)Regenerating sdk/types.ts from OpenAPI schema...$(RESET)"
	$(COMPOSE) exec api mkdir -p /app/scripts /app/sdk
	$(COMPOSE) cp scripts/gen_sdk.py api:/app/scripts/gen_sdk.py
	$(COMPOSE) exec api python3 /app/scripts/gen_sdk.py
	$(COMPOSE) cp api:/app/sdk/types.ts sdk/types.ts
	@echo "$(CYAN)Done.$(RESET)"

# ── Linting / cleanup ────────────────────────────────────────
lint:
	@command -v ruff >/dev/null 2>&1 || pip install ruff -q
	ruff check app/

clean:
	@echo "$(GREEN)Cleaning up...$(RESET)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	@echo "$(GREEN)Done.$(RESET)"
