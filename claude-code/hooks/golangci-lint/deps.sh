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

# Check for golangci-lint
if command_exists golangci-lint; then
    version=$(golangci-lint --version 2>/dev/null | head -n1)
    echo -e "${GREEN}✓ golangci-lint is installed${NC} ($version)"

    # Check if version supports the required flags (v2.1.0+ has --output.tab.path)
    version_num=$(echo "$version" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
    if [[ -n "$version_num" ]]; then
        # Convert version to comparable number (e.g., 2.1.0 -> 10210)
        IFS='.' read -ra VER <<< "$version_num"
        version_compare=$((VER[0] * 10000 + VER[1] * 100 + VER[2]))
        min_version=$((2 * 10000 + 1 * 100 + 0)) # 2.1.0

        if [[ $version_compare -lt $min_version ]]; then
            echo -e "${RED}✗ golangci-lint $version_num is too old${NC}"
            echo -e "${YELLOW}Required: v2.1.0 or later for --output.tab.path support${NC}"
            echo -e "${YELLOW}Current: $version_num${NC}"
            echo ""
            echo -e "${YELLOW}Update golangci-lint:${NC}"
            echo "  macOS: brew upgrade golangci-lint"
            echo "  Linux: curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b \$(go env GOPATH)/bin"
            echo "  Or visit: https://golangci-lint.run/usage/install/"
            exit 1
        fi
    fi
else
    echo -e "${RED}✗ golangci-lint is not installed${NC}"
    echo -e "${YELLOW}Install golangci-lint:${NC}"
    echo "  macOS: brew install golangci-lint"
    echo "  Linux: curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b \$(go env GOPATH)/bin"
    echo "  Windows: choco install golangci-lint"
    echo "  Or visit: https://golangci-lint.run/usage/install/"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies are satisfied${NC}"
