# ─────────────────────────────────────────────────────────────
#  SFOACC Backend Makefile
# ─────────────────────────────────────────────────────────────

COMPOSE      = docker compose
COMPOSE_LOCAL = docker compose -f docker-compose.local.yml

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
	@echo "$(CYAN)╔══════════════════════════════════════════════════╗$(RESET)"
	@echo "$(CYAN)║           SFOACC Backend — Make Commands         ║$(RESET)"
	@echo "$(CYAN)╚══════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(GREEN)── Local Dev (no Docker) ──────────────────────────$(RESET)"
	@echo "  $(YELLOW)make dev$(RESET)"
	@echo "      Start uvicorn with hot-reload on http://localhost:8000"
	@echo "      Use this for local development without Docker."
	@echo ""
	@echo "$(GREEN)── Docker ─────────────────────────────────────────$(RESET)"
	@echo "  $(YELLOW)make build$(RESET)"
	@echo "      Build Docker images (uses layer cache — fast)."
	@echo ""
	@echo "  $(YELLOW)make build-clean$(RESET)"
	@echo "      Rebuild images from scratch, ignoring cache."
	@echo "      Use when dependencies or Dockerfile change."
	@echo ""
	@echo "  $(YELLOW)make up$(RESET)"
	@echo "      Start all services: api, db, nginx, adminer."
	@echo "      Requires SSL certs for all domains."
	@echo ""
	@echo "  $(YELLOW)make up backend=1$(RESET)"
	@echo "      Start backend only: api, db, adminer (no nginx)."
	@echo "      Use for local dev or when frontend is not set up yet."
	@echo "      API available at http://localhost:8000"
	@echo ""
	@echo "  $(YELLOW)make down$(RESET)"
	@echo "      Stop and remove all containers."
	@echo ""
	@echo "  $(YELLOW)make restart$(RESET)"
	@echo "      Stop then start all services. Accepts backend=1 flag."
	@echo "      Example: make restart backend=1"
	@echo ""
	@echo "  $(YELLOW)make logs$(RESET)"
	@echo "      Tail logs for all services."
	@echo ""
	@echo "  $(YELLOW)make logs s=api$(RESET)"
	@echo "      Tail logs for a specific service (api, db, nginx, adminer)."
	@echo ""
	@echo "$(GREEN)── First-time Setup ───────────────────────────────$(RESET)"
	@echo "  $(YELLOW)make setup$(RESET)"
	@echo "      Full setup: ssl → build → up → init-db → seed → superuser."
	@echo "      Run once on a fresh server."
	@echo ""
	@echo "  $(YELLOW)make ssl$(RESET)"
	@echo "      Generate self-signed SSL certs (dev only)."
	@echo "      On production, use certbot instead."
	@echo ""
	@echo "$(GREEN)── Database & Migrations ──────────────────────────$(RESET)"
	@echo "  $(YELLOW)make migrate$(RESET)"
	@echo "      Apply all pending Alembic migrations."
	@echo ""
	@echo "  $(YELLOW)make migrate-auto m=\"your message\"$(RESET)"
	@echo "      Auto-generate a new migration from model changes."
	@echo "      Example: make migrate-auto m=\"add phone to users\""
	@echo ""
	@echo "  $(YELLOW)make migrate-history$(RESET)"
	@echo "      Show full migration history."
	@echo ""
	@echo "  $(YELLOW)make migrate-rollback$(RESET)"
	@echo "      Undo the last applied migration."
	@echo ""
	@echo "  $(YELLOW)make init-db$(RESET)"
	@echo "      Run the init_db script inside the container."
	@echo "      Creates tables if they don't exist."
	@echo ""
	@echo "  $(YELLOW)make seed$(RESET)"
	@echo "      Seed reference data (sacraments, communities, languages, etc)."
	@echo ""
	@echo "  $(YELLOW)make seed-rbac$(RESET)"
	@echo "      Seed roles and permissions."
	@echo ""
	@echo "  $(YELLOW)make seed-parish$(RESET)"
	@echo "      Seed the default parish and stations."
	@echo ""
	@echo "  $(YELLOW)make check-db$(RESET)"
	@echo "      Test that the database connection is working."
	@echo ""
	@echo "  $(YELLOW)make dump-db$(RESET)"
	@echo "      Dump the database to dumps/<timestamp>.sql."
	@echo "      Use to back up or copy data to another environment."
	@echo ""
	@echo "  $(YELLOW)make load-dump dump=<filename>$(RESET)"
	@echo "      Wipe the database and restore from a dump file."
	@echo "      Example: make load-dump dump=dump_20260405_103405.sql"
	@echo ""
	@echo "$(GREEN)── Admin ───────────────────────────────────────────$(RESET)"
	@echo "  $(YELLOW)make superuser$(RESET)"
	@echo "      Create the first superuser account."
	@echo "      Uses FIRST_SUPERUSER_* values from .env."
	@echo ""
	@echo "$(GREEN)── SDK ─────────────────────────────────────────────$(RESET)"
	@echo "  $(YELLOW)make sdk$(RESET)"
	@echo "      Regenerate sdk/types.ts from the live OpenAPI schema."
	@echo "      Run after adding or changing API endpoints."
	@echo ""
	@echo "$(GREEN)── Dev Tools ───────────────────────────────────────$(RESET)"
	@echo "  $(YELLOW)make shell$(RESET)"
	@echo "      Open a Python shell inside the api container."
	@echo ""
	@echo "  $(YELLOW)make bash$(RESET)"
	@echo "      Open a bash shell inside the api container."
	@echo ""
	@echo "  $(YELLOW)make lint$(RESET)"
	@echo "      Run ruff linter on the app/ directory."
	@echo ""
	@echo "  $(YELLOW)make clean$(RESET)"
	@echo "      Remove all __pycache__ and .pyc files."
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
ifdef backend
	$(COMPOSE_LOCAL) up -d
	@echo ""
	@echo "$(CYAN)Services running (local — no nginx):$(RESET)"
	@echo "  API:     http://localhost:8000"
	@echo "  Docs:    http://localhost:8000/api/v1/docs"
	@echo "  Health:  http://localhost:8000/api/v1/health"
	@echo "  Adminer: http://localhost:8888"
else
	$(COMPOSE) up -d
	@echo ""
	@echo "$(CYAN)Services running:$(RESET)"
	@echo "  API:     https://localhost"
	@echo "  Docs:    https://localhost/api/v1/docs"
	@echo "  Health:  https://localhost/api/v1/health"
	@echo "  Adminer: http://localhost:8888"
endif

down:
	@echo "$(RED)Stopping services...$(RESET)"
ifdef backend
	$(COMPOSE_LOCAL) down --remove-orphans
else
	$(COMPOSE) down --remove-orphans
endif

restart: down up

logs:
ifdef backend
  ifdef s
	$(COMPOSE_LOCAL) logs -f $(s)
  else
	$(COMPOSE_LOCAL) logs -f
  endif
else
  ifdef s
	$(COMPOSE) logs -f $(s)
  else
	$(COMPOSE) logs -f
  endif
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
ifndef dump
	$(eval dump := app_dump_20260310_075402.sql)
endif
	@test -f dumps/$(dump) || (echo "$(RED)Error: dumps/$(dump) not found$(RESET)" && exit 1)
	@echo "$(GREEN)Loading parishioners from dumps/$(dump)...$(RESET)"
	$(COMPOSE) cp dumps/$(dump) api:/app/dumps/$(dump)
	$(COMPOSE) exec api python3 /app/app/scripts/load_from_dump.py $(dump)

# ── Dumps ────────────────────────────────────────────────────
dump-db:
	@mkdir -p dumps
	@STAMP=$$(date +%Y%m%d_%H%M%S) && \
	FILE="dumps/dump_$${STAMP}.sql" && \
	echo "$(GREEN)Dumping database to $${FILE}...$(RESET)" && \
	$(COMPOSE) exec -T db sh -c \
		'pg_dump -U $$POSTGRES_USER -d $$POSTGRES_DB --no-owner --no-acl' \
		> "$$FILE" && \
	echo "$(GREEN)Dump saved to $${FILE}$(RESET)"

load-dump:
ifndef dump
	$(error Usage: make load-dump dump=<filename>)
endif
	@test -f dumps/$(dump) || (echo "$(RED)Error: dumps/$(dump) not found$(RESET)" && exit 1)
	@echo "$(YELLOW)Wiping existing database...$(RESET)"
	$(COMPOSE) exec -T db sh -c \
		'psql -U $$POSTGRES_USER -d $$POSTGRES_DB -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
	@echo "$(YELLOW)Loading dumps/$(dump) ...$(RESET)"
	$(COMPOSE) exec -T db sh -c \
		'psql -U $$POSTGRES_USER -d $$POSTGRES_DB' \
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
