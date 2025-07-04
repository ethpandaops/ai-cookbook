#!/bin/bash

# Dependency check for eslint hook

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

deps_met=true

echo "Checking dependencies for eslint hook..."
echo ""

# Check if jq is available (required for JSON parsing)
if command -v jq &> /dev/null; then
    echo -e "${GREEN}✓${NC} jq"
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

# Check if npx is available
if command -v npx &> /dev/null; then
    echo -e "${GREEN}✓${NC} npx"
else
    echo -e "${RED}✗${NC} npx is not installed"
    echo ""
    echo "To install npx (comes with npm 5.2+):"
    echo "  macOS:    brew install node       # npx included with Node.js"
    echo "  Ubuntu:   sudo apt install nodejs npm"
    echo "  Fedora:   sudo dnf install nodejs npm"
    echo "  Windows:  choco install nodejs    # npx included with Node.js"
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