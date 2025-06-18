#!/bin/bash

# Fast LastMile API - Development Startup Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Fast LastMile API...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from template...${NC}"
    cp env.example .env
    echo -e "${YELLOW}Please edit .env file with your configuration before running again.${NC}"
    exit 1
fi

# Create required directories
echo -e "${GREEN}Creating required directories...${NC}"
mkdir -p uploads outputs data logs

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Check if ORS server is running
echo -e "${GREEN}Checking ORS server connection...${NC}"
ORS_URL=$(grep ORS_BASE_URL .env | cut -d '=' -f2)
if [ -z "$ORS_URL" ]; then
    ORS_URL="http://localhost:6080"
fi

if curl -s --max-time 5 "$ORS_URL/ors/v2/health" > /dev/null; then
    echo -e "${GREEN}✓ ORS server is running at $ORS_URL${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Could not connect to ORS server at $ORS_URL${NC}"
    echo -e "${YELLOW}  Make sure OpenRouteService is running before processing requests.${NC}"
fi

# Start the application
echo -e "${GREEN}Starting FastAPI application...${NC}"
echo -e "${GREEN}API will be available at: http://localhost:8000${NC}"
echo -e "${GREEN}API Documentation: http://localhost:8000/docs${NC}"
echo -e "${GREEN}Health Check: http://localhost:8000/health${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000