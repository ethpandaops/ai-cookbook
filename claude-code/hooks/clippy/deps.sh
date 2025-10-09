#!/bin/bash

# Dependency check for clippy hook

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

deps_met=true

echo "Checking dependencies for clippy hook..."
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

# Check if cargo is available
if command -v cargo &> /dev/null; then
    echo -e "${GREEN}✓${NC} cargo"

    # Check if clippy is installed
    if cargo clippy --version &> /dev/null; then
        echo -e "${GREEN}✓${NC} clippy"
    else
        echo -e "${RED}✗${NC} clippy is not installed"
        echo ""
        echo "To install clippy:"
        echo "  rustup component add clippy"
        deps_met=false
    fi
else
    echo -e "${RED}✗${NC} cargo is not installed"
    echo ""
    echo "To install Rust (which includes cargo):"
    echo "  Install from: https://rustup.rs/"
    echo ""
    echo "After installing Rust, add clippy:"
    echo "  rustup component add clippy"
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
