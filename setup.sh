#!/bin/bash

# EthPandaOps AI Cookbook Setup Script
# This script:
# 1. Copies command files to ~/.claude/commands/ethpandaops/
# 2. Adds the scripts directory to PATH (if not already present)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMANDS_DIR="$SCRIPT_DIR/claude-code/commands"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
CLAUDE_DIR="$HOME/.claude"
CLAUDE_COMMANDS_DIR="$CLAUDE_DIR/commands"
TARGET_DIR="$CLAUDE_COMMANDS_DIR/ethpandaops"

echo "🐼 EthPandaOps AI Cookbook Setup"
echo "================================"

# Check if claude-code/commands directory exists
if [ ! -d "$COMMANDS_DIR" ]; then
    echo "❌ Error: claude-code/commands directory not found at $COMMANDS_DIR"
    exit 1
fi

# Create ~/.claude directory if it doesn't exist
if [ ! -d "$CLAUDE_DIR" ]; then
    echo "📁 Creating ~/.claude directory..."
    mkdir -p "$CLAUDE_DIR"
fi

# Create ~/.claude/commands directory if it doesn't exist
if [ ! -d "$CLAUDE_COMMANDS_DIR" ]; then
    echo "📁 Creating ~/.claude/commands directory..."
    mkdir -p "$CLAUDE_COMMANDS_DIR"
fi

# Remove existing ethpandaops directory if it exists
if [ -d "$TARGET_DIR" ]; then
    echo "🧹 Removing existing ethpandaops commands directory..."
    rm -rf "$TARGET_DIR"
fi

# Create the ethpandaops directory
echo "📁 Creating ethpandaops commands directory..."
mkdir -p "$TARGET_DIR"

# Copy all .md files from commands directory
echo "📋 Copying command files..."
commands_copied=0

for command_file in "$COMMANDS_DIR"/*.md; do
    if [ -f "$command_file" ]; then
        filename=$(basename "$command_file")
        cp "$command_file" "$TARGET_DIR/$filename"
        echo "   ✅ Copied: $filename"
        ((commands_copied++))
    fi
done

if [ $commands_copied -eq 0 ]; then
    echo "   ⚠️  No .md files found in $COMMANDS_DIR"
fi

# Handle PATH modification for scripts directory
echo ""
echo "🔧 Setting up scripts PATH..."

# Check if scripts directory exists
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "📁 Creating scripts directory..."
    mkdir -p "$SCRIPTS_DIR"
fi

# Detect shell and profile file
SHELL_NAME=$(basename "$SHELL")
case "$SHELL_NAME" in
    "bash")
        PROFILE_FILE="$HOME/.bashrc"
        if [ ! -f "$PROFILE_FILE" ] && [ -f "$HOME/.bash_profile" ]; then
            PROFILE_FILE="$HOME/.bash_profile"
        fi
        ;;
    "zsh")
        PROFILE_FILE="$HOME/.zshrc"
        ;;
    *)
        PROFILE_FILE="$HOME/.profile"
        ;;
esac

# Check if PATH already contains the scripts directory
if echo "$PATH" | grep -q "$SCRIPTS_DIR"; then
    echo "   ✅ Scripts directory already in PATH"
    PATH_UPDATED=false
else
    # Check if the PATH export is already in the profile file
    PATH_EXPORT="export PATH=\"\$PATH:$SCRIPTS_DIR\""
    if [ -f "$PROFILE_FILE" ] && grep -Fq "$SCRIPTS_DIR" "$PROFILE_FILE"; then
        echo "   ✅ Scripts directory already configured in $PROFILE_FILE"
        PATH_UPDATED=false
    else
        echo "   📝 Adding scripts directory to PATH in $PROFILE_FILE"
        echo "" >> "$PROFILE_FILE"
        echo "# EthPandaOps AI Cookbook scripts" >> "$PROFILE_FILE"
        echo "$PATH_EXPORT" >> "$PROFILE_FILE"
        echo "   ✅ Added to $PROFILE_FILE"
        PATH_UPDATED=true
    fi
fi

echo ""
if [ $commands_copied -gt 0 ] || [ "$PATH_UPDATED" = true ]; then
    echo "✅ Setup completed successfully!"
    echo ""
    echo "📋 Summary:"
    echo "   • Commands directory: $COMMANDS_DIR"
    if [ $commands_copied -gt 0 ]; then
        echo "   • Copied $commands_copied files to $TARGET_DIR"
    fi
    echo "   • Scripts directory: $SCRIPTS_DIR"
    if [ "$PATH_UPDATED" = true ]; then
        echo "   • Added scripts directory to PATH in $PROFILE_FILE"
    fi
    echo ""
    echo "🚀 Next steps:"
    echo "   • Commands are now available in Claude Code"
    if [ "$PATH_UPDATED" = true ]; then
        echo "   • Restart your terminal or run 'source $PROFILE_FILE' to use scripts"
    fi
    echo "   • Run './setup.sh' again after adding new commands or scripts"
    echo "   • Add new commands to claude-code/commands/ and scripts to scripts/"
else
    echo "✅ All components already configured!"
fi