#!/bin/bash

# scripts/dev.sh
set -e

# Colors for output
RED='\033[0;31m'
NC='\033[0m' # No Color
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if SSL certificates exist and are valid
check_ssl_certificates() {
    local ssl_dir="nginx/ssl"
    local cert_file="${ssl_dir}/server.crt"
    local key_file="${ssl_dir}/server.key"
    
    # Create SSL directory if it doesn't exist
    mkdir -p "$ssl_dir"
    
    # Check if both files exist
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        return 1
    fi

    # Check if certificate is readable
    if ! openssl x509 -in "$cert_file" -noout 2>/dev/null; then
        print_message "$YELLOW" "Invalid or corrupted certificate found"
        return 1
    fi

    # Check certificate expiration
    local expires_date
    expires_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d'=' -f2)
    local expires_epoch
    expires_epoch=$(date -d "$expires_date" +%s)
    local current_epoch
    current_epoch=$(date +%s)
    local days_left
    days_left=$(( (expires_epoch - current_epoch) / 86400 ))
    
    if [ $days_left -lt 30 ]; then
        print_message "$YELLOW" "SSL certificate will expire in $days_left days"
        return 1
    fi

    return 0
}

# Function to generate self-signed SSL certificate
generate_ssl_certificate() {
    local ssl_dir="nginx/ssl"
    mkdir -p "$ssl_dir"
    
    print_message "$BLUE" "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$ssl_dir/server.key" \
        -out "$ssl_dir/server.crt" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    chmod 644 "$ssl_dir/server.crt"
    chmod 600 "$ssl_dir/server.key"
    
    print_message "$GREEN" "SSL certificate generated successfully"
}

# Function to setup SSL
setup_ssl() {
    if ! check_ssl_certificates; then
        print_message "$YELLOW" "SSL certificates need to be generated..."
        generate_ssl_certificate
    else
        print_message "$GREEN" "Valid SSL certificates found"
    fi
}

# Function to check required files and directories
check_requirements() {
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_message "$RED" "Error: .env file not found!"
        print_message "$YELLOW" "Please create .env file with required variables"
        exit 1
    fi

    # Check if docker compose is installed
    if ! command -v docker &> /dev/null; then
        print_message "$RED" "Error: docker is not installed!"
        exit 1
    fi

    # Check if Nginx configuration exists
    if [ ! -f "nginx/conf.d/default.conf" ]; then
        print_message "$RED" "Error: Nginx configuration file not found at nginx/conf.d/default.conf!"
        exit 1
    fi

    # Create necessary directories
    print_message "$BLUE" "Creating necessary directories..."
    mkdir -p nginx/{ssl,logs}
}

# Function to wait for services health
wait_for_services() {
    print_message "$BLUE" "Waiting for services to be healthy..."
    local timeout=300  # 5 minutes timeout
    local elapsed=0
    local all_healthy=false

    while [ $elapsed -lt $timeout ]; do
        if docker compose ps | grep -q "unhealthy"; then
            print_message "$YELLOW" "Some services are still initializing... (${elapsed}s elapsed)"
            sleep 5
            elapsed=$((elapsed + 5))
        else
            all_healthy=true
            break
        fi
    done

    if [ "$all_healthy" = true ]; then
        print_message "$GREEN" "✔ All services are healthy!"
        print_message "$GREEN" "
Development environment is ready!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API:     https://localhost:8000
Adminer: https://localhost:8080
DB Info: https://localhost:8001
Health:  https://localhost:8001/health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 0
    else
        print_message "$RED" "✘ Timeout waiting for services to be healthy"
        return 1
    fi
}

# Main execution
main() {
    print_message "$BLUE" "Starting development environment setup..."
    
    # Check requirements
    check_requirements
    
    # Setup SSL
    setup_ssl
    
    # Start services
    print_message "$BLUE" "Building and starting services..."
    docker compose down --remove-orphans
    docker compose build
    docker compose up -d
    
    # Wait for services to be healthy
    wait_for_services
}

# Run main function
main