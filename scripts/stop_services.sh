#!/bin/bash

# Stop Services Script for AI Mentor Assistant
# This script stops both Q&A and Realtime services for the AI Mentor app

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🛑 Stopping AI Mentor Assistant Services${NC}"

# Function to stop service by PID file
stop_service() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🔧 Stopping $service_name (PID: $pid)...${NC}"
            kill "$pid"
            
            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}⚠️  Force killing $service_name...${NC}"
                kill -9 "$pid" 2>/dev/null || true
            fi
            
            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name PID $pid not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠️  No PID file found for $service_name${NC}"
    fi
}

# Stop Q&A Service
stop_service "Q&A Service" "logs/qa_service.pid"

# Stop Realtime Service
stop_service "Realtime Service" "logs/realtime_service.pid"

# Also kill any remaining Python processes on our ports
echo -e "${YELLOW}🔍 Cleaning up any remaining processes on ports 8080 and 8084...${NC}"

# Kill processes on port 8084 (Q&A Service)
QA_PIDS=$(lsof -ti:8084 2>/dev/null || true)
if [ ! -z "$QA_PIDS" ]; then
    echo -e "${YELLOW}🔧 Killing processes on port 8084: $QA_PIDS${NC}"
    echo "$QA_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Kill processes on port 8080 (Realtime Service)
REALTIME_PIDS=$(lsof -ti:8080 2>/dev/null || true)
if [ ! -z "$REALTIME_PIDS" ]; then
    echo -e "${YELLOW}🔧 Killing processes on port 8080: $REALTIME_PIDS${NC}"
    echo "$REALTIME_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Clean up any python processes running our scripts
PYTHON_PIDS=$(pgrep -f "python.*production_backend.py\|python.*production_realtime.py" 2>/dev/null || true)
if [ ! -z "$PYTHON_PIDS" ]; then
    echo -e "${YELLOW}🔧 Killing remaining Python service processes: $PYTHON_PIDS${NC}"
    echo "$PYTHON_PIDS" | xargs kill 2>/dev/null || true
    sleep 2
    # Force kill if still running
    PYTHON_PIDS=$(pgrep -f "python.*production_backend.py\|python.*production_realtime.py" 2>/dev/null || true)
    if [ ! -z "$PYTHON_PIDS" ]; then
        echo "$PYTHON_PIDS" | xargs kill -9 2>/dev/null || true
    fi
fi

echo -e "${GREEN}✅ All AI Mentor Assistant services stopped${NC}"

# Show remaining processes (if any)
REMAINING=$(lsof -ti:8080,8084 2>/dev/null || true)
if [ ! -z "$REMAINING" ]; then
    echo -e "${RED}⚠️  Warning: Some processes still running on ports 8080/8084:${NC}"
    lsof -i:8080,8084 2>/dev/null || true
else
    echo -e "${GREEN}🎉 Ports 8080 and 8084 are now free${NC}"
fi
