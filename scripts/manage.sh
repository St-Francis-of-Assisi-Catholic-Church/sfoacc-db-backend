#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to create superuser
create_superuser() {
    echo -e "${GREEN}Creating superuser...${NC}"
    docker compose exec api python3 -m app.scripts.create_superuser
}

# Function to check database connection
check_db() {
    echo -e "${YELLOW}Checking database connection...${NC}"
    docker compose exec api python3 -c "
from app.core.database import db
from sqlalchemy import text
with db.session() as session:
    session.execute(text('SELECT 1'))
print('Database connection successful')
"
}

# Function to run server
run_server() {
    echo -e "${GREEN}Starting Docker containers...${NC}"
    docker compose up
}

# Function to build containers
build() {
    echo -e "${GREEN}Building Docker containers...${NC}"
    docker compose down --remove-orphans
    docker compose build
}

# Function to start services
start_services() {
    echo -e "${GREEN}Starting Docker services in detached mode...${NC}"
    docker compose up -d
}

# Function to access Python shell
access_shell() {
    echo -e "${GREEN}Opening Python shell in api container...${NC}"
    docker compose exec api python3
}

# Function to show help
show_help() {
    echo -e "${GREEN}Available commands:${NC}"
    echo -e "  ${YELLOW}createsuperuser${NC}  - Create a superuser account"
    echo -e "  ${YELLOW}checkdb${NC}         - Check database connection"
    echo -e "  ${YELLOW}runserver${NC}       - Run Docker containers (attached mode)"
    echo -e "  ${YELLOW}start${NC}           - Start services in detached mode"
    echo -e "  ${YELLOW}build${NC}           - Build Docker containers"
    echo -e "  ${YELLOW}shell${NC}           - Open Python shell in api container"
    echo -e "  ${YELLOW}help${NC}            - Show this help message"
}

# Main script
case "$1" in
    "createsuperuser")
        create_superuser
        ;;
    "checkdb")
        check_db
        ;;
    "runserver")
        run_server
        ;;
    "start")
        start_services
        ;;
    "build")
        build
        ;;
    "shell")
        access_shell
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac