#!/bin/bash

# EthPandaOps AI Cookbook Setup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMANDS_DIR="$SCRIPT_DIR/claude-code/commands"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
CLAUDE_DIR="$HOME/.claude"
CLAUDE_COMMANDS_DIR="$CLAUDE_DIR/commands"
TARGET_DIR="$CLAUDE_COMMANDS_DIR/ethpandaops"

echo "🐼 EthPandaOps AI Cookbook Setup"

# Create directories if they don't exist
[ ! -d "$COMMANDS_DIR" ] && { echo "❌ Error: claude-code/commands directory not found"; exit 1; }
[ ! -d "$CLAUDE_DIR" ] && mkdir -p "$CLAUDE_DIR"
[ ! -d "$CLAUDE_COMMANDS_DIR" ] && mkdir -p "$CLAUDE_COMMANDS_DIR"
[ -d "$TARGET_DIR" ] && rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Copy command files
echo "📋 Copying command files..."
commands_copied=0
for command_file in "$COMMANDS_DIR"/*.md; do
    if [ -f "$command_file" ]; then
        filename=$(basename "$command_file")
        cp "$command_file" "$TARGET_DIR/$filename"
        echo "   ✅ $filename"
        commands_copied=$((commands_copied + 1))
    fi
done
[ $commands_copied -eq 0 ] && echo "⚠️ No .md files found in $COMMANDS_DIR"

# Make scripts executable
echo "🔧 Setting script permissions..."
script_count=0
for script_file in "$SCRIPTS_DIR"/*.py; do
    if [ -f "$script_file" ]; then
        filename=$(basename "$script_file")
        chmod +x "$script_file"
        echo "   ✅ $filename"
        script_count=$((script_count + 1))
    fi
done
[ $script_count -eq 0 ] && echo "⚠️ No Python scripts found in $SCRIPTS_DIR"

# Handle PATH configuration
echo "🔧 Setting up scripts PATH..."
[ ! -d "$SCRIPTS_DIR" ] && mkdir -p "$SCRIPTS_DIR"

# Detect shell profile
SHELL_NAME=$(basename "$SHELL")
case "$SHELL_NAME" in
    "bash") PROFILE_FILE="${HOME}/.bashrc"; [ ! -f "$PROFILE_FILE" ] && [ -f "$HOME/.bash_profile" ] && PROFILE_FILE="$HOME/.bash_profile" ;;
    "zsh") PROFILE_FILE="$HOME/.zshrc" ;;
    *) PROFILE_FILE="$HOME/.profile" ;;
esac

# Update PATH if needed
PATH_UPDATED=false
if ! echo "$PATH" | grep -q "$SCRIPTS_DIR"; then
    if [ -f "$PROFILE_FILE" ] && grep -Fq "$SCRIPTS_DIR" "$PROFILE_FILE"; then
        echo "✅ Scripts directory already configured in $PROFILE_FILE"
    else
        echo "# EthPandaOps AI Cookbook scripts" >> "$PROFILE_FILE"
        echo "export PATH=\"\$PATH:$SCRIPTS_DIR\"" >> "$PROFILE_FILE"
        PATH_UPDATED=true
    fi
fi

# Print completion message
if [ $commands_copied -gt 0 ] || [ "$PATH_UPDATED" = true ] || [ $script_count -gt 0 ]; then
    echo -e "\n✅ Setup completed successfully!"
    [ "$PATH_UPDATED" = true ] && echo "⚠️ Restart your terminal or run 'source $PROFILE_FILE' to use scripts"
else
    echo -e "\n✅ All components already configured!"
fi