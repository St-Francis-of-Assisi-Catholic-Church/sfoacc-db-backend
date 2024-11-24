#!/bin/bash

# scripts/generate-ssl.sh
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Set variables for certificate generation
SSL_DIR="nginx/ssl"
DAYS_VALID=365
RSA_KEY_SIZE=2048

# Configuration for SSL certificate
CONFIG_FILE="${SSL_DIR}/openssl.conf"
COUNTRY="US"
STATE="State"
LOCALITY="City"
ORGANIZATION="Development"
ORGANIZATIONAL_UNIT="IT"
COMMON_NAME="localhost"
EMAIL="admin@localhost"
DOMAINS="localhost,127.0.0.1"

# Create SSL directory if it doesn't exist
mkdir -p $SSL_DIR

print_message $GREEN "Generating SSL certificates for development..."

# Create OpenSSL configuration file
cat > $CONFIG_FILE << EOF
[req]
default_bits = ${RSA_KEY_SIZE}
prompt = no
default_md = sha256
x509_extensions = v3_req
distinguished_name = dn

[dn]
C = ${COUNTRY}
ST = ${STATE}
L = ${LOCALITY}
O = ${ORGANIZATION}
OU = ${ORGANIZATIONAL_UNIT}
CN = ${COMMON_NAME}
emailAddress = ${EMAIL}

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Generate SSL certificate and key
print_message $YELLOW "Generating private key and certificate..."
openssl req \
    -x509 \
    -nodes \