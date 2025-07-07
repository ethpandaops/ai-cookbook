#!/bin/bash

# Comprehensive test script for the ast-grep hook
HOOK_SCRIPT="$(dirname "$0")/hook.sh"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a hook test
run_test() {
    local test_name="$1"
    local input_json="$2"
    local expected_pattern="$3"
    local should_trigger="$4"  # true, false, or error
    
    echo -n "Testing: $test_name ... "
    
    # Run the hook and capture output and exit code
    local output
    output=$(echo "$input_json" | bash "$HOOK_SCRIPT" 2>&1)
    local exit_code=$?
    # Filter out grep usage errors as they're not relevant to our tests
    output=$(echo "$output" | grep -v "Usage: grep" | grep -v "Try 'grep --help'")
    
    # Check if the hook triggered (exit code 2) or errored (exit code 1)
    if [ "$should_trigger" = "error" ]; then
        # Expecting an error (exit code 1)
        if [ $exit_code -eq 1 ]; then
            echo -e "${GREEN}PASS${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}FAIL${NC} - Expected error exit code 1, got: $exit_code"
            echo "Output: $output"
            ((TESTS_FAILED++))
        fi
    elif [ "$should_trigger" = "true" ]; then
        if [ $exit_code -eq 2 ]; then
            # Check if expected pattern is in output (if provided)
            if [ -n "$expected_pattern" ]; then
                if echo "$output" | grep -qF "$expected_pattern"; then
                    echo -e "${GREEN}PASS${NC}"
                    ((TESTS_PASSED++))
                else
                    echo -e "${RED}FAIL${NC} - Expected pattern not found: $expected_pattern"
                    echo "Output: $output"
                    ((TESTS_FAILED++))
                fi
            else
                echo -e "${GREEN}PASS${NC}"
                ((TESTS_PASSED++))
            fi
        else
            echo -e "${RED}FAIL${NC} - Hook should have triggered (exit code: $exit_code)"
            echo "Output: $output"
            ((TESTS_FAILED++))
        fi
    else
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}PASS${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}FAIL${NC} - Hook should not have triggered (exit code: $exit_code)"
            echo "Output: $output"
            ((TESTS_FAILED++))
        fi
    fi
}

# Copy of extract_file_patterns function for testing
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

# Function to test file pattern extraction
test_extraction() {
    local test_name="$1"
    local command="$2"
    local expected="$3"
    
    echo -n "Testing extraction: $test_name ... "
    
    # Call the extraction function
    local result=$(extract_file_patterns "$command")
    
    if [ "$result" = "$expected" ]; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        echo "  Command: $command"
        echo "  Expected: '$expected'"
        echo "  Got: '$result'"
        ((TESTS_FAILED++))
    fi
}

echo "=========================================="
echo "AST-GREP HOOK COMPREHENSIVE TEST SUITE"
echo "=========================================="

# Section 1: Core Functionality Tests
echo -e "\n${BLUE}=== SECTION 1: Core Functionality Tests ===${NC}"

echo -e "\n${YELLOW}1.1 Basic Detection${NC}"
run_test "Basic Python detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep class *.py"}}' \
    "Pattern suggestions for .py:" \
    "true"

run_test "Basic JavaScript detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep function *.js"}}' \
    "Pattern suggestions for .js:" \
    "true"

run_test "Basic Go detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep func *.go"}}' \
    "Pattern suggestions for .go:" \
    "true"

echo -e "\n${YELLOW}1.2 Non-Code Files (Should Not Trigger)${NC}"
run_test "Text files" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep TODO *.txt"}}' \
    "" \
    "false"

run_test "Markdown files" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep ## *.md"}}' \
    "" \
    "false"

echo -e "\n${YELLOW}1.3 Direct Grep Tool Usage${NC}"
run_test "Grep tool with Go files" \
    '{"tool_name": "Grep", "tool_input": {"pattern": "TODO", "include": "*.go"}}' \
    "Pattern suggestions for .go:" \
    "true"

run_test "Grep tool with TypeScript" \
    '{"tool_name": "Grep", "tool_input": {"pattern": "import", "include": "*.ts"}}' \
    "Pattern suggestions for .ts:" \
    "true"

# Section 2: File Pattern Extraction Tests
echo -e "\n${BLUE}=== SECTION 2: File Pattern Extraction Tests ===${NC}"

echo -e "\n${YELLOW}2.1 Basic Patterns${NC}"
test_extraction "Simple *.js" "grep function *.js" "*.js"
test_extraction "Simple *.py" "grep class *.py" "*.py"
test_extraction "Multiple files" "grep TODO *.js *.py" "*.js
*.py"

echo -e "\n${YELLOW}2.2 With Grep Flags${NC}"
test_extraction "grep -r pattern *.go" "grep -r pattern *.go" "*.go"
test_extraction "grep -n pattern *.rb" "grep -n pattern *.rb" "*.rb"
test_extraction "grep -i pattern *.java" "grep -i pattern *.java" "*.java"
test_extraction "grep -e pattern *.php" "grep -e pattern *.php" "*.php"
test_extraction "grep -e 'pattern' *.php" "grep -e 'pattern' *.php" "*.php"

echo -e "\n${YELLOW}2.3 Complex Patterns${NC}"
test_extraction "Path with directory" "grep function src/main.go" "src/main.go"
test_extraction "Glob pattern" "grep TODO src/**/*.rs" "src/**/*.rs"
test_extraction "Brace expansion" 'grep import "*.{ts,tsx}"' "*.{ts,tsx}"
test_extraction "Multiple with paths" "grep TODO src/*.js lib/*.py" "src/*.js
lib/*.py"

echo -e "\n${YELLOW}2.4 Quoted Patterns${NC}"
test_extraction "Double quoted file" 'grep TODO "my file.js"' "my file.js"
test_extraction "Single quoted file" "grep TODO 'test.py'" "test.py"
test_extraction "Mixed quotes" 'grep TODO "file1.js" file2.py' "file1.js
file2.py"

echo -e "\n${YELLOW}2.5 Special Cases${NC}"
test_extraction "--include flag" 'grep -r --include="*.java" "@Component"' "*.java"
test_extraction "--include no quotes" 'grep -r --include=*.cpp "class"' "*.cpp"
test_extraction "No files" "grep pattern" ""
test_extraction "CSS file" 'grep ".my-class" *.css' "*.css"
test_extraction "YAML files" 'grep "port:" *.yml *.yaml' "*.yml
*.yaml"

echo -e "\n${YELLOW}2.6 Should NOT Match${NC}"
test_extraction "No extension" "grep pattern README" ""
test_extraction "Hidden file (not code)" "grep pattern .gitignore" ""
test_extraction "Regex pattern confused as file" 'grep ".*\\.js" file.txt' "file.txt"

# Section 3: Original Hook Tests
echo -e "\n${BLUE}=== SECTION 3: Pattern Detection and Edge Cases ===${NC}"

echo -e "\n${YELLOW}3.1 Complex File Pattern Extraction${NC}"
run_test "Quoted pattern with spaces" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep TODO \"my file.js\""}}' \
    "Pattern suggestions for .js:" \
    "true"

run_test "Single quoted pattern" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep TODO '\''test.py'\''"}}' \
    "Pattern suggestions for .py:" \
    "true"

run_test "Path with directory" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep function src/main.go"}}' \
    "Pattern suggestions for .go:" \
    "true"

run_test "Glob pattern with path" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep TODO src/**/*.rs"}}' \
    "Pattern suggestions for .rs:" \
    "true"

run_test "Brace expansion pattern" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep import \"*.{ts,tsx}\""}}' \
    "Pattern suggestions for .ts:" \
    "true"

echo -e "\n${YELLOW}3.2 Specific Pattern Detection${NC}"
run_test "Python def detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"def \" *.py"}}' \
    "def \$FUNC(\$\$\$PARAMS): \$\$\$" \
    "true"

run_test "Go error checking pattern" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"if err != nil\" *.go"}}' \
    "if err != nil { \$\$\$BODY }" \
    "true"

run_test "TypeScript console detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"console.log\" *.ts"}}' \
    "console.\$METHOD(\$\$\$)" \
    "true"

run_test "Rust unwrap detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \".unwrap()\" *.rs"}}' \
    "\$EXPR.unwrap()" \
    "true"

run_test "Ruby each block detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \".each {\" *.rb"}}' \
    "\$ENUMERABLE.each { |\$VAR| \$\$\$BODY }" \
    "true"

echo -e "\n${YELLOW}3.3 Edge Cases and Special Characters${NC}"
run_test "Pattern with regex special chars" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"function.*{\" *.js"}}' \
    "Pattern suggestions for .js:" \
    "true"

run_test "Multiple extensions same command" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep TODO file1.py file2.rb file3.go"}}' \
    "Pattern suggestions for .py:" \
    "true"

run_test "Complex grep flags" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep -r -n --include=\"*.java\" \"@Component\""}}' \
    "Pattern suggestions for .java:" \
    "true"

run_test "Grep with -e flag" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep -e \"pattern\" *.php"}}' \
    "Pattern suggestions for .php:" \
    "true"

echo -e "\n${YELLOW}3.4 Non-Triggering Cases${NC}"
run_test "ripgrep command" \
    '{"tool_name": "Bash", "tool_input": {"command": "rg pattern *.js"}}' \
    "" \
    "false"

run_test "ast-grep command" \
    '{"tool_name": "Bash", "tool_input": {"command": "ast-grep --pattern \"$FUNC()\" *.js"}}' \
    "" \
    "false"

run_test "No file pattern" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep -r TODO"}}' \
    "" \
    "false"

run_test "Different tool" \
    '{"tool_name": "Read", "tool_input": {"file": "test.js"}}' \
    "" \
    "false"

echo -e "\n${YELLOW}3.5 Real-World Scenarios${NC}"
run_test "Find TODO comments in TypeScript" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep -n \"// TODO\\|// FIXME\" src/**/*.ts"}}' \
    "Pattern suggestions for .ts:" \
    "true"

run_test "Search Python imports" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"^from .* import\\|^import \" lib/*.py"}}' \
    "Pattern suggestions for .py:" \
    "true"

run_test "Find React components" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"<[A-Z][a-zA-Z]*\" components/*.tsx"}}' \
    "Pattern suggestions for .tsx:" \
    "true"

run_test "Search for async functions" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"async def\" **/*.py"}}' \
    "async def \$FUNC(\$\$\$PARAMS): \$\$\$" \
    "true"

echo -e "\n${YELLOW}3.6 Language-Specific Pattern Matching${NC}"
run_test "C malloc detection" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"malloc(\" *.c"}}' \
    "malloc(\$SIZE)" \
    "true"

run_test "Java try-catch" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"try {\" *.java"}}' \
    "try { \$\$\$TRY } catch (\$EXCEPTION \$VAR) { \$\$\$CATCH }" \
    "true"

run_test "CSS class selector" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"\\.my-class\" *.css"}}' \
    "Pattern suggestions for .css:" \
    "true"

run_test "YAML port config" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"port:\" *.yml"}}' \
    "\$KEY: \$VALUE" \
    "true"

echo -e "\n${YELLOW}3.7 Pattern Fallback Behavior${NC}"
run_test "No specific pattern match - Python" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"RANDOM_STRING\" *.py"}}' \
    "Match function definitions" \
    "true"

run_test "No specific pattern match - Go" \
    '{"tool_name": "Bash", "tool_input": {"command": "grep \"UNCOMMON\" *.go"}}' \
    "Match function declarations" \
    "true"

echo -e "\n${YELLOW}3.8 Invalid Inputs${NC}"
run_test "Invalid JSON (should exit with error)" \
    'invalid json' \
    "" \
    "error"

run_test "Empty command" \
    '{"tool_name": "Bash", "tool_input": {"command": ""}}' \
    "" \
    "false"

run_test "Null tool input" \
    '{"tool_name": "Bash", "tool_input": null}' \
    "" \
    "false"

# Summary
echo -e "\n=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Total tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi