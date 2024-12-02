#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


get_domain() {
    if [ -f .env ]; then
        DOMAIN=$(grep DOMAIN .env | cut -d '=' -f2)
        echo "${DOMAIN:-localhost}" # Default to localhost if not found
    else
        echo "localhost"
    fi
}


# Function to display service status and URLs
show_service_info() {
    DOMAIN=$(get_domain)
    echo -e "\n${GREEN}Service Status and URLs:${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    
    # Show URLs
    echo -e "\n${GREEN}Available URLs:${NC}"
    echo -e "API:        ${YELLOW}http://${DOMAIN}:8000${NC}"
    echo -e "           ${YELLOW}https://${DOMAIN}:8000${NC}"
    echo -e "Adminer:    ${YELLOW}http://${DOMAIN}:8080${NC}"
    echo -e "           ${YELLOW}https://${DOMAIN}:8080${NC}"
    echo -e "DB Info:    ${YELLOW}http://${DOMAIN}:8081${NC}"
    echo -e "           ${YELLOW}https://${DOMAIN}:8081${NC}"
}


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
    docker compose down -v
    docker compose down --remove-orphans
    docker compose build --no-cache
}

# Function to start services
start_services() {
    echo -e "${GREEN}Starting Docker services in detached mode...${NC}"
    docker compose up -d
    
    # Wait a moment for services to initialize
    echo -e "${YELLOW}Waiting for services to initialize...${NC}"
    sleep 5
    
    # Show service information
    show_service_info
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