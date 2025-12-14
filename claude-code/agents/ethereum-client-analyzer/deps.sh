#!/bin/bash

# deps.sh for ethereum-client-analyzer agent
# Checks for ethpandaops-production-data MCP server availability

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${BLUE}Checking dependencies for ethereum-client-analyzer agent...${NC}"

# Check for claude-code (since this agent is designed to work within claude-code environment)
if command_exists claude; then
    echo -e "${GREEN}✓ claude is available${NC}"
    
    # Check if the ethpandaops-production-data MCP server is running
    echo -e "${BLUE}Checking MCP server status...${NC}"
    if claude mcp list | grep -q "ethpandaops-production-data.*✓ Connected"; then
        echo -e "${GREEN}✓ ethpandaops-production-data MCP server is connected${NC}"
    else
        echo -e "${RED}✗ ethpandaops-production-data MCP server is not connected${NC}"
        echo -e "${YELLOW}Please ensure the MCP server is running and configured in Claude Code${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}! claude command not found${NC}"
    echo -e "${RED}This agent requires Claude Code to be installed${NC}"
    exit 1
fi

echo -e "${BLUE}Note: This agent uses the ethpandaops-production-data MCP server${NC}"
echo -e "${BLUE}which provides access to Loki logs, Prometheus metrics, and ClickHouse data${NC}"

echo -e "${GREEN}✓ All dependencies are satisfied${NC}"

exit 0