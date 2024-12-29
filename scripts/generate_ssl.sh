#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# SSL directory
SSL_DIR="nginx/ssl"
DOMAIN=$(grep DOMAIN .env | cut -d '=' -f2 || echo "localhost")

echo -e "${YELLOW}Generating SSL certificates for domain: ${DOMAIN}${NC}"

# Create SSL directory if it doesn't exist
mkdir -p ${SSL_DIR}

# Generate SSL certificate and key
echo -e "${GREEN}Generating SSL certificates...${NC}"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ${SSL_DIR}/server.key \
    -out ${SSL_DIR}/server.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=${DOMAIN}" \
    2>/dev/null

# Set proper permissions
chmod 644 ${SSL_DIR}/server.crt
chmod 600 ${SSL_DIR}/server.key

# Verify certificate
echo -e "${YELLOW}Verifying certificate...${NC}"
openssl x509 -in ${SSL_DIR}/server.crt -text -noout | grep "Subject: CN"

echo -e "${GREEN}SSL certificates generated successfully!${NC}"
echo -e "Certificate: ${YELLOW}${SSL_DIR}/server.crt${NC}"
echo -e "Private Key: ${YELLOW}${SSL_DIR}/server.key${NC}"