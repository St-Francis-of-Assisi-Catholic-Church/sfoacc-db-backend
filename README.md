# St. Francis of Assisi Catholic Church DB Project Backend

# Project Setup Documentation

## Overview

This project uses Docker for containerization and includes several services:

- PostgreSQL Database
- Adminer (Database Management Tool)
- Nginx (Reverse Proxy)
- API Service

## Prerequisites

- Docker and Docker Compose
- Bash shell (for running scripts)
- OpenSSL (for SSL certificate generation)

## Quick Start

1. Clone the repository:

```bash
git clone git@github.com:St-Francis-of-Assisi-Catholic-Church/sfoacc-db-backend.git
cd sfoacc-db-backend
```

2. Copy the sample environment file and modify as needed:

```bash
cp sample.env .env
```

3. Run the development script:

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

## What the Setup Script Does

The `dev.sh` script automates the entire setup process:

1. **Requirement Check**

   - Verifies presence of `.env` file
   - Checks if docker-compose is installed
   - Validates Nginx configuration
   - Creates necessary directories

2. **SSL Certificate Setup**

   - Checks for existing SSL certificates
   - Generates self-signed certificates if needed
   - Validates certificate expiration

3. **Service Deployment**
   - Stops any existing containers
   - Builds fresh containers
   - Starts all services
   - Waits for health checks to pass

## Accessing Services

Once the setup is complete, you can access the following services:

| Service           | URL                           | Description                   |
| ----------------- | ----------------------------- | ----------------------------- |
| API               | https://localhost:8000        | Main API endpoint             |
| API Documentation | https://localhost:8000/docs   | API Swager documentation      |
| Adminer           | https://localhost:8080        | Database management interface |
| DB Info           | https://localhost:8001        | Database status information   |
| Health Check      | https://localhost:8001/health | Service health status         |

## Project Structure

```
.
├── app/
│   ├── api/                  # API endpoints and routes
│   └── core/                # Core application logic
├── docker-compose.yml       # Docker composition configuration
├── sample.env              # Sample environment variables
├── .env                    # Environment variables (created from sample.env)
├── nginx/
│   ├── conf.d/             # Nginx configuration
│   ├── ssl/               # SSL certificates
│   └── logs/              # Nginx logs
└── scripts/
    └── dev.sh            # Development setup script
```

## Notes

# Make script executable

chmod +x scripts/manage.sh

# Create superuser

./scripts/manage.sh createsuperuser

# Check database connection

./scripts/manage.sh checkdb

# Run development server (local only)

./scripts/manage.sh runserver

# Open Python shell

./scripts/manage.sh shell

# Show help

./scripts/manage.sh help

## Environment Variables

The project uses environment variables for configuration. Copy `sample.env` to `.env` and adjust the values as needed.

## SSL Certificates

The project uses SSL for secure communication. The setup script automatically:

- Generates self-signed certificates for development
- Places them in `nginx/ssl/`
- Validates existing certificates
- Warns about expiring certificates (30 days threshold)

## Health Checks

All services include health checks to ensure proper operation:

- Database: Checks PostgreSQL connectivity
- Adminer: Verifies web interface accessibility
- API: Validates endpoint responsiveness
- Nginx: Confirms proxy functionality

## Troubleshooting

1. **SSL Certificate Issues**

   ```bash
   # Regenerate certificates manually
   rm -rf nginx/ssl/*
   ./scripts/dev.sh
   ```

2. **Service Health Check Failures**

   ```bash
   # View service logs
   docker-compose logs [service-name]
   ```

3. **Port Conflicts**
   ```bash
   # Check for port usage
   sudo lsof -i :[port-number]
   ```

## Development Notes

- All services use SSL/TLS encryption
- The API includes CORS headers for frontend integration
- Logs are available in `nginx/logs/`
- Database data is persisted in a Docker volume

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your License Information]
