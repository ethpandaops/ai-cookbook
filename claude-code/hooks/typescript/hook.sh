#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract file path from tool input (Write and Edit both use file_path)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

# Check if we found a file path and it's a TypeScript file
if [ -z "$file_path" ] || [[ ! "$file_path" =~ \.(ts|tsx)$ ]]; then
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

# Function to check if typescript is a dependency in package.json
has_typescript_dep() {
    local pkg_json="$1"
    if [ -f "$pkg_json" ]; then
        jq -e '.dependencies.typescript or .devDependencies.typescript' "$pkg_json" >/dev/null 2>&1
        return $?
    fi
    return 1
}

# Function to find all package.json files from a directory up to CWD
find_all_package_jsons() {
    local dir="$1"
    local cwd="$2"
    local found_typescript=false
    local typescript_prefix=""
    
    # Start from the file's directory and walk up to CWD
    current_dir="$dir"
    while [[ "$current_dir" == "$cwd"* ]] || [[ "$current_dir" == "$cwd" ]]; do
        if [ -f "$current_dir/package.json" ]; then
            echo "Found package.json at: $current_dir" >&2
            if has_typescript_dep "$current_dir/package.json"; then
                echo "  ✓ Has typescript dependency" >&2
                found_typescript=true
                typescript_prefix="$current_dir"
                break
            else
                echo "  ✗ No typescript dependency" >&2
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
    
    if $found_typescript; then
        echo "$typescript_prefix"
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

# Find the first package.json with typescript dependency in the hierarchy
typescript_package_dir=$(find_all_package_jsons "$file_dir" "$CWD")

if [ -z "$typescript_package_dir" ]; then
    echo "No package.json with typescript dependency found in hierarchy within $CWD" >&2
    exit 0
fi

# Function to find the nearest tsconfig.json from a directory
find_nearest_tsconfig() {
    local dir="$1"
    local typescript_root="$2"
    
    # Start from the file's directory and walk up to the typescript package directory
    current_dir="$dir"
    while [[ "$current_dir" == "$typescript_root"* ]] || [[ "$current_dir" == "$typescript_root" ]]; do
        if [ -f "$current_dir/tsconfig.json" ]; then
            echo "$current_dir"
            return 0
        fi
        
        # Move up one directory
        parent_dir=$(dirname "$current_dir")
        if [ "$parent_dir" = "$current_dir" ]; then
            break
        fi
        current_dir="$parent_dir"
    done
    
    return 1
}

# Run tsc from the correct npm prefix
if command -v npx &> /dev/null; then
    # Find the nearest tsconfig.json from the file's directory
    config_dir=$(find_nearest_tsconfig "$file_dir" "$typescript_package_dir")
    
    if [ -z "$config_dir" ]; then
        stop_reason="no tsconfig.json found"
        reason="No tsconfig.json found between $file_dir and $typescript_package_dir. Ensure a tsconfig.json file exists in the project hierarchy."
        jq -n --arg decision "block" --arg reason "$reason" --arg stopReason "$stop_reason" '{decision: $decision, reason: $reason, stopReason: $stopReason}'
        exit 0
    fi
    
    echo "Found tsconfig.json in: $config_dir" >&2
    
    # Build the tsc command - npx will handle package manager resolution
    tsc_cmd="npx tsc --noEmit --pretty false ${file_path}"
    
    echo "Running tsc command from $config_dir:" >&2
    echo "  $tsc_cmd" >&2
    
    # Change to the config directory to ensure correct tsc resolution
    (cd "$config_dir" && eval "$tsc_cmd")
    tsc_exit_code=$?
    
    if [ $tsc_exit_code -eq 0 ]; then
        echo "Successfully type-checked project from $config_dir"
    else
        # Capture tsc output for error reporting
        tsc_output=$(cd "$config_dir" && eval "$tsc_cmd --pretty false" 2>&1) || true
        
        # Count TypeScript errors
        error_count=$(echo "$tsc_output" | grep -cE "^[^:]+\([0-9]+,[0-9]+\): error TS[0-9]+:" || true)
        
        if [ "$error_count" -gt 0 ]; then
            stop_reason="tsc found $error_count type errors"
            reason="TypeScript compiler found $error_count type errors. Review and fix these issues using a subtask if they're not expected, then continue with your original task.

$tsc_output"
        else
            stop_reason="tsc error (exit $tsc_exit_code)"
            reason="TypeScript compiler failed with exit code $tsc_exit_code. Review and fix this issue using a subtask if it's not expected, then continue with your original task.

$tsc_output"
        fi
        
        jq -n --arg decision "block" --arg reason "$reason" --arg stopReason "$stop_reason" '{decision: $decision, reason: $reason, stopReason: $stopReason}'
        exit 0
    fi
else
    stop_reason="npx not found"
    reason="Error: npx not found. Please ensure npx is installed and available via npx"
    jq -n --arg decision "block" --arg reason "$reason" --arg stopReason "$stop_reason" '{decision: $decision, reason: $reason, stopReason: $stopReason}'
    exit 0
fi