# Claude Code Hooks

This directory contains hooks that can be installed to extend Claude Code's functionality.

Read more: https://code.claude.com/docs/en/hooks

## Creating New Hooks

To create a new hook, create a directory with:

1. `hook.sh` - The hook script that receives JSON input via stdin
2. `config.json` - Hook metadata and configuration
3. `deps.sh` (optional) - Dependency check script that exits 0 if all dependencies are met

### Example config.json:
```json
{
  "name": "hook-name",
  "description": "What this hook does",
  "hook_type": "PostToolUse",
  "matcher": "Write|Edit",
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

### Manual Installation

If you prefer to configure hooks manually instead of using the installer, add them to your Claude Code settings file.

**Global** (`~/.claude/settings.json`) or **Local** (`.claude/settings.json`):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/hook.sh"
          }
        ]
      }
    ]
  }
}
```
