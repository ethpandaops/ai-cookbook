#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for jq
if command_exists jq; then
    echo -e "${GREEN}✓ jq is installed${NC}"
else
    echo -e "${RED}✗ jq is not installed${NC}"
    echo -e "${YELLOW}Install jq:${NC}"
    echo "  macOS: brew install jq"
    echo "  Ubuntu/Debian: sudo apt-get install jq"
    echo "  CentOS/RHEL: sudo yum install jq"
    echo "  Windows: choco install jq"
    exit 1
fi

# Check for ast-grep
if command_exists ast-grep; then
    version=$(ast-grep --version 2>/dev/null | head -n1)
    echo -e "${GREEN}✓ ast-grep is installed${NC} ($version)"
else
    echo -e "${RED}✗ ast-grep is not installed${NC}"
    echo -e "${YELLOW}Install ast-grep:${NC}"
    echo "  macOS: brew install ast-grep"
    echo "  Cargo: cargo install ast-grep"
    echo "  npm: npm install -g @ast-grep/cli"
    echo "  Or visit: https://ast-grep.github.io/guide/quick-start.html"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies are satisfied${NC}"