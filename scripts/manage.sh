#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


# Default environment
ENV=${2:-prod}


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
    echo -e "API:       ${YELLOW}http://${DOMAIN}:8000${NC}"
    echo -e "           ${YELLOW}https://${DOMAIN}:8000${NC}"
    
    # Show Adminer URLs only in local mode
    if [ "$ENV" == "local" ]; then
        echo -e "Adminer:   ${YELLOW}http://${DOMAIN}:8080${NC}"
        echo -e "           ${YELLOW}https://${DOMAIN}:8080${NC}"
    fi
    
    echo -e "Health:    ${YELLOW}http://${DOMAIN}:8081${NC}"
    echo -e "           ${YELLOW}https://${DOMAIN}:8081${NC}"
}


# Function to initiliaze db
init_db() {
    echo -e "${GREEN}Initializing database...${NC}"
    docker compose exec api python3 -m app.scripts.init_db
}

seed_church_data() {
    echo -e "${GREEN}Seeding church data table...${NC}"
    docker compose exec api python3 -m app.scripts.seed_sacraments
    docker compose exec api python3 -m app.scripts.seed_church_communities --force
    docker compose exec api python3 -m app.scripts.seed_place_of_worship
    docker compose exec api python3 -m app.scripts.seed_church_societies
    docker compose exec api python3 -m app.scripts.seed_languages
    # add rest of date scripts here
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
    # echo -e "${GREEN}Starting Docker containers...${NC}"
    # docker compose up
    if [ "$ENV" == "local" ]; then
        echo -e "${GREEN}Starting Docker containers in LOCAL mode...${NC}"
        export ENVIRONMENT=local
        docker compose --profile local up
    else
        echo -e "${GREEN}Starting Docker containers in PRODUCTION mode...${NC}"
        export ENVIRONMENT=prod
        docker compose up
    fi
}

# Function to build containers
build() {
    # echo -e "${GREEN}Building Docker containers...${NC}"
     # Note: Using 'docker compose down' instead of 'docker compose down -v'
    # to preserve the database volume during rebuilds
    # docker compose down -v
    # docker compose down 
    # docker compose down --remove-orphans
    # docker compose build --no-cache
    if [ "$ENV" == "local" ]; then
        echo -e "${GREEN}Building Docker containers for LOCAL development...${NC}"
        export ENVIRONMENT=local
        docker compose --profile local down 
        docker compose --profile local down --remove-orphans
        docker compose --profile local build --no-cache
    else
        echo -e "${GREEN}Building Docker containers for PRODUCTION...${NC}"
        export ENVIRONMENT=prod
        docker compose down 
        docker compose down --remove-orphans
        docker compose build --no-cache
    fi
}

# Function to start services
start_services() {
    # echo -e "${GREEN}Starting Docker services in detached mode...${NC}"
    # docker compose up -d
    if [ "$ENV" == "local" ]; then
        echo -e "${GREEN}Starting Docker services in LOCAL mode (detached)...${NC}"
        export ENVIRONMENT=local
        docker compose --profile local up -d
    else
        echo -e "${GREEN}Starting Docker services in PRODUCTION mode (detached)...${NC}"
        export ENVIRONMENT=prod
        docker compose up -d
    fi
    
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

# function to access container's bash shell
access_bash() {
    echo -e "${GREEN}Opening bash shell in api container...${NC}"
    docker compose exec api /bin/bash
}

# Function to generate SSL certificates
generate_ssl() {
    echo -e "${GREEN}Generating SSL certificates...${NC}"
    chmod +x scripts/generate_ssl.sh
    ./scripts/generate_ssl.sh
}

# Function to setup project
setup_project() {
    # echo -e "${GREEN}Setting up project...${NC}"
    if [ "$ENV" == "local" ]; then
        echo -e "${GREEN}Setting up project in LOCAL mode...${NC}"
    else
        echo -e "${GREEN}Setting up project in PRODUCTION mode...${NC}"
    fi
    
    # Create necessary directories
    mkdir -p nginx/conf.d nginx/logs
    
    # Generate SSL certificates
    generate_ssl
    
    # Build and start services
    build
    start_services

    # create superuser
    create_superuser

    # see data
    seed_church_data
}

# Function to show help
show_help() {
    echo -e "  ${GREEN}Available commands:${NC}"
    echo -e "  ${YELLOW}setup [env]${NC}           - Initial project setup (directories, SSL, build)"
    echo -e "  ${YELLOW}seed${NC}                  - Seed church data"
    echo -e "  ${YELLOW}ssl${NC}                   - Generate SSL certificates"
    echo -e "  ${YELLOW}initdb${NC}                - Initialize db"
    echo -e "  ${YELLOW}createsuperuser${NC}       - Create a superuser account"
    echo -e "  ${YELLOW}checkdb${NC}               - Check database connection"
    echo -e "  ${YELLOW}runserver [env]${NC}       - Run Docker containers (attached mode)"
    echo -e "  ${YELLOW}start [env]${NC}           - Start services in detached mode"
    echo -e "  ${YELLOW}build [env]${NC}           - Build Docker containers"
    echo -e "  ${YELLOW}shell${NC}                 - Open Python shell in api container"
    echo -e "  ${YELLOW}bash${NC}                  - Open Container's bash shell in api"
    echo -e "  ${YELLOW}help${NC}                  - Show this help message"
    echo -e ""
    echo -e "  ${GREEN}Environment flag [env]:${NC}"
    echo -e "  ${YELLOW}local${NC}                 - Run in local development mode with database and adminer"
    echo -e "  ${YELLOW}prod${NC}                  - Run in production mode (default if no env is specified)"
    echo -e "  ${YELLOW}Examples:${NC} './start.sh build local' or './start.sh runserver'"
}

# Main script
case "$1" in
    "initdb")
        init_db
        ;;
    "setup")
        setup_project
        ;;
    "seed")
        seed_church_data
        ;;
    "ssl")
        generate_ssl
        ;;
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
    "bash")
        access_bash
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