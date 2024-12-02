#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if running in Docker
is_docker() {
    if [ "$(docker ps -q -f name=api)" ]; then
        return 0  # true in bash
    else
        return 1  # false in bash
    fi
}

# Function to run command in docker or locally
run_command() {
    if is_docker; then
        echo -e "${YELLOW}Running in Docker container...${NC}"
        docker compose exec api "$@"
    else
        echo -e "${YELLOW}Running locally...${NC}"
        "$@"
    fi
}

# Function to create superuser
create_superuser() {
    echo -e "${GREEN}Creating superuser...${NC}"
    if is_docker; then
        docker compose exec api python3 -m app.scripts.create_superuser
    else
        python3 -m app.scripts.create_superuser
    fi
}

# Function to check database connection
check_db() {
    echo -e "${YELLOW}Checking database connection...${NC}"
    if is_docker; then
        docker compose exec api python3 -c "
from app.core.database import db
from sqlalchemy import text
with db.session() as session:
    session.execute(text('SELECT 1'))
print('Database connection successful')
"
    else
        python3 -c "
from app.core.database import db
from sqlalchemy import text
with db.session() as session:
    session.execute(text('SELECT 1'))
print('Database connection successful')
"
    fi
}

# Function to run server
run_server() {
    if is_docker; then
        echo -e "${GREEN}Starting Docker containers...${NC}"
        docker compose up
    else
        echo -e "${GREEN}Starting development server...${NC}"
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    fi
}

# Function to build containers
build() {
    if is_docker; then
        echo -e "${GREEN}Building Docker containers...${NC}"
        docker compose down --remove-orphans
        docker compose build
    else
        echo -e "${RED}Build command only available in Docker mode${NC}"
    fi
}


# function to start services
start_services() {
    if is_docker; then
        echo -e "${GREEN}Starting Docker services within the containers...${NC}"
        docker compose up -d
     else
        echo -e "${RED}Build command only available in Docker mode${NC}"
    fi
}

# Function to show help
show_help() {
    echo -e "${GREEN}Available commands:${NC}"
    echo -e "  ${YELLOW}createsuperuser${NC}  - Create a superuser account"
    echo -e "  ${YELLOW}checkdb${NC}         - Check database connection"
    echo -e "  ${YELLOW}runserver${NC}       - Run development server or Docker containers"
    echo -e "  ${YELLOW}start_services${NC}  - Starts services in the docker containers"
    echo -e "  ${YELLOW}build${NC}           - Build Docker containers"
    echo -e "  ${YELLOW}shell${NC}           - Open Python shell with app context"
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
    "start_services")
        start_services
        ;;
    "build")
        build
        ;;
    "shell")
        if is_docker; then
            docker compose exec api python3
        else
            python3
        fi
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