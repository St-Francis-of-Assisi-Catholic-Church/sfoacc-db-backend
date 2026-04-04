# St. Francis of Assisi Catholic Church — Backend

FastAPI · PostgreSQL · Nginx · Docker

---

## Prerequisites

- Docker & Docker Compose
- `make`
- OpenSSL (for SSL cert generation)
- Python 3.10+ with `uvicorn` (only for local non-Docker dev)

---

## Local Development

### First-time setup

```bash
git clone git@github.com:St-Francis-of-Assisi-Catholic-Church/sfoacc-db-backend.git
cd sfoacc-db-backend
cp .env.staging .env   # edit with your values
make setup             # ssl → build → up → init-db → seed → superuser
```

`make setup` spins up **api + db + nginx** in Docker, runs all migrations, seeds reference data, and creates the first superuser.

### Day-to-day

| Goal | Command |
|---|---|
| Start services | `make up` |
| Stop services | `make down` |
| Restart | `make restart` |
| View logs | `make logs` or `make logs s=api` |
| Run without Docker (hot-reload) | `make dev` |

### Service URLs

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/api/v1/docs |
| Health check | http://localhost:8000/api/v1/health |
| Adminer | http://localhost:8888 |

---

## Production Deployment (Bare Metal)

### 1. SSH into the server

From your local machine:

```bash
ssh ubuntu@<SERVER_IP>
```

> If you have a `.pem` key file: `ssh -i /path/to/key.pem ubuntu@<SERVER_IP>`

---

### 2. Add swap (the server has no swap by default)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make it persist across reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
free -h
```

---

### 3. Install Docker

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl

# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker apt repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow your user to run docker without sudo
sudo usermod -aG docker ubuntu

# Log out and back in for the group change to take effect
exit
# then: ssh ubuntu@<SERVER_IP>

# Verify
docker --version
docker compose version
```

---

### 4. Install make and git

```bash
sudo apt-get install -y make git
```

---

### 5. Generate a deploy key for GitHub

This key lets the server pull code from GitHub.

```bash
ssh-keygen -t ed25519 -C "sfoacc-server-deploy" -f ~/.ssh/sfoacc_deploy -N ""

# Print the public key — you'll add this to GitHub next
cat ~/.ssh/sfoacc_deploy.pub
```

Add the public key to GitHub:
> Repo → **Settings** → **Deploy keys** → **Add deploy key**
> - Title: `production server`
> - Key: paste the output of `cat ~/.ssh/sfoacc_deploy.pub`
> - Leave "Allow write access" unchecked

Tell SSH to use this key for GitHub:

```bash
cat >> ~/.ssh/config << 'EOF'

Host github.com
  IdentityFile ~/.ssh/sfoacc_deploy
  IdentitiesOnly yes
EOF
```

Test it:

```bash
ssh -T git@github.com
# Should say: Hi St-Francis-of-Assisi-Catholic-Church/...! You've successfully authenticated
```

---

### 6. Clone the repo

```bash
sudo mkdir -p /opt/sfoacc
sudo chown ubuntu:ubuntu /opt/sfoacc

git clone git@github.com:St-Francis-of-Assisi-Catholic-Church/sfoacc-db-backend.git /opt/sfoacc
cd /opt/sfoacc
```

---

### 7. Configure environment

```bash
cp .env.staging .env
nano .env   # or: vim .env
```

Key values to set for production:

```env
ENVIRONMENT=production
POSTGRES_SERVER=db        # always "db" — points to the db container
WEB_CONCURRENCY=6         # matches the server's 6 CPU cores
LOG_LEVEL=warning
```

---

### 8. First-time start

```bash
cd /opt/sfoacc
make setup
```

This runs: SSL cert generation → build → start → init-db → seed → seed-rbac → seed-parish → create superuser.

---

### 9. Set up GitHub Actions for auto-deploy

Every push to `main` will automatically deploy. You need to add 3 secrets to GitHub.

First, get the private key from the server:

```bash
cat ~/.ssh/sfoacc_deploy   # on the server
```

Then add these secrets at:
> Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Value |
|---|---|
| `SERVER_HOST` | Your static IP address |
| `SERVER_USER` | `ubuntu` |
| `SERVER_SSH_KEY` | The full output of `cat ~/.ssh/sfoacc_deploy` (private key) |

After this, every push to `main` triggers:

```
push to main
  └─ lint (ruff)
       └─ SSH to server
            ├─ git pull
            ├─ docker compose build api
            ├─ docker compose up -d
            ├─ alembic upgrade head
            └─ docker image prune
```

Pull requests run **lint only** — no deploy.

---

### SSL

The server uses self-signed certificates generated by `make ssl`. Browsers will show a warning — this is fine for internal/admin use. If you get a domain name later, point it to your static IP and use Certbot for a free Let's Encrypt cert.

---

## All Make Targets

```bash
make help
```

### Docker

| Command | Description |
|---|---|
| `make build` | Build images (with layer cache) |
| `make build-clean` | Build from scratch (no cache) |
| `make up` | Start api, db, nginx, adminer |
| `make down` | Stop and remove containers |
| `make restart` | down + up |
| `make logs [s=<service>]` | Tail logs |

### Database

| Command | Description |
|---|---|
| `make migrate` | Apply all pending Alembic migrations |
| `make migrate-auto m="msg"` | Auto-generate a new migration |
| `make migrate-history` | Show migration history |
| `make migrate-rollback` | Rollback last migration |
| `make init-db` | Run init_db script inside container |
| `make seed` | Seed reference data (sacraments, communities, etc.) |
| `make seed-rbac` | Seed RBAC roles and permissions |
| `make seed-parish` | Seed default parish and stations |
| `make superuser` | Create the first superuser |
| `make check-db` | Test database connection |
| `make dump-db` | Dump DB to `dumps/<timestamp>.sql` |
| `make load-dump dump=<file>` | Restore a dump into the running DB container |

### Dev Tools

| Command | Description |
|---|---|
| `make dev` | Run uvicorn locally with hot-reload (no Docker) |
| `make shell` | Python shell inside api container |
| `make bash` | Bash shell inside api container |
| `make lint` | Run ruff linter |
| `make ssl` | Generate/refresh self-signed SSL certs |
| `make sdk` | Regenerate `sdk/types.ts` from live OpenAPI schema |
| `make clean` | Remove `__pycache__` and `.pyc` files |

---

## Project Structure

```
.
├── app/
│   ├── api/v1/routes/    # Route handlers
│   ├── core/             # DB engine, config, security, exceptions
│   ├── middleware/        # Audit logging, HTTP request logger
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Business logic (email, SMS, reports, OTP)
│   └── scripts/          # Init, seed, and superuser scripts
├── alembic/              # Database migrations
├── nginx/
│   ├── prod/             # Nginx config (rate limiting, security headers)
│   ├── ssl/              # SSL certificates (auto-generated, gitignored)
│   └── logs/             # Nginx access/error logs
├── scripts/              # Shell utilities (SSL gen, server setup)
├── sdk/                  # Generated TypeScript types
├── dumps/                # Database dumps
├── .github/workflows/    # CI/CD pipeline
├── Makefile
├── docker-compose.yml
└── api.Dockerfile
```

---

## Troubleshooting

**Container not healthy**
```bash
make logs s=api
make logs s=nginx
```

**SSL issues**
```bash
rm -rf nginx/ssl/*
make ssl
make restart
```

**Port already in use**
```bash
sudo lsof -i :8000
```

**Reset everything (data loss — dev only)**
```bash
make down
docker volume rm sfoacc-db-backend_app-db-data
make setup
```
