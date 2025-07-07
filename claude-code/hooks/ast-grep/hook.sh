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
            
            # Extract file patterns from the command - simplified approach
            extract_file_patterns() {
                local cmd="$1"
                local patterns=""
                
                # Look for --include= patterns first
                if echo "$cmd" | grep -q -- '--include='; then
                    patterns=$(echo "$cmd" | grep -oE -- '--include="?[^"[:space:]]+"?' | sed 's/--include=//')
                    # Remove quotes if present
                    patterns=$(echo "$patterns" | tr -d '"' | tr -d "'")
                else
                    # Remove grep command and common flags
                    local cleaned=$(echo "$cmd" | sed -E 's/^[^[:space:]]*grep[[:space:]]+//')
                    # Remove flags like -r, -n, -i, -e pattern, etc.
                    cleaned=$(echo "$cleaned" | sed -E 's/-[rinlvH]+[[:space:]]+//g')
                    cleaned=$(echo "$cleaned" | sed -E 's/-e[[:space:]]+("[^"]*"|'"'"'[^'"'"']*'"'"'|[^[:space:]]+)[[:space:]]*//g')
                    
                    # Remove the search pattern (first non-flag argument that doesn't look like a file)
                    # This handles: "pattern" or 'pattern' or pattern (without extension)
                    cleaned=$(echo "$cleaned" | sed -E 's/^("[^"]*"|'"'"'[^'"'"']*'"'"'|[^[:space:]]+\.[^[:space:]]+|[^[:space:]]+)[[:space:]]+//')
                    
                    # Now extract file patterns from what remains
                    # Match files with extensions, including globs and paths
                    patterns=$(echo "$cleaned" | grep -oE '[^[:space:]]+\.[a-zA-Z0-9\{\},*]+|"[^"]+"|'"'"'[^'"'"']+'"'"'' | \
                        while read -r pattern; do
                            # Remove quotes and check if it has an extension
                            local unquoted=$(echo "$pattern" | tr -d '"' | tr -d "'")
                            if echo "$unquoted" | grep -qE '\.[a-zA-Z0-9\{\},*]+$'; then
                                echo "$unquoted"
                            fi
                        done)
                fi
                
                echo "$patterns"
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
code_extensions=$(jq -r '.supported_extensions | to_entries[] | .value[]' "$extensions_file" 2>/dev/null)

# Check if the include pattern contains any code file extension
is_code_file=false

# For unknown files, check if the original command mentions code files
if [ "$include_pattern" = "unknown_files" ]; then
    # Check if the command contains any code file extensions
    for ext in $code_extensions; do
        # Check if the command contains this extension
        if [[ "$command" == *".$ext"* ]]; then
            is_code_file=true
            break
        fi
    done
else
    # Check against the list of extensions for extracted patterns
    # This now handles brace expansion like *.{ts,tsx} and complex patterns
    for ext in $code_extensions; do
        # Check if include pattern contains this extension
        # This works for: *.js, **/*.js, src/*.js, *.{js,jsx}, etc.
        if [[ "$include_pattern" == *"$ext"* ]]; then
            is_code_file=true
            break
        fi
    done
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
        # Debug: show what we're working with
        # Extract extension from pattern - look for any known extension
        # Match the extension at the end of the pattern or before glob markers
        # Sort extensions by length (longest first) to avoid false matches
        sorted_extensions=$(echo "$code_extensions" | tr ' ' '\n' | awk '{ print length, $0 }' | sort -rn | cut -d' ' -f2-)
        for ext in $sorted_extensions; do
            # Check for exact extension match at word boundaries
            # Handle patterns like *.ext, path/file.ext, *.{ext,other}, etc.
            # Make sure we match .ext not just any occurrence of ext
            # Use grep for more reliable pattern matching
            # Handle both .ext and {ext in brace expansions
            # For .c, we need to ensure it's not .c++ or .cpp etc
            # Escape special regex characters in extension
            escaped_ext=$(echo "$ext" | sed 's/[+]/\\&/g')
            if echo "$include_pattern" | grep -qE "(\\.|\\{)${escaped_ext}([^a-zA-Z0-9+]|,|\\}|$)"; then
                detected_file_type=".$ext"
                break
            fi
        done
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
