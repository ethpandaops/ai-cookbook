#!/bin/bash

# Test script for the ast-grep hook
HOOK_SCRIPT="$(dirname "$0")/hook.sh"

echo "Testing ast-grep hook implementation..."
echo "======================================="

# Test 1: Basic grep with .js file pattern
echo -e "\nTest 1: grep 'function' *.js"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''function'\'' *.js"}}' | bash "$HOOK_SCRIPT"

# Test 2: Complex pattern with quotes
echo -e "\nTest 2: grep 'class' \"src/**/*.py\""
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''class'\'' \"src/**/*.py\""}}' | bash "$HOOK_SCRIPT"

# Test 3: Multiple patterns
echo -e "\nTest 3: grep 'import' *.ts *.tsx"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''import'\'' *.ts *.tsx"}}' | bash "$HOOK_SCRIPT"

# Test 4: Direct Grep tool usage
echo -e "\nTest 4: Grep tool with include pattern"
echo '{"tool_name": "Grep", "tool_input": {"pattern": "TODO", "include": "*.go"}}' | bash "$HOOK_SCRIPT"

# Test 5: Non-code file (should not trigger)
echo -e "\nTest 5: grep 'text' *.txt (should not trigger)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''text'\'' *.txt"}}' | bash "$HOOK_SCRIPT"
echo "Exit code: $?"

# Test 6: ripgrep command (should not trigger)
echo -e "\nTest 6: rg 'pattern' *.js (should not trigger)"
echo '{"tool_name": "Bash", "tool_input": {"command": "rg '\''pattern'\'' *.js"}}' | bash "$HOOK_SCRIPT"
echo "Exit code: $?"

echo -e "\n======================================="
echo "REGEX PATTERN DETECTION TESTS"
echo "======================================="

# Test 7: Go error checking pattern
echo -e "\nTest 7: grep 'if err != nil' *.go (Go error pattern)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''if err != nil'\'' *.go"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 8: Python decorator pattern
echo -e "\nTest 8: grep '@decorator' *.py (Python decorator)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''@decorator'\'' *.py"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 9: JavaScript arrow function
echo -e "\nTest 9: grep '=>' *.js (Arrow function)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep \"=>\" *.js"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 10: Rust match expression
echo -e "\nTest 10: grep 'match' *.rs (Rust match)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''match '\'' *.rs"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 11: TypeScript interface
echo -e "\nTest 11: grep 'interface' *.ts (TypeScript interface)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''interface'\'' *.ts"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 12: CSS class selector
echo -e "\nTest 12: grep '.class-name' *.css (CSS class)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''.class-name'\'' *.css"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 13: Java try-catch
echo -e "\nTest 13: grep 'try {' *.java (Java try-catch)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''try {'\'' *.java"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 14: Ruby each iterator
echo -e "\nTest 14: grep '.each' *.rb (Ruby each)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''.each'\'' *.rb"}}' | bash "$HOOK_SCRIPT" 2>&1

# Test 15: C malloc call
echo -e "\nTest 15: grep 'malloc(' *.c (C malloc)"
echo '{"tool_name": "Bash", "tool_input": {"command": "grep '\''malloc('\'' *.c"}}' | bash "$HOOK_SCRIPT" 2>&1

echo -e "\n======================================="
echo "Testing complete!"