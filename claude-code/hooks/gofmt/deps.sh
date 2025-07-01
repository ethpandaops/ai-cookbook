#!/bin/bash

# Dependency check for gofmt hook

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

deps_met=true

echo "Checking dependencies for gofmt hook..."
echo ""

# Check if jq is available (required for JSON parsing)
if command -v jq &> /dev/null; then
    echo -e "${GREEN}✓${NC} jq is installed"
    echo "  $(jq --version)"
else
    echo -e "${RED}✗${NC} jq is not installed (required for JSON parsing)"
    echo ""
    echo "To install jq:"
    echo "  macOS:    brew install jq"
    echo "  Ubuntu:   sudo apt install jq"
    echo "  Fedora:   sudo dnf install jq"
    echo "  Windows:  choco install jq"
    deps_met=false
fi

# Check if gofmt is available
if command -v gofmt &> /dev/null; then
    echo -e "${GREEN}✓${NC} gofmt is installed"
    echo "  $(go version 2>&1 | head -1)"
else
    echo -e "${RED}✗${NC} gofmt is not installed"
    echo ""
    echo "To install Go (which includes gofmt):"
    echo "  macOS:    brew install go"
    echo "  Ubuntu:   sudo apt install golang-go"
    echo "  Fedora:   sudo dnf install golang"
    echo "  Windows:  https://go.dev/dl/"
    echo ""
    echo "Or download from: https://go.dev/dl/"
    deps_met=false
fi

if [ "$deps_met" = true ]; then
    echo ""
    echo -e "${GREEN}All dependencies are satisfied!${NC}"
    exit 0
else
    echo ""
    echo -e "${YELLOW}Please install missing dependencies before using this hook.${NC}"
    exit 1
fi