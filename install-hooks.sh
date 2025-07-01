#!/bin/bash

# Claude Code Hooks Setup
# Install and manage hooks for Claude Code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/claude-code/hooks"
CLAUDE_DIR="$HOME/.claude"
CLAUDE_CONFIG_FILE="$CLAUDE_DIR/settings.json"
USER_HOOKS_DIR="$CLAUDE_DIR/hooks/ethpandaops"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[HOOKS]${NC} $1"
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

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Function to backup settings.json
backup_settings() {
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        local backup_dir="$CLAUDE_DIR/backups"
        mkdir -p "$backup_dir"
        local backup_file="$backup_dir/settings.json.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$CLAUDE_CONFIG_FILE" "$backup_file"
        log "Created backup: $backup_file"
    fi
}

# Function to check if jq is installed
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed"
        echo "Install jq:"
        echo "  macOS:    brew install jq"
        echo "  Ubuntu:   sudo apt-get install jq"
        echo "  Fedora:   sudo dnf install jq"
        exit 1
    fi
}

# Function to get available hooks
get_available_hooks() {
    local hooks=()
    if [ -d "$HOOKS_DIR" ]; then
        for hook_dir in "$HOOKS_DIR"/*; do
            if [ -d "$hook_dir" ] && [ -f "$hook_dir/config.json" ]; then
                # Check for either hook.py or hook.sh
                if [ -f "$hook_dir/hook.py" ] || [ -f "$hook_dir/hook.sh" ]; then
                    hooks+=("$(basename "$hook_dir")")
                fi
            fi
        done
    fi
    printf '%s\n' "${hooks[@]}"
}

# Function to get hook info
get_hook_info() {
    local hook_name="$1"
    local config_file="$HOOKS_DIR/$hook_name/config.json"
    
    if [ -f "$config_file" ]; then
        jq -r '.description // "No description available"' "$config_file"
    else
        echo "No description available"
    fi
}

# Function to install a specific hook
install_hook() {
    local hook_name="$1"
    local hook_dir="$HOOKS_DIR/$hook_name"
    local hook_config="$hook_dir/config.json"
    local deps_script="$hook_dir/deps.sh"
    
    # Find the hook script (either .py or .sh)
    local hook_script=""
    if [ -f "$hook_dir/hook.sh" ]; then
        hook_script="$hook_dir/hook.sh"
    else
        error "Hook '$hook_name' not found or incomplete (hook.sh)"
        return 1
    fi
    
    if [ ! -f "$hook_config" ]; then
        error "Hook '$hook_name' missing config.json"
        return 1
    fi
    
    # Check dependencies if deps.sh exists
    if [ -f "$deps_script" ]; then
        log "Checking dependencies for $hook_name..."
        if ! bash "$deps_script"; then
            error "Dependencies not met for $hook_name"
            return 1
        fi
        echo ""
    fi
    
    # Create claude directory if it doesn't exist
    mkdir -p "$CLAUDE_DIR"
    
    # Initialize settings.json if it doesn't exist
    if [ ! -f "$CLAUDE_CONFIG_FILE" ]; then
        echo '{"hooks": {}}' > "$CLAUDE_CONFIG_FILE"
        log "Created new settings.json"
    fi
    
    # Backup current settings
    backup_settings
    
    # Copy hook script to user's hooks directory
    mkdir -p "$USER_HOOKS_DIR"
    
    # Preserve the original extension
    local hook_ext="${hook_script##*.}"
    local installed_hook_path="$USER_HOOKS_DIR/${hook_name}.${hook_ext}"
    cp "$hook_script" "$installed_hook_path"
    chmod +x "$installed_hook_path"
    
    # Read hook configuration
    local hook_type=$(jq -r '.hook_type // "PostToolUse"' "$hook_config")
    local matcher=$(jq -r '.matcher // ""' "$hook_config")
    
    # Update settings.json with the hook configuration
    local temp_file=$(mktemp)
    
    # Create the hook configuration
    jq --arg hook_type "$hook_type" \
       --arg matcher "$matcher" \
       --arg command "$installed_hook_path" \
       --arg hook_name "$hook_name" \
       '
       # Ensure hooks object exists
       .hooks = (.hooks // {}) |
       
       # Ensure hook type array exists
       .hooks[$hook_type] = (.hooks[$hook_type] // []) |
       
       # Remove any existing entry for this hook
       .hooks[$hook_type] = [.hooks[$hook_type][] | select(.hooks[0].command | contains($hook_name) | not)] |
       
       # Add the new hook configuration
       .hooks[$hook_type] += [{
         "matcher": $matcher,
         "hooks": [{
           "type": "command",
           "command": $command
         }]
       }]
       ' "$CLAUDE_CONFIG_FILE" > "$temp_file"
    
    mv "$temp_file" "$CLAUDE_CONFIG_FILE"
    
    success "Installed hook: $hook_name"
    info "Hook location: $installed_hook_path"
}

# Function to uninstall a hook
uninstall_hook() {
    local hook_name="$1"
    
    # Find the installed hook (either .py or .sh)
    local installed_hook_path=""
    if [ -f "$USER_HOOKS_DIR/${hook_name}.py" ]; then
        installed_hook_path="$USER_HOOKS_DIR/${hook_name}.py"
    elif [ -f "$USER_HOOKS_DIR/${hook_name}.sh" ]; then
        installed_hook_path="$USER_HOOKS_DIR/${hook_name}.sh"
    fi
    
    if [ ! -f "$CLAUDE_CONFIG_FILE" ]; then
        warn "No settings.json found"
        return 0
    fi
    
    # Backup current settings
    backup_settings
    
    # Remove hook from settings.json
    local temp_file=$(mktemp)
    jq --arg hook_name "$hook_name" '
    .hooks |= with_entries(
        .value |= map(select(.hooks[0].command | contains($hook_name) | not))
    ) |
    # Remove empty hook type arrays
    .hooks |= with_entries(select(.value | length > 0))
    ' "$CLAUDE_CONFIG_FILE" > "$temp_file"
    
    mv "$temp_file" "$CLAUDE_CONFIG_FILE"
    
    # Remove hook script
    if [ -f "$installed_hook_path" ]; then
        rm "$installed_hook_path"
        log "Removed hook script: $installed_hook_path"
    fi
    
    success "Uninstalled hook: $hook_name"
}

# Function to uninstall all hooks
uninstall_all_hooks() {
    if [ ! -f "$CLAUDE_CONFIG_FILE" ]; then
        warn "No settings.json found"
        return 0
    fi
    
    log "Uninstalling all hooks..."
    echo ""
    
    # Get list of installed hooks
    local installed_hooks=$(jq -r '
    .hooks | to_entries[] | 
    .value[] | 
    .hooks[0].command | 
    select(contains("/ethpandaops/")) |
    split("/")[-1] | 
    sub("\\.(py|sh)$"; "")
    ' "$CLAUDE_CONFIG_FILE" 2>/dev/null | sort -u)
    
    if [ -z "$installed_hooks" ]; then
        warn "No hooks to uninstall"
        return 0
    fi
    
    # Uninstall each hook
    while IFS= read -r hook; do
        log "Uninstalling $hook..."
        uninstall_hook "$hook"
        echo ""
    done <<< "$installed_hooks"
    
    # Clean up hooks directory if empty
    if [ -d "$USER_HOOKS_DIR" ]; then
        rmdir "$USER_HOOKS_DIR" 2>/dev/null || true
    fi
    
    success "All hooks uninstalled"
}

# Function to list installed hooks
list_installed_hooks() {
    if [ ! -f "$CLAUDE_CONFIG_FILE" ]; then
        warn "No hooks installed (settings.json not found)"
        return 0
    fi
    
    local installed_hooks=$(jq -r '
    .hooks | to_entries[] | 
    .value[] | 
    .hooks[0].command | 
    split("/")[-1] | 
    sub("\\.(py|sh)$"; "")
    ' "$CLAUDE_CONFIG_FILE" 2>/dev/null | sort -u)
    
    if [ -z "$installed_hooks" ]; then
        warn "No hooks installed"
    else
        echo "Installed hooks:"
        echo "$installed_hooks" | while read -r hook; do
            echo "  ✓ $hook"
        done
    fi
}

# Interactive installer
interactive_install() {
    local available_hooks=($(get_available_hooks))
    
    if [ ${#available_hooks[@]} -eq 0 ]; then
        error "No hooks available to install"
        return 1
    fi
    
    echo "Available hooks:"
    echo ""
    
    local i=1
    for hook in "${available_hooks[@]}"; do
        local desc=$(get_hook_info "$hook")
        local hook_dir="$HOOKS_DIR/$hook"
        echo "  $i) $hook"
        echo "     $desc"
        # Add clickable link to inspect hook
        if [ -f "$hook_dir/hook.py" ]; then
            echo "     Inspect: file://$hook_dir/hook.py (Cmd+click)"
        elif [ -f "$hook_dir/hook.sh" ]; then
            echo "     Inspect: file://$hook_dir/hook.sh (Cmd+click)"
        fi
        echo ""
        ((i++))
    done
    
    echo "  q) Quit"
    echo ""
    
    while true; do
        read -p "Select hook to install (1-${#available_hooks[@]} or q): " choice
        
        if [[ "$choice" == "q" ]]; then
            echo "Installation cancelled"
            return 0
        fi
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#available_hooks[@]} ]; then
            local selected_hook="${available_hooks[$((choice-1))]}"
            install_hook "$selected_hook"
            
            echo ""
            read -p "Install another hook? (y/n): " another
            if [[ ! "$another" =~ ^[Yy] ]]; then
                break
            fi
            
            echo ""
            echo "Available hooks:"
            i=1
            for hook in "${available_hooks[@]}"; do
                local desc=$(get_hook_info "$hook")
                local hook_dir="$HOOKS_DIR/$hook"
                echo "  $i) $hook"
                echo "     $desc"
                # Add clickable link to inspect hook
                if [ -f "$hook_dir/hook.py" ]; then
                    echo "     Inspect: file://$hook_dir/hook.py (Cmd+click)"
                elif [ -f "$hook_dir/hook.sh" ]; then
                    echo "     Inspect: file://$hook_dir/hook.sh (Cmd+click)"
                fi
                echo ""
                ((i++))
            done
            echo "  q) Quit"
            echo ""
        else
            error "Invalid selection"
        fi
    done
}

# Function to install all hooks
install_all_hooks() {
    local available_hooks=($(get_available_hooks))
    
    if [ ${#available_hooks[@]} -eq 0 ]; then
        error "No hooks available to install"
        return 1
    fi
    
    log "Installing all available hooks..."
    echo ""
    
    for hook in "${available_hooks[@]}"; do
        log "Installing $hook..."
        install_hook "$hook"
        echo ""
    done
    
    success "All hooks installed successfully"
}

# Function to show hook details
show_hook_details() {
    local hook_name="$1"
    local hook_dir="$HOOKS_DIR/$hook_name"
    local hook_config="$hook_dir/config.json"
    
    if [ ! -f "$hook_config" ]; then
        error "Hook '$hook_name' not found"
        return 1
    fi
    
    echo "Hook: $hook_name"
    echo "=================="
    echo ""
    
    local desc=$(jq -r '.description // "No description"' "$hook_config")
    local hook_type=$(jq -r '.hook_type // "PostToolUse"' "$hook_config")
    local matcher=$(jq -r '.matcher // "No matcher"' "$hook_config")
    
    echo "Description: $desc"
    echo "Hook Type:   $hook_type"
    echo "Matcher:     $matcher"
    
    # Show the actual script file with clickable link
    if [ -f "$hook_dir/hook.py" ]; then
        echo "Script:      file://$hook_dir/hook.py"
        echo "             (Cmd+click to inspect)"
    elif [ -f "$hook_dir/hook.sh" ]; then
        echo "Script:      file://$hook_dir/hook.sh"
        echo "             (Cmd+click to inspect)"
    fi
    
    # Check dependencies if deps.sh exists
    if [ -f "$hook_dir/deps.sh" ]; then
        echo ""
        echo "Dependencies:"
        if bash "$hook_dir/deps.sh" &>/dev/null; then
            success "All dependencies met"
        else
            warn "Missing dependencies (run deps.sh for details)"
            echo "Check deps: file://$hook_dir/deps.sh"
        fi
    fi
    
    # Check if installed
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        local is_installed=$(jq --arg hook_name "$hook_name" '
        .hooks | to_entries[] | 
        .value[] | 
        select(.hooks[0].command | contains($hook_name))
        ' "$CLAUDE_CONFIG_FILE" 2>/dev/null)
        
        if [ -n "$is_installed" ]; then
            echo ""
            success "Status: Installed"
        else
            echo ""
            warn "Status: Not installed"
        fi
    fi
}

# Main execution
main() {
    local install=false
    local all=false
    local list=false
    local uninstall=false
    local show=false
    local hook_name=""
    echo "================================================"  
    echo "🐼 ethPandaOps Claude Code"
    echo ""
    echo " 🪝 Hooks Installer 🪝"
    echo "================================================"
    echo ""
    info "Hooks location: ~/.claude/hooks/ethpandaops/"
    info "Settings file: ~/.claude/settings.json"
    echo ""
    echo "WARNING: Hooks are dangerous. Inspect the hook before installing. Please be careful. Install at your own risk. "
    echo ""
    
    check_dependencies
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--install)
                install=true
                if [[ $# -gt 1 && ! "$2" =~ ^- ]]; then
                    hook_name="$2"
                    shift
                fi
                shift
                ;;
            -a|--all)
                all=true
                shift
                ;;
            -l|--list)
                list=true
                shift
                ;;
            -u|--uninstall)
                uninstall=true
                if [[ $# -gt 1 && ! "$2" =~ ^- ]]; then
                    hook_name="$2"
                    shift
                fi
                shift
                ;;
            -s|--show)
                show=true
                if [[ $# -gt 1 && ! "$2" =~ ^- ]]; then
                    hook_name="$2"
                    shift
                fi
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -i, --install [hook]   Install a specific hook or run interactive installer"
                echo "  -a, --all              Install all available hooks"
                echo "  -l, --list             List installed hooks"
                echo "  -u, --uninstall [hook] Uninstall a specific hook (use 'all' to uninstall all)"
                echo "  -s, --show [hook]      Show details about a specific hook"
                echo "  -h, --help             Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                     # Interactive installer"
                echo "  $0 --all               # Install all hooks"
                echo "  $0 --install gofmt     # Install specific hook"
                echo "  $0 --list              # List installed hooks"
                echo "  $0 --uninstall gofmt   # Uninstall specific hook"
                echo "  $0 --uninstall all     # Uninstall all hooks"
                echo "  $0 --show gofmt        # Show hook details"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Execute based on options
    if [ "$list" = true ]; then
        list_installed_hooks
    elif [ "$show" = true ]; then
        if [ -z "$hook_name" ]; then
            error "Please specify a hook name"
            echo "Available hooks: $(get_available_hooks | tr '\n' ' ')"
            exit 1
        fi
        show_hook_details "$hook_name"
    elif [ "$uninstall" = true ]; then
        if [ -z "$hook_name" ]; then
            error "Please specify a hook to uninstall or use '--uninstall all'"
            list_installed_hooks
            exit 1
        elif [ "$hook_name" = "all" ]; then
            uninstall_all_hooks
        else
            uninstall_hook "$hook_name"
        fi
    elif [ "$all" = true ]; then
        install_all_hooks
    elif [ "$install" = true ]; then
        if [ -n "$hook_name" ]; then
            install_hook "$hook_name"
        else
            interactive_install
        fi
    else
        # Default: interactive install
        interactive_install
    fi
}

# Check if script is being executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi