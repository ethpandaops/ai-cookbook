#!/bin/bash

# EthPandaOps Code Standards Setup (Simplified)
# Adds fetch instructions to ~/.claude/CLAUDE.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/claude-code/code-standards/config.json"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to backup CLAUDE.md
backup_claude_md() {
    if [ -f "$CLAUDE_MD" ]; then
        local backup_dir="$HOME/.claude/backups"
        mkdir -p "$backup_dir"
        local backup_file="$backup_dir/CLAUDE.md.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$CLAUDE_MD" "$backup_file"
        log "Created backup: $backup_file"
    fi
}

# Function to check if ethpandaops section exists
has_ethpandaops_section() {
    if [ ! -f "$CLAUDE_MD" ]; then
        return 1
    fi
    
    grep -q "<!-- ETHPANDAOPS_STANDARDS_START -->" "$CLAUDE_MD"
}

# Function to remove existing ethpandaops section
remove_ethpandaops_section() {
    local input_file="$1"
    local temp_file
    temp_file=$(mktemp)
    
    awk '
    /<!-- ETHPANDAOPS_STANDARDS_START -->/ { in_section = 1; next }
    /<!-- ETHPANDAOPS_STANDARDS_END -->/ { in_section = 0; next }
    !in_section { print }
    ' "$input_file" > "$temp_file"
    
    echo "$temp_file"
}

# Function to generate ethpandaops section from config
generate_ethpandaops_section() {
    if [ ! -f "$CONFIG_FILE" ]; then
        error "Config file not found: $CONFIG_FILE"
        return 1
    fi
    
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed"
        return 1
    fi
    
    local temp_section
    temp_section=$(mktemp)
    
    # Start the section
    cat > "$temp_section" << 'EOF'
<!-- ETHPANDAOPS_STANDARDS_START -->
# ethpandaops

When making changes to supported file types, you MUST use WebFetch to download the latest coding standards from GitHub and apply them:
EOF
    
    # Add each enabled language
    jq -r '.languages | to_entries[] | select(.value.enabled == true) | @base64' "$CONFIG_FILE" | while read -r item; do
        decoded=$(echo "$item" | base64 --decode)
        lang_name=$(echo "$decoded" | jq -r '.value.name')
        patterns=$(echo "$decoded" | jq -r '.value.patterns | join(", ")')
        standards_url=$(echo "$decoded" | jq -r '.value.standards_url')
        
        echo "- **${lang_name}** (${patterns}): ${standards_url}" >> "$temp_section"
    done
    

    echo "After loading the standards, you should briefly mention \"Loaded 🐼 ethPandaOps 🐼 code standards for [language]\"" >> "$temp_section"
    # End the section
    echo "<!-- ETHPANDAOPS_STANDARDS_END -->" >> "$temp_section"
    
    echo "$temp_section"
}

# Function to add ethpandaops section
add_ethpandaops_section() {
    local force="${1:-false}"
    
    # Create ~/.claude directory if needed
    mkdir -p "$(dirname "$CLAUDE_MD")"
    
    # Check if section already exists
    if has_ethpandaops_section && [ "$force" != "true" ]; then
        warn "ethpandaops section already exists in CLAUDE.md"
        echo "Use --force to overwrite existing section"
        return 0
    fi
    
    log "Adding ethpandaops section to CLAUDE.md..."
    
    # Backup existing file
    backup_claude_md
    
    # Remove existing section if present
    local temp_file
    if [ -f "$CLAUDE_MD" ]; then
        temp_file=$(remove_ethpandaops_section "$CLAUDE_MD")
    else
        temp_file=$(mktemp)
        touch "$temp_file"
    fi
    
    # Generate new section from config
    local section_file
    section_file=$(generate_ethpandaops_section)
    
    # Create new CLAUDE.md
    local final_file
    final_file=$(mktemp)
    
    # Copy existing content (without ethpandaops section)
    if [ -s "$temp_file" ]; then
        cat "$temp_file" >> "$final_file"
        # Only add blank line if the file doesn't already end with one
        if [ "$(tail -c1 "$temp_file")" != "" ]; then
            echo "" >> "$final_file"
        fi
    fi
    
    # Add ethpandaops section
    cat "$section_file" >> "$final_file"
    
    # Replace original file
    mv "$final_file" "$CLAUDE_MD"
    
    # Cleanup
    rm -f "$temp_file" "$section_file"
    
    local lang_count
    lang_count=$(jq -r '[.languages | to_entries[] | select(.value.enabled == true)] | length' "$CONFIG_FILE")
    
    success "Added ethpandaops section to CLAUDE.md"
    success "Claude will now fetch standards for $lang_count language(s)"
    echo ""
    echo "View your updated CLAUDE.md: file://$CLAUDE_MD"
    echo "   (Cmd+click to open in your editor)"
    echo ""
    
    # Show the configured languages tree
    echo "Configured languages:"
    
    # Show enabled languages from config
    if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
        # Process each language separately for better formatting
        while read -r item; do
            decoded=$(echo "$item" | base64 --decode)
            lang_name=$(echo "$decoded" | jq -r '.value.name')
            patterns=$(echo "$decoded" | jq -r '.value.patterns | join(", ")')
            standards_url=$(echo "$decoded" | jq -r '.value.standards_url')
            
            echo "📄 $lang_name"
            echo "├── Files: $patterns"
            echo "└── URL: $standards_url"
        done < <(jq -r '.languages | to_entries[] | select(.value.enabled == true) | @base64' "$CONFIG_FILE")
        
        echo ""
        echo "Claude has been instructed to auto-fetch the code standards on-demand to preserve context & stay up to date."
        echo ""
        echo "Uninstall the code standards at any time with: $0 --uninstall"
    fi
}

# Function to show current status
show_status() {
    log "EthPandaOps Standards Status"
    echo "============================="
    echo ""
    
    if [ -f "$CLAUDE_MD" ]; then
        if has_ethpandaops_section; then
            success "ethpandaops section found in ~/.claude/CLAUDE.md"
            echo ""
            
            # Show enabled languages from config
            if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
                # Process each language separately for better formatting
                local lang_count=0
                while read -r item; do
                    decoded=$(echo "$item" | base64 --decode)
                    lang_name=$(echo "$decoded" | jq -r '.value.name')
                    patterns=$(echo "$decoded" | jq -r '.value.patterns | join(", ")')
                    standards_url=$(echo "$decoded" | jq -r '.value.standards_url')
                    
                    lang_count=$((lang_count + 1))
                    echo "📄 $lang_name"
                    echo "├── Files: $patterns"
                    echo "└── URL: $standards_url"
                done < <(jq -r '.languages | to_entries[] | select(.value.enabled == true) | @base64' "$CONFIG_FILE")
                
                echo ""
                echo "🤖 Claude auto-fetches the code standards on-demand to preserve context & stay up to date"
                echo ""
                echo "To uninstall the code standards at any time, run: $0 --uninstall"
            else
                echo "Standards for supported file types"
            fi
        else
            warn "No ethpandaops section in ~/.claude/CLAUDE.md"
            echo "Run: $0 --install"
        fi
    else
        warn "~/.claude/CLAUDE.md not found"
        echo "Run: $0 --install"
    fi
}

# Function to remove ethpandaops section
remove_section() {
    if [ ! -f "$CLAUDE_MD" ]; then
        warn "CLAUDE.md not found"
        return 0
    fi
    
    if ! has_ethpandaops_section; then
        warn "No ethpandaops section found to remove"
        return 0
    fi
    
    log "Removing ethpandaops section from CLAUDE.md..."
    
    # Backup first
    backup_claude_md
    
    # Remove section
    local temp_file
    temp_file=$(remove_ethpandaops_section "$CLAUDE_MD")
    mv "$temp_file" "$CLAUDE_MD"
    
    success "Removed ethpandaops section from CLAUDE.md"
}

# Main execution
main() {
    local install=false
    local force=false
    local remove=false
    local status=false
    
    echo "🐼 ethPandaOps Code Standards Setup"
    echo "==================================="
    echo ""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--install)
                install=true
                shift
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -u|--uninstall)
                remove=true
                shift
                ;;
            -s|--status)
                status=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -i, --install         Add ethpandaops fetch instructions to CLAUDE.md"
                echo "  -f, --force          Force overwrite existing ethpandaops section"
                echo "  -u, --uninstall      Remove ethpandaops section from CLAUDE.md"
                echo "  -s, --status         Show current status"
                echo "  -h, --help           Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                   # Install/update standards (default)"
                echo "  $0 --status          # Check current status"
                echo "  $0 --uninstall       # Remove standards"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    if [ "$remove" = true ]; then
        remove_section
    elif [ "$install" = true ]; then
        add_ethpandaops_section "$force"
    elif [ "$status" = true ]; then
        show_status
    else
        # Default: automatically install/update with force
        add_ethpandaops_section true
    fi
}

# Check if script is being executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi