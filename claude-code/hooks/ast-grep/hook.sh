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
            
            # Extract file patterns from the command
            # This handles common patterns like *.js, file.py, etc.
            file_pattern=$(echo "$command" | grep -oE '[*]?\.[a-zA-Z0-9]+' | head -1)
            if [ -n "$file_pattern" ]; then
                include_pattern="$file_pattern"
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

# Embedded code extensions that ast-grep supports
code_extensions="
.bash
.bats
.cgi
.command
.env
.fcgi
.ksh
.sh
.sh.in
.tmux
.tool
.zsh
.c
.h
.cc
.hpp
.cpp
.c++
.hh
.cxx
.cu
.ino
.cs
.css
.ex
.exs
.go
.hs
.html
.htm
.xhtml
.java
.cjs
.js
.mjs
.jsx
.kt
.ktm
.kts
.lua
.php
.py
.py3
.pyi
.bzl
.rb
.rbw
.gemspec
.rs
.scala
.sc
.sbt
.swift
.ts
.cts
.mts
.tsx
"

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

# If searching in code files, provide gentle feedback
if [ "$is_code_file" = true ]; then
    echo "" >&2
    echo "💡 Note for future Claude: grep detected while searching in code files." >&2
    echo "   ast-grep is installed and understands code syntax better than text matching." >&2
    echo "   Consider using 'ast-grep --pattern ...' for more precise code searches in the future." >&2
    echo "" >&2
    # Exit with code 2 so Claude sees the feedback (PostToolUse behavior)
    exit 2
fi

# No feedback needed - exit normally
exit 0
