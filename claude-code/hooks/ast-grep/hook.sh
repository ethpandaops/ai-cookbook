#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Validate JSON input
if ! echo "$input" | jq empty 2>/dev/null; then
    echo "Error: Invalid JSON input" >&2
    exit 1
fi

# Extract tool information with validation
tool_name=$(echo "$input" | jq -r '.tool_name // ""')
tool_input=$(echo "$input" | jq -r '.tool_input // {}')

# Initialize variables
include_pattern=""
should_check=false

# Handle different tool types
case "$tool_name" in
    "Grep")
        # Direct Grep tool usage
        include_pattern=$(echo "$tool_input" | jq -r '.include // ""')
        if [ -n "$include_pattern" ]; then
            should_check=true
        fi
        ;;
    "Bash")
        # Check if the bash command contains grep (but not ripgrep/rg/ast-grep)
        command=$(echo "$tool_input" | jq -r '.command // ""')
        
        # Validate command input
        if [ -z "$command" ]; then
            exit 0
        fi
        
        # Check if this is a grep command (but not rg, ripgrep, or ast-grep)
        if echo "$command" | grep -qE "(^|[;&|])\s*grep\s+" && \
           ! echo "$command" | grep -qE "(ripgrep|rg|ast-grep)"; then
            
            # Extract file patterns from the command using enhanced pattern extraction
            # Function to extract multiple patterns and handle complex cases
            extract_file_patterns() {
                local cmd="$1"
                # Remove the grep command and its flags to focus on file patterns
                # Handle patterns like: *.js, "*.{ts,tsx}", 'src/**/*.py', etc.
                echo "$cmd" | sed -E 's/^[^[:space:]]*grep[[:space:]]+(-[[:space:]]*[a-zA-Z]*[[:space:]]*)*("[^"]*"|'"'"'[^'"'"']*'"'"'|[^[:space:]]+)[[:space:]]*//' | \
                    grep -oE '(["'"'"']?[^"'"'"'\s]*\*?\.[a-zA-Z0-9\{\},]+["'"'"']?|["'"'"'][^"'"'"']+["'"'"'])' | tr -d '"' | tr -d "'"
            }
            
            # Get all file patterns
            file_patterns=$(extract_file_patterns "$command")
            
            if [ -n "$file_patterns" ]; then
                # Use the first pattern for checking
                include_pattern=$(echo "$file_patterns" | head -1)
                should_check=true
            else
                # If no specific pattern found, check if any files are mentioned
                include_pattern="unknown_files"
                should_check=true
            fi
        fi
        ;;
    *)
        # Not a tool we care about
        exit 0
        ;;
esac

# If we shouldn't check, exit
if [ "$should_check" = false ]; then
    exit 0
fi

# Load extensions from config
extensions_file="$(dirname "$0")/extensions.json"
code_extensions=$(jq -r '.supported_extensions | to_entries[] | .value[]' "$extensions_file" 2>/dev/null | sed 's/^/./')

# Check if the include pattern contains any code file extension
is_code_file=false

# For unknown files, check if the original command mentions code files
if [ "$include_pattern" = "unknown_files" ]; then
    # Check if the command contains any code file extensions
    while IFS= read -r ext; do
        # Skip empty lines
        [ -z "$ext" ] && continue
        
        # Check if the command contains this extension
        if [[ "$command" == *"$ext"* ]]; then
            is_code_file=true
            break
        fi
    done <<< "$code_extensions"
else
    # Check against the list of extensions for extracted patterns
    while IFS= read -r ext; do
        # Skip empty lines
        [ -z "$ext" ] && continue
        
        # Check if include pattern ends with or contains this extension
        # Support patterns like *.js, **/*.js, src/*.js
        if [[ "$include_pattern" == *"$ext"* ]]; then
            is_code_file=true
            break
        fi
    done <<< "$code_extensions"
fi

# Function to suggest ast-grep patterns based on grep pattern and file type
suggest_ast_grep_pattern() {
    local grep_pattern="$1"
    local file_type="$2"
    local extensions_file="$(dirname "$0")/extensions.json"
    local patterns_file="$(dirname "$0")/patterns.json"
    
    # Try to extract the search pattern from the grep command
    local search_pattern=$(echo "$command" | sed -n 's/.*grep[[:space:]]\+\(-[[:space:]]*[a-zA-Z]*[[:space:]]*\)*"\?\([^"]*\)"\?.*/\2/p')
    
    # First, map extension to language code
    local lang_code=""
    if [ -f "$extensions_file" ]; then
        lang_code=$(jq -r --arg ext "${file_type#.}" '
            .supported_extensions | to_entries[] | 
            select(.value[] | . == $ext) | 
            .key
        ' "$extensions_file" 2>/dev/null | head -1)
    fi
    
    # If we couldn't find a language code, bail out
    if [ -z "$lang_code" ]; then
        echo "   Try: ast-grep --pattern 'your_pattern_here' --lang <language>" >&2
        echo "   Learn more: https://ast-grep.github.io/guide/pattern-syntax.html" >&2
        return
    fi
    
    # Load patterns from JSON file
    if [ -f "$patterns_file" ]; then
        # Use jq to get pattern suggestions based on language code and search pattern
        # First try pattern detection, then fall back to ALL general examples
        local lang_info=$(jq -r --arg lang "$lang_code" --arg pattern "$search_pattern" '
            .[$lang] |
            if . then
                if .pattern_detection then
                    # Try pattern detection first
                    ((.pattern_detection[] | 
                      select(.regex as $rx | $pattern | test($rx)) |
                      .suggestion + " --lang " + $lang + " # " + .description) 
                    // 
                    # Fall back to ALL general examples
                    (.general_examples[] | 
                     .pattern + " --lang " + $lang + " # " + .description))
                else
                    # Only general examples available - show ALL
                    .general_examples[] | 
                    .pattern + " --lang " + $lang + " # " + .description
                end
            else
                empty
            end
        ' "$patterns_file" 2>/dev/null)
        
        if [ -n "$lang_info" ]; then
            echo "   Pattern suggestions for $file_type:" >&2
            echo "$lang_info" | while IFS= read -r suggestion; do
                echo "   - $suggestion" >&2
            done
        else
            # Fallback to generic suggestion if no patterns found
            echo "   Try: ast-grep --pattern 'your_pattern_here' --lang $lang_code" >&2
        fi
    else
        # Fallback if patterns.json is missing
        echo "   Try: ast-grep --pattern 'your_pattern_here' --lang $lang_code" >&2
    fi
    
    echo "   Learn more: https://ast-grep.github.io/guide/pattern-syntax.html" >&2
}

# If searching in code files, provide gentle feedback
if [ "$is_code_file" = true ]; then
    echo "" >&2
    echo "💡 Note for future Claude: grep detected while searching in code files." >&2
    echo "   ast-grep is installed and understands code syntax better than text matching." >&2
    echo "   Consider using 'ast-grep --pattern ...' for more precise code searches in the future." >&2
    
    # Determine file type from include pattern if possible
    detected_file_type=""
    if [ "$include_pattern" != "unknown_files" ]; then
        # Extract extension from pattern
        detected_file_type=$(echo "$include_pattern" | grep -oE '\.[a-zA-Z0-9]+' | head -1)
    fi
    
    # Suggest patterns if we detected a file type
    if [ -n "$detected_file_type" ]; then
        suggest_ast_grep_pattern "$command" "$detected_file_type"
    fi
    
    echo "" >&2
    # Exit with code 2 so Claude sees the feedback (PostToolUse behavior)
    exit 2
fi

# No feedback needed - exit normally
exit 0
