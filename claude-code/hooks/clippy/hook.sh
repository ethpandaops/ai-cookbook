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

# Check for clippy configuration file
has_clippy_config() {
    local dir="$1"
    [ -f "$dir/.clippy.toml" ] || [ -f "$dir/clippy.toml" ]
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

# Check if we found a file path and it's a .rs file
if [ -z "$file_path" ] || [[ ! "$file_path" =~ \.rs$ ]]; then
    exit 0
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
file_basename=$(basename "$file_path")

# Run clippy on the project
cd "$cargo_dir"

# Build clippy command
clippy_cmd="cargo clippy --message-format=short"

# Check if we should use strict mode
strict_mode=false
if has_clippy_config "$cargo_dir"; then
    # If there's a clippy config, assume the project wants strict checking
    clippy_cmd="$clippy_cmd -- -D warnings"
    strict_mode=true
fi

# Run clippy and capture output
set +e  # Don't exit on command failure
output=$($clippy_cmd 2>&1)
exit_code=$?
set -e  # Re-enable exit on error

if [[ $exit_code -eq 0 ]]; then
    # Success: no issues found, exit silently
    exit 0
elif [[ $exit_code -eq 101 ]]; then
    # Issues found (warnings treated as errors in strict mode, or actual errors)

    # Try to filter output to only show issues related to our file
    if [[ -n "$file_basename" ]]; then
        # Filter for issues mentioning our file
        filtered_output=$(echo "$output" | grep -E "(^(warning|error):|$file_basename|^\s+-->.*$file_basename)" || true)

        # If we have filtered output, use it
        if [[ -n "$filtered_output" ]]; then
            # Count issues in filtered output
            warning_count=$(echo "$filtered_output" | grep -c "^warning:" || true)
            error_count=$(echo "$filtered_output" | grep -c "^error:" || true)
        else
            # No issues in our file, exit silently
            exit 0
        fi
    else
        # Count all issues
        warning_count=$(echo "$output" | grep -c "^warning:" || true)
        error_count=$(echo "$output" | grep -c "^error:" || true)
        filtered_output="$output"
    fi

    total_issues=$((warning_count + error_count))

    if [[ $total_issues -eq 0 ]]; then
        # No warnings or errors found, but exit code was 101 - likely a clippy internal error
        echo "Clippy encountered an issue but reported no warnings or errors" >&2
        echo "$output" >&2
        exit 0
    fi

    # Prepare the message
    if [[ $error_count -gt 0 ]]; then
        issue_summary="$error_count error(s)"
        if [[ $warning_count -gt 0 ]]; then
            issue_summary="$issue_summary and $warning_count warning(s)"
        fi
    else
        issue_summary="$warning_count warning(s)"
    fi

    # Limit output if too long
    line_count=$(echo "$filtered_output" | wc -l | tr -d ' ')
    if [[ $line_count -gt 25 ]]; then
        limited_output=$(echo "$filtered_output" | head -n 20)
        display_output="$limited_output
... (output truncated, showing first 20 lines)

To see all issues, run: cd \"$cargo_dir\" && $clippy_cmd"
    else
        display_output="$filtered_output"
    fi

    if [[ "$strict_mode" == "true" ]] || [[ $error_count -gt 0 ]]; then
        # Block Claude in strict mode or if there are errors
        stop_reason="clippy found $issue_summary"

        if [[ "$strict_mode" == "true" ]]; then
            reason="clippy found $issue_summary in strict mode (clippy.toml detected). Review and fix these issues before continuing.

$display_output"
        else
            reason="clippy found $issue_summary. Fix these errors before continuing.

$display_output"
        fi

        # Output JSON to block Claude
        jq -n --arg decision "block" --arg reason "$reason" --arg stopReason "$stop_reason" '{decision: $decision, reason: $reason, stopReason: $stopReason}'
        exit 0
    else
        # Just warnings in non-strict mode - show to user but don't block
        echo "clippy found $issue_summary in $relative_file:" >&2
        echo "$display_output" >&2
        exit 0
    fi
else
    # Other error codes - show to user but don't block
    echo "clippy failed with unexpected exit code $exit_code" >&2
    if [[ -n "$output" ]]; then
        echo "$output" >&2
    fi
    exit 0
fi