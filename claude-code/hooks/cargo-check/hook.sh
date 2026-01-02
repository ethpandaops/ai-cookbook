#!/bin/bash
set -e

# Check if we're in a git repository
is_git_repo() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# Get the modified file path relative to git root
get_git_relative_path() {
    local file_path="$1"
    if is_git_repo; then
        git_root=$(git rev-parse --show-toplevel)
        realpath --relative-to="$git_root" "$file_path" 2>/dev/null || echo "$file_path"
    else
        echo "$file_path"
    fi
}

# Read JSON input from stdin
input=$(cat)

# Extract tool information
tool_name=$(echo "$input" | jq -r '.tool_name // ""')
tool_input=$(echo "$input" | jq -r '.tool_input // {}')

# Check if this is a file editing tool
case "$tool_name" in
    Write|Edit|MultiEdit|str_replace_editor|str_replace_based_edit_tool)
        ;;
    *)
        exit 0
        ;;
esac

# Extract file path based on tool type
file_path=""

case "$tool_name" in
    Write|Edit|MultiEdit)
        file_path=$(echo "$tool_input" | jq -r '.file_path // ""')
        ;;
    str_replace_editor)
        # Parse command field for path
        command=$(echo "$tool_input" | jq -r '.command // ""')
        if [[ "$command" =~ path=([^ ]+) ]]; then
            file_path="${BASH_REMATCH[1]}"
        fi
        ;;
    str_replace_based_edit_tool)
        file_path=$(echo "$tool_input" | jq -r '.path // ""')
        ;;
esac

# Check if we found a file path and it's a Rust file (.rs or Cargo.toml)
if [ -z "$file_path" ]; then
    exit 0
fi

if [[ ! "$file_path" =~ \.(rs|toml)$ ]]; then
    exit 0
fi

# For .toml files, only process if it's Cargo.toml
if [[ "$file_path" =~ \.toml$ ]]; then
    basename=$(basename "$file_path")
    if [ "$basename" != "Cargo.toml" ]; then
        exit 0
    fi
fi

# Check if the file exists
if [ ! -f "$file_path" ]; then
    echo "File not found: $file_path" >&2
    exit 0
fi

# Find the nearest Cargo.toml
dir=$(dirname "$file_path")
cargo_dir=""
while [ "$dir" != "/" ]; do
    if [ -f "$dir/Cargo.toml" ]; then
        cargo_dir="$dir"
        break
    fi
    dir=$(dirname "$dir")
done

if [ -z "$cargo_dir" ]; then
    # No Cargo.toml found, exit silently
    exit 0
fi

# Get relative path for better output
relative_file=$(get_git_relative_path "$file_path")

# Run cargo check on the project
cd "$cargo_dir"

# Run cargo check and capture output
set +e  # Don't exit on command failure
output=$(cargo check --message-format=short 2>&1)
exit_code=$?
set -e  # Re-enable exit on error

if [[ $exit_code -eq 0 ]]; then
    # Success: no errors found, exit silently
    exit 0
elif [[ $exit_code -eq 101 ]]; then
    # Compilation errors found

    # Try to filter output to only show errors related to our file
    if [[ -n "$relative_file" ]]; then
        # Filter for errors mentioning our file
        filtered_output=$(echo "$output" | grep -E "(^error|^$relative_file|^\s+-->.*$relative_file)" || true)
        if [[ -n "$filtered_output" ]]; then
            output="$filtered_output"
        fi
    fi

    # Count errors
    error_count=$(echo "$output" | grep -c "^error" || true)

    if [[ $error_count -eq 0 ]]; then
        # Sometimes exit code 101 without explicit errors means dependency issues
        stop_reason="cargo check failed (likely dependency or configuration issue)"
        reason="cargo check failed in $cargo_dir. This may be due to dependency issues or configuration problems.

$output

To investigate further, run: cd \"$cargo_dir\" && cargo check"
    else
        stop_reason="cargo check found $error_count compilation error(s)"

        # Limit output if too many errors
        line_count=$(echo "$output" | wc -l | tr -d ' ')
        if [[ $line_count -gt 30 ]]; then
            limited_output=$(echo "$output" | head -n 25)
            reason="cargo check found $error_count compilation error(s) in the project. Fix these errors before continuing.

$limited_output
... (output truncated, showing first 25 lines)

To see all errors, run: cd \"$cargo_dir\" && cargo check"
        else
            reason="cargo check found $error_count compilation error(s). Fix these errors before continuing.

$output"
        fi
    fi

    # Output JSON to block Claude
    jq -n --arg decision "block" --arg reason "$reason" --arg stopReason "$stop_reason" '{decision: $decision, reason: $reason, stopReason: $stopReason}'
    exit 0
else
    # Other error codes - show to user but don't block
    echo "cargo check failed with unexpected exit code $exit_code" >&2
    if [[ -n "$output" ]]; then
        echo "$output" >&2
    fi
    exit 1
fi