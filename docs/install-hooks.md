# install-hooks

The `install-hooks` script manages Claude Code hooks that automatically run after Claude performs operations on files. It provides both an interactive UI and command-line interface for installing, uninstalling, and managing hooks in either global or local contexts.

## Overview

The script provides:

1. **Interactive mode**: Terminal UI with arrow key navigation for easy hook management
2. **Command-line mode**: Direct commands for automation and scripting
3. **Dual installation modes**: Global (system-wide) or local (project-specific) installations
4. **Smart detection**: Automatically detects where hooks are installed for seamless management

## Installation Modes

### Global Mode
- **Location**: `~/.claude/hooks/ethpandaops/`
- **Config**: `~/.claude/settings.json`
- **Scope**: Hooks apply to all projects on your system
- **Use case**: Common formatting/linting that should apply everywhere

### Local Mode
- **Location**: `.claude/hooks/ethpandaops/` (in current directory)
- **Config**: `.claude/settings.json` (in current directory)
- **Scope**: Hooks apply only to the specific project
- **Use case**: Project-specific tooling or conventions

## Usage

### Interactive Mode

Launch the interactive UI by running without arguments:

```bash
install-hooks.py
```

#### Interactive Controls

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate through hooks |
| `ENTER` | Install/uninstall selected hook |
| `d` | Toggle detailed view for selected hook |
| `a` | Install all available hooks |
| `r` | Remove all installed hooks |
| `m` | Change installation mode (global/local) |
| `q` | Quit the application |

#### Interactive Features

- **Visual feedback**: Installed hooks show with green checkmarks (✓)
- **Smart toggling**: ENTER installs if not installed, uninstalls if already installed
- **Details view**: Press 'd' to see full description, dependencies, and file paths
- **Mode switching**: Change between global and local without restarting
- **Terminal resize support**: UI automatically adjusts when terminal is resized

### Command Line Mode

#### Installation Commands

```bash
# Install specific hook (prompts for mode if not specified)
install-hooks.py --install gofmt

# Install with explicit mode
install-hooks.py --install gofmt --global
install-hooks.py -i gofmt -L  # Local installation

# Install all available hooks
install-hooks.py --all
install-hooks.py --all --local
```

#### Listing Commands

```bash
# List all hooks (shows both global and local)
install-hooks.py --list

# List specific mode
install-hooks.py --list --global
install-hooks.py -l -L  # List local only
```

#### Uninstall Commands

```bash
# Uninstall specific hook (auto-detects location)
install-hooks.py --uninstall gofmt

# Uninstall with explicit mode
install-hooks.py --uninstall gofmt --global
install-hooks.py -u gofmt -L  # Uninstall from local

# Uninstall all hooks
install-hooks.py --uninstall all --local
```

#### Information Commands

```bash
# Show detailed information about a hook
install-hooks.py --show gofmt
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--install HOOK` | `-i` | Install specific hook |
| `--uninstall HOOK` | `-u` | Uninstall specific hook (use "all" for all hooks) |
| `--all` | `-a` | Install all available hooks |
| `--list` | `-l` | List installed hooks |
| `--show HOOK` | `-s` | Show detailed hook information |
| `--global` | `-g` | Use global installation mode |
| `--local` | `-L` | Use local installation mode |
| `--help` | `-h` | Show help message |

## Smart Mode Detection

The script intelligently handles mode selection:

### For Uninstall Operations
1. **Single location**: Automatically uninstalls from where it's found
2. **Both locations**: Prompts user to specify `--global` or `--local`
3. **Not installed**: Shows appropriate warning

### For Install Operations
1. **Already installed**: Shows where it's installed and exits
2. **Not installed**: Prompts for installation mode if not specified

## Available Hooks

### gofmt
- **Description**: Automatically formats Go files after editing
- **Trigger**: After Write or Edit operations
- **Dependencies**: Requires `gofmt` command

### eslint
- **Description**: Formats and lints JavaScript/TypeScript files
- **Trigger**: After Write or Edit operations
- **Dependencies**: Requires `npx` and project-level eslint

### rustfmt
- **Description**: Formats Rust files with rustfmt
- **Trigger**: After Write or Edit operations
- **Dependencies**: Requires `rustfmt` (via rustup)

*Additional hooks can be found in `claude-code/hooks/`*

## Hook Structure

Each hook consists of:

```
hook-name/
├── hook.sh        # The executable script
├── config.json    # Hook configuration
└── deps.sh        # Optional dependency checker
```

### config.json Format

```json
{
  "description": "Brief description of what the hook does",
  "hook_type": "PostToolUse",
  "matcher": "Write|Edit"
}
```

## Settings Configuration

Hooks are configured in the Claude settings file:

### Global: ~/.claude/settings.json
### Local: .claude/settings.json

Example configuration:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "/home/user/.claude/hooks/ethpandaops/gofmt.sh"
        }]
      }
    ]
  }
}
```

## Examples

### Project-Specific Go Formatting

Set up Go formatting for a specific project:

```bash
cd my-go-project
install-hooks.py --install gofmt --local
```

### Global Web Development Setup

Install eslint globally for all web projects:

```bash
install-hooks.py --install eslint --global
```

### Audit Hook Installation

Check what's installed where:

```bash
# See everything
install-hooks.py --list

# Check specific hook details
install-hooks.py --show gofmt
```

### Clean Uninstall

Remove hooks when switching tools:

```bash
# Remove from everywhere it's installed
install-hooks.py --uninstall eslint

# Remove all hooks from local project
cd my-project
install-hooks.py --uninstall all --local
```

## Troubleshooting

### Command Not Found

If `install-hooks.py` is not found:

```bash
# Re-run setup
cd /path/to/ai-cookbook
./setup.sh

# Or add scripts to PATH manually
export PATH="$PATH:/path/to/ai-cookbook/scripts"
```

### Permission Denied

If you get permission errors:

```bash
# Make script executable
chmod +x /path/to/ai-cookbook/scripts/install-hooks.py
```

### Hook Not Running

If installed hooks aren't executing:

1. **Check installation**:
   ```bash
   install-hooks.py --list
   install-hooks.py --show hook-name
   ```

2. **Verify dependencies**:
   ```bash
   # Check if required command exists
   which gofmt  # or rustfmt, etc.
   ```

3. **Check Claude settings**:
   ```bash
   # Global
   cat ~/.claude/settings.json | jq .hooks

   # Local
   cat .claude/settings.json | jq .hooks
   ```

### Multiple Installation Conflicts

If a hook is installed both globally and locally:

- Local installation takes precedence
- Use explicit `--global` or `--local` flags to manage specific installation
- Consider uninstalling from one location to avoid confusion

## Creating Custom Hooks

To add new hooks to the repository:

1. Create directory: `claude-code/hooks/your-hook/`
2. Add `hook.sh` with your script
3. Add `config.json` with hook metadata
4. Optionally add `deps.sh` to check dependencies
5. Test with `install-hooks.py --show your-hook`

Example minimal hook:

```bash
# claude-code/hooks/example/hook.sh
#!/bin/bash
echo "Hook executed for file: $1"
```

```json
// claude-code/hooks/example/config.json
{
  "description": "Example hook that prints filename",
  "hook_type": "PostToolUse",
  "matcher": "Write|Edit"
}
```

## Best Practices

1. **Use local mode** for project-specific tools and conventions
2. **Use global mode** for universal formatters you always want
3. **Check dependencies** before installing hooks (`--show` command)
4. **Test hooks** after installation by editing a relevant file
5. **Document custom hooks** in your project README if using local installation