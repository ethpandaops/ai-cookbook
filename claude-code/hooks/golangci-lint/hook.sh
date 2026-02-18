#!/bin/bash
set -e


# Find golangci-lint config file in current directory or parent directories
find_golangci_config() {
    local current_dir
    current_dir="$(pwd)"
    
    # Check current directory and walk up to root
    while [[ "$current_dir" != "/" ]]; do
        # Check for .golangci.yml
        if [[ -f "$current_dir/.golangci.yml" ]]; then
            echo "$current_dir/.golangci.yml"
            return 0
        fi
        
        # Check for .golangci.yaml
        if [[ -f "$current_dir/.golangci.yaml" ]]; then
            echo "$current_dir/.golangci.yaml"
            return 0
        fi
        
        # Move up one directory
        current_dir="$(dirname "$current_dir")"
    done
    
    # No config file found
    return 1
}

# Check if we're in a git repository
is_git_repo() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# Get the appropriate revision for --new-from-rev
get_base_revision() {
    if is_git_repo; then
        # Try to get HEAD~1, fallback to initial commit
        if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
            echo "HEAD~1"
        else
            # Repository has only one commit, use empty tree
            git hash-object -t tree /dev/null
        fi
    else
        # Not in a git repo, return empty (will skip --new-from-rev)
        echo ""
    fi
}

# Read JSON input from stdin
input=$(cat)

# Extract file path from tool input (Write and Edit both use file_path)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

# Only process Go files
if [[ ! "$file_path" =~ \.go$ ]]; then
    exit 0
fi

# Verify file exists
if [[ ! -f "$file_path" ]]; then
    echo "File not found: $file_path"
    exit 1
fi

# Get package directory
package_dir=$(dirname "$file_path")

# Change to package directory for analysis
cd "$package_dir"

# Check for golangci-lint configuration file
if ! find_golangci_config >/dev/null; then
    # Silent exit when no config file found
    exit 0
fi

# Build golangci-lint command with compact output
cmd="golangci-lint run"

# Add --new-from-rev if in git repo
base_rev=$(get_base_revision)
if [[ -n "$base_rev" ]]; then
    cmd="$cmd --new-from-rev=$base_rev"
fi

# Add compact output flags to minimize token usage
cmd="$cmd --output.tab.path=stdout"
cmd="$cmd --output.tab.print-linter-name=false"
cmd="$cmd --output.tab.colors=false"
cmd="$cmd --show-stats=false"
cmd="$cmd --max-issues-per-linter=20"
cmd="$cmd --max-same-issues=3"

# Add package path (current directory)
cmd="$cmd ./..."

# Run golangci-lint and capture output
set +e  # Don't exit on command failure
output=$($cmd 2>&1)
exit_code=$?
set -e  # Re-enable exit on error

if [[ $exit_code -eq 0 ]]; then
    # Success: no issues found, exit silently
    exit 0
elif [[ $exit_code -eq 1 ]]; then
    # Issues found: send JSON output to Claude with continue instruction
    issue_count=$(echo "$output" | wc -l | tr -d ' ')
    stop_reason="golangci-lint found $issue_count issues"
    
    # Limit output to last 5 errors to save context window
    if [[ $issue_count -gt 5 ]]; then
        limited_output=$(echo "$output" | tail -n 5)
        reason="golangci-lint found $issue_count linting issues (showing last 5). Review and fix these issues using a subtask if they're not expected, then continue with your original task.

$limited_output

To see all errors, run: (cd \"$package_dir\" && $cmd)"
    else
        reason="golangci-lint found $issue_count linting issues. Review and fix these issues using a subtask if they're not expected, then continue with your original task.

$output"
    fi
    
    jq -n --arg decision "block" --arg reason "$reason" --arg stopReason "$stop_reason" '{decision: $decision, reason: $reason, stopReason: $stopReason}'
    exit 0
elif [[ $exit_code -eq 3 ]]; then
    # Failure (syntax errors, etc.): show to user only, don't tell Claude
    echo "golangci-lint failed due to syntax errors or compilation issues:

$output" >&2
    exit 1
else
    # Other error (exit code 2, 4, 5, etc.): show to user only, don't tell Claude
    if [[ -n "$output" ]]; then
        echo "golangci-lint encountered an error (exit code $exit_code):

$output" >&2
    else
        echo "golangci-lint failed with exit code $exit_code but produced no output. This may be a configuration or tool issue." >&2
    fi
    exit 1
fi