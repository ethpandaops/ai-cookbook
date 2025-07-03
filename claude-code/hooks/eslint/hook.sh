#!/bin/bash

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

# Check if we found a file path and it's a JavaScript/TypeScript file
if [ -z "$file_path" ] || [[ ! "$file_path" =~ \.(js|jsx|ts|tsx|mjs|cjs)$ ]]; then
    exit 0
fi

# Check if the file exists
if [ ! -f "$file_path" ]; then
    echo "File not found: $file_path" >&2
    exit 0
fi

# Get the current working directory
CWD=$(pwd)

# Function to find npm prefix from a given directory
find_npm_prefix() {
    local dir="$1"
    (cd "$dir" && npm prefix 2>/dev/null)
}

# Function to check if eslint is a dependency in package.json
has_eslint_dep() {
    local pkg_json="$1"
    if [ -f "$pkg_json" ]; then
        jq -e '.dependencies.eslint or .devDependencies.eslint' "$pkg_json" >/dev/null 2>&1
        return $?
    fi
    return 1
}

# Function to find all package.json files from a directory up to CWD
find_all_package_jsons() {
    local dir="$1"
    local cwd="$2"
    local found_eslint=false
    local eslint_prefix=""
    
    # Start from the file's directory and walk up to CWD
    current_dir="$dir"
    while [[ "$current_dir" == "$cwd"* ]] || [[ "$current_dir" == "$cwd" ]]; do
        if [ -f "$current_dir/package.json" ]; then
            echo "Found package.json at: $current_dir" >&2
            if has_eslint_dep "$current_dir/package.json"; then
                echo "  ✓ Has eslint dependency" >&2
                found_eslint=true
                eslint_prefix="$current_dir"
                break
            else
                echo "  ✗ No eslint dependency" >&2
            fi
        fi
        
        # Move up one directory
        parent_dir=$(dirname "$current_dir")
        if [ "$parent_dir" = "$current_dir" ]; then
            # Reached root
            break
        fi
        current_dir="$parent_dir"
    done
    
    if $found_eslint; then
        echo "$eslint_prefix"
        return 0
    fi
    return 1
}

# Find the npm prefix from the file's directory
file_dir=$(dirname "$file_path")
file_npm_prefix=$(find_npm_prefix "$file_dir")

# Check if we found a valid npm prefix and it's within CWD
if [ -z "$file_npm_prefix" ]; then
    echo "No package.json found for $file_path" >&2
    exit 0
fi

# Ensure the npm prefix is within or equal to CWD
if [[ ! "$file_npm_prefix" == "$CWD"* ]]; then
    echo "Package.json found at $file_npm_prefix is outside working directory $CWD" >&2
    exit 0
fi

# Find the first package.json with eslint dependency in the hierarchy
eslint_package_dir=$(find_all_package_jsons "$file_dir" "$CWD")

if [ -z "$eslint_package_dir" ]; then
    echo "No package.json with eslint dependency found in hierarchy within $CWD" >&2
    exit 0
fi

# Function to find the nearest eslint config from a directory
find_nearest_eslint_config() {
    local dir="$1"
    local eslint_root="$2"
    
    # Start from the file's directory and walk up to the eslint package directory
    current_dir="$dir"
    while [[ "$current_dir" == "$eslint_root"* ]] || [[ "$current_dir" == "$eslint_root" ]]; do
        # Check for ESLint v9 configs
        for config in "eslint.config.js" "eslint.config.mjs" "eslint.config.cjs"; do
            if [ -f "$current_dir/$config" ]; then
                echo "$current_dir"
                return 0
            fi
        done
        
        # Check for legacy configs
        for config in ".eslintrc.js" ".eslintrc.cjs" ".eslintrc.json" ".eslintrc.yml" ".eslintrc.yaml" ".eslintrc"; do
            if [ -f "$current_dir/$config" ]; then
                echo "$current_dir"
                return 0
            fi
        done
        
        # Move up one directory
        parent_dir=$(dirname "$current_dir")
        if [ "$parent_dir" = "$current_dir" ]; then
            break
        fi
        current_dir="$parent_dir"
    done
    
    return 1
}

# Run eslint from the correct npm prefix
if command -v npx &> /dev/null; then
    # Find the nearest eslint config from the file's directory
    config_dir=$(find_nearest_eslint_config "$file_dir" "$eslint_package_dir")
    
    if [ -z "$config_dir" ]; then
        echo "No eslint config found between $file_dir and $eslint_package_dir" >&2
        exit 1
    fi
    
    echo "Found eslint config in: $config_dir" >&2
    
    # Build the eslint command - npx will handle package manager resolution
    eslint_cmd="npx eslint --fix \"$file_path\""
    
    echo "Running eslint command from $config_dir:" >&2
    echo "  $eslint_cmd" >&2
    
    # Change to the config directory to ensure correct eslint resolution
    (cd "$config_dir" && eval "$eslint_cmd")
    eslint_exit_code=$?
    
    if [ $eslint_exit_code -eq 0 ]; then
        echo "Successfully formatted $file_path with eslint from $config_dir"
    else
        echo "eslint failed for $file_path (exit code: $eslint_exit_code)" >&2
        exit 1
    fi
else
    echo "Error: npx not found. Please ensure npx is installed and available via npx" >&2
    exit 1
fi
