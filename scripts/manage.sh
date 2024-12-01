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
        docker-compose exec api "$@"
    else
        echo -e "${YELLOW}Running locally...${NC}"
        "$@"
    fi
}

# Function to create superuser
create_superuser() {
    echo -e "${GREEN}Creating superuser...${NC}"
    run_command python -m app.scripts.create_superuser
}

# Function to check database connection
check_db() {
    echo -e "${YELLOW}Checking database connection...${NC}"
    run_command python -c "
from app.core.database import db
from sqlalchemy import text
with db.session() as session:
    session.execute(text('SELECT 1'))
print('Database connection successful')
"
}

# Function to run server
run_server() {
    if is_docker; then
        echo -e "${YELLOW}Server is managed by Docker. Use 'docker-compose up' instead.${NC}"
    else
        echo -e "${GREEN}Starting development server...${NC}"
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    fi
}

# Function to show help
show_help() {
    echo -e "${GREEN}Available commands:${NC}"
    echo -e "  ${YELLOW}createsuperuser${NC}  - Create a superuser account"
    echo -e "  ${YELLOW}checkdb${NC}         - Check database connection"
    echo -e "  ${YELLOW}runserver${NC}       - Run development server (local only)"
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
    "shell")
        run_command python
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