#!/bin/bash

# Fast LastMile API - Docker Deployment Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Fast LastMile API Docker Deployment${NC}"
echo -e "${BLUE}=================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Docker installation
if ! command_exists docker; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Check for environment file
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "${YELLOW}Creating from production template...${NC}"

    if [ -f "env.production.example" ]; then
        cp env.production.example .env
        echo -e "${GREEN}Created .env from env.production.example${NC}"
        echo -e "${YELLOW}Please edit .env file with your configuration before continuing${NC}"
        read -p "Press Enter after editing .env file..."
    else
        echo -e "${RED}Error: Neither .env nor env.production.example found${NC}"
        exit 1
    fi
fi

# Parse command line arguments
ACTION=${1:-"up"}
DETACHED=""

if [ "$2" == "-d" ]; then
    DETACHED="-d"
fi

case $ACTION in
    "up"|"start")
        echo -e "${GREEN}Starting services...${NC}"
        docker-compose up --build $DETACHED
        ;;

    "down"|"stop")
        echo -e "${YELLOW}Stopping services...${NC}"
        docker-compose down
        ;;

    "restart")
        echo -e "${YELLOW}Restarting services...${NC}"
        docker-compose down
        docker-compose up --build $DETACHED
        ;;

    "logs")
        echo -e "${BLUE}Showing logs...${NC}"
        docker-compose logs -f
        ;;

    "migrate")
        echo -e "${GREEN}Running database migrations...${NC}"
        docker-compose exec fast-lastmile-api alembic upgrade head
        ;;

    "shell")
        echo -e "${BLUE}Opening shell in container...${NC}"
        docker-compose exec fast-lastmile-api /bin/bash
        ;;

    "build")
        echo -e "${GREEN}Building images...${NC}"
        docker-compose build
        ;;

    "status")
        echo -e "${BLUE}Service status:${NC}"
        docker-compose ps
        ;;

    *)
        echo -e "${YELLOW}Usage: $0 [command] [options]${NC}"
        echo ""
        echo "Commands:"
        echo "  up, start    - Start all services"
        echo "  down, stop   - Stop all services"
        echo "  restart      - Restart all services"
        echo "  logs         - Show logs"
        echo "  migrate      - Run database migrations"
        echo "  shell        - Open shell in API container"
        echo "  build        - Build Docker images"
        echo "  status       - Show service status"
        echo ""
        echo "Options:"
        echo "  -d           - Run in detached mode (for up/start/restart)"
        exit 1
        ;;
esac