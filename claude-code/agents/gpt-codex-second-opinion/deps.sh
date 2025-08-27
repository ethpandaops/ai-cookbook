#!/bin/bash

# deps.sh for gpt-codex-second-opinion agent
# Checks for codex installation and ensures gpt-5-high profile exists

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

# Check for codex
if command_exists codex; then
    echo -e "${GREEN}✓ codex is installed${NC}"
else
    echo -e "${RED}✗ codex is not installed${NC}"
    echo -e "${YELLOW}Please install codex to use the gpt-codex-second-opinion agent${NC}"
    echo "  Visit: https://github.com/openai/codex for installation instructions"
    exit 1
fi

# Check codex config directory exists
CODEX_CONFIG_DIR="$HOME/.codex"
CODEX_CONFIG_FILE="$CODEX_CONFIG_DIR/config.toml"

if [ ! -d "$CODEX_CONFIG_DIR" ]; then
    echo -e "${YELLOW}Creating codex config directory at $CODEX_CONFIG_DIR${NC}"
    mkdir -p "$CODEX_CONFIG_DIR"
fi

# Check if config.toml exists
if [ ! -f "$CODEX_CONFIG_FILE" ]; then
    echo -e "${YELLOW}Creating codex config file at $CODEX_CONFIG_FILE${NC}"
    echo "# Codex configuration file" > "$CODEX_CONFIG_FILE"
fi

# Check if gpt-5-high profile exists
if grep -q "\[profiles.gpt-5-high\]" "$CODEX_CONFIG_FILE"; then
    echo -e "${GREEN}✓ gpt-5-high profile is configured${NC}"
else
    echo -e "${YELLOW}Adding gpt-5-high profile to codex configuration${NC}"
    
    # Add the profile configuration
    cat >> "$CODEX_CONFIG_FILE" << 'EOF'

[profiles.gpt-5-high]
model = "gpt-5"
model_provider = "openai"
approval_policy = "never"
model_reasoning_effort = "high"
model_reasoning_summary = "detailed"

EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully added gpt-5-high profile${NC}"
    else
        echo -e "${RED}✗ Failed to add gpt-5-high profile to $CODEX_CONFIG_FILE${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ All dependencies are satisfied${NC}"

exit 0