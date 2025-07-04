#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if we're in the right directory
if [ ! -d "src/ai_cookbook" ]; then
    print_error "This script must be run from the root of the ai-cookbook repository"
    exit 1
fi

# Check Python version
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    print_error "Python 3.8 or higher is required"
    exit 1
fi

print_info "Setting up ai-cookbook..."

# No external dependencies needed

# Get the absolute path to this directory
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create a simple wrapper script
SCRIPT_CONTENT="#!/bin/bash
# ai-cookbook wrapper script

# Find the best Python 3 executable
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=\"python3\"
elif command -v python >/dev/null 2>&1 && python --version 2>&1 | grep -q \"Python 3\"; then
    PYTHON_CMD=\"python\"
else
    echo \"Error: Python 3 is required but not found\" >&2
    exit 1
fi

export PYTHONPATH=\"$REPO_ROOT/src:\$PYTHONPATH\"
exec \"\$PYTHON_CMD\" -m ai_cookbook.main \"\$@\"
"

# Detect user's shell and shell profile
if [[ "$SHELL" == *"zsh"* ]]; then
    PROFILE_FILE="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        PROFILE_FILE="$HOME/.bash_profile"
    else
        PROFILE_FILE="$HOME/.bashrc"
    fi
else
    PROFILE_FILE="$HOME/.profile"
fi

# Create bin directory in home if it doesn't exist
mkdir -p "$HOME/bin"

# Write the wrapper script
echo "$SCRIPT_CONTENT" > "$HOME/bin/ai-cookbook"
chmod +x "$HOME/bin/ai-cookbook"

# Add ~/bin to PATH if not already there
if ! echo "$PATH" | grep -q "$HOME/bin"; then
    echo "" >> "$PROFILE_FILE"
    echo "# Added by ethpandaops/ai-cookbook installer" >> "$PROFILE_FILE"
    echo "export PATH=\"\$HOME/bin:\$PATH\"" >> "$PROFILE_FILE"
    print_info "Added ~/bin to PATH in $PROFILE_FILE"
    print_info "You may need to restart your shell or run: source $PROFILE_FILE"
fi

print_success "ai-cookbook installed successfully!"
echo ""
print_info "You can now run: ai-cookbook"
print_info "Or if PATH isn't updated yet: ~/bin/ai-cookbook"
echo ""
print_info "The interactive installer provides the following options:"
echo "  • Claude Commands - AI-assisted development commands"
echo "  • Code Standards - Language-specific coding standards"
echo "  • Hooks - Automated formatting and linting"
echo "  • Scripts - Add utility scripts to PATH"
echo ""
print_info "Run 'ai-cookbook' to get started!"