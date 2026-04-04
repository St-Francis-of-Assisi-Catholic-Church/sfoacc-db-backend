#!/bin/bash
# ─────────────────────────────────────────────────────────────
# SFOACC Server Setup — Ubuntu 24.04
# Run once as root (or with sudo) on a fresh bare metal server
# Usage: sudo bash scripts/server-setup.sh
# ─────────────────────────────────────────────────────────────
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}==> $1${NC}"; }
success() { echo -e "${GREEN}✔  $1${NC}"; }
warn()    { echo -e "${YELLOW}!  $1${NC}"; }

# ── 1. Swap (2 GB) ───────────────────────────────────────────
info "Configuring 2 GB swap..."
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  success "Swap created"
else
  warn "Swap file already exists — skipping"
fi

# ── 2. Docker Engine ─────────────────────────────────────────
info "Installing Docker..."
apt-get update -q
apt-get install -y -q ca-certificates curl

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -q
apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add ubuntu user to docker group (no sudo needed for docker commands)
usermod -aG docker ubuntu

success "Docker installed: $(docker --version)"

# ── 3. Project directory ─────────────────────────────────────
info "Creating project directory /opt/sfoacc..."
mkdir -p /opt/sfoacc
chown ubuntu:ubuntu /opt/sfoacc
success "Done"

# ── 4. Deploy SSH key for GitHub ─────────────────────────────
info "Generating deploy key for GitHub..."
DEPLOY_KEY_PATH="/home/ubuntu/.ssh/id_ed25519_sfoacc_deploy"
if [ ! -f "$DEPLOY_KEY_PATH" ]; then
  sudo -u ubuntu ssh-keygen -t ed25519 -C "sfoacc-deploy" -f "$DEPLOY_KEY_PATH" -N ""
  success "Deploy key created at $DEPLOY_KEY_PATH"
else
  warn "Deploy key already exists — skipping"
fi

# ── 5. Next steps ────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Server setup complete. Next steps:${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}1. Add this deploy public key to GitHub repo → Settings → Deploy keys:${NC}"
echo ""
cat "${DEPLOY_KEY_PATH}.pub"
echo ""
echo -e "${YELLOW}2. Log out and back in (so docker group takes effect), then:${NC}"
echo ""
echo "   git clone git@github.com:St-Francis-of-Assisi-Catholic-Church/sfoacc-db-backend.git /opt/sfoacc"
echo "   cd /opt/sfoacc"
echo "   cp .env.staging .env"
echo "   # Edit .env — set POSTGRES_SERVER=db, WEB_CONCURRENCY=6, ENVIRONMENT=production"
echo "   make setup"
echo ""
echo -e "${YELLOW}3. Add these secrets to GitHub repo → Settings → Secrets → Actions:${NC}"
echo ""
echo "   SERVER_HOST   = <your server IP>"
echo "   SERVER_USER   = ubuntu"
echo "   SERVER_SSH_KEY = <paste the PRIVATE key below>"
echo ""
echo -e "${YELLOW}Private key (paste as SERVER_SSH_KEY secret):${NC}"
cat "${DEPLOY_KEY_PATH}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
