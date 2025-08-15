#!/bin/bash

# Start Services Script for AI Mentor Assistant
# This script starts both Q&A and Realtime services for the AI Mentor app

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting AI Mentor Assistant Services${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from template...${NC}"
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo -e "${YELLOW}📝 Please edit .env file with your configuration before running again${NC}"
        exit 1
    else
        echo -e "${RED}❌ No .env.template found. Please create .env file manually${NC}"
        exit 1
    fi
fi

# Check if OpenAI API key is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo -e "${YELLOW}⚠️  Please set your OPENAI_API_KEY in .env file${NC}"
    echo -e "${YELLOW}   Edit .env and add: OPENAI_API_KEY=sk-your-key-here${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Q&A Service (Port 8084)
echo -e "${GREEN}🔧 Starting Q&A Service on port 8084...${NC}"
nohup python production_backend.py > logs/qa_service.log 2>&1 &
QA_PID=$!
echo $QA_PID > logs/qa_service.pid
echo -e "${GREEN}✅ Q&A Service started (PID: $QA_PID)${NC}"

# Wait a moment for the service to start
sleep 2

# Start Realtime Service (Port 8080)
echo -e "${GREEN}🔧 Starting Realtime Service on port 8080...${NC}"
nohup python production_realtime.py > logs/realtime_service.log 2>&1 &
REALTIME_PID=$!
echo $REALTIME_PID > logs/realtime_service.pid
echo -e "${GREEN}✅ Realtime Service started (PID: $REALTIME_PID)${NC}"

# Wait for services to fully start
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 5

# Health check
echo -e "${GREEN}🔍 Checking service health...${NC}"

# Check Q&A Service
if curl -s http://localhost:8084/api/health > /dev/null; then
    echo -e "${GREEN}✅ Q&A Service is healthy (http://localhost:8084)${NC}"
else
    echo -e "${RED}❌ Q&A Service health check failed${NC}"
fi

# Check Realtime Service
if curl -s http://localhost:8080/api/health > /dev/null; then
    echo -e "${GREEN}✅ Realtime Service is healthy (http://localhost:8080)${NC}"
else
    echo -e "${RED}❌ Realtime Service health check failed${NC}"
fi

echo -e "${GREEN}🎉 AI Mentor Assistant is running!${NC}"
echo -e "${GREEN}   Q&A API: http://localhost:8084${NC}"
echo -e "${GREEN}   Realtime API: http://localhost:8080${NC}"
echo -e "${YELLOW}   Logs: logs/qa_service.log, logs/realtime_service.log${NC}"
echo -e "${YELLOW}   To stop services: ./scripts/stop_services.sh${NC}"
