# Claude Code Hooks

This directory contains hooks that can be installed to extend Claude Code's functionality.

Read more: https://docs.anthropic.com/en/docs/claude-code/hooks

## Creating New Hooks

To create a new hook, create a directory with:

1. `hook.sh` or `hook.py` - The hook script that receives JSON input via stdin
2. `config.json` - Hook metadata and configuration
3. `deps.sh` (optional) - Dependency check script that exits 0 if all dependencies are met

### Example config.json:
```json
{
  "name": "hook-name",
  "description": "What this hook does",
  "hook_type": "PostToolUse",
  "matcher": "Write|Edit|MultiEdit",
  "requirements": {
    "commands": ["required-command"],
    "description": "Human readable requirements"
  }
}
```

### Hook Input Format

Hooks receive JSON input via stdin with this structure:
```json
{
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.go",
    "old_string": "...",
    "new_string": "..."
  },
  "tool_response": {
    // Tool response data
  }
}
```
