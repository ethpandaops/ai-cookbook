#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract file path from tool input (Write and Edit both use file_path)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

# Check if we found a file path and it's a .rs file
if [ -z "$file_path" ] || [[ ! "$file_path" =~ \.rs$ ]]; then
    exit 0
fi

# Check if the file exists
if [ ! -f "$file_path" ]; then
    echo "File not found: $file_path" >&2
    exit 0
fi

# Run rustfmt on the file
if command -v rustfmt &> /dev/null; then
    if rustfmt "$file_path"; then
        echo "Successfully formatted $file_path with rustfmt"
    else
        echo "rustfmt failed for $file_path" >&2
        exit 1
    fi
else
    echo "Error: rustfmt not found. Please ensure Rust is installed and rustfmt is in your PATH" >&2
    exit 1
fi
