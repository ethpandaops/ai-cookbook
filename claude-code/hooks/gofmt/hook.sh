#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract file path from tool input (Write and Edit both use file_path)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

# Check if we found a file path and it's a .go file
if [ -z "$file_path" ] || [[ ! "$file_path" =~ \.go$ ]]; then
    exit 0
fi

# Check if the file exists
if [ ! -f "$file_path" ]; then
    echo "File not found: $file_path" >&2
    exit 0
fi

# Run gofmt on the file
if command -v gofmt &> /dev/null; then
    if gofmt -w "$file_path"; then
        echo "Successfully formatted $file_path with gofmt"
    else
        echo "gofmt failed for $file_path" >&2
        exit 1
    fi
else
    echo "Error: gofmt not found. Please ensure Go is installed and gofmt is in your PATH" >&2
    exit 1
fi