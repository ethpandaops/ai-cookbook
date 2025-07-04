"""
Configuration settings for ai-cookbook
Unified installer for ethPandaOps AI cookbook components
"""

from pathlib import Path

# Application constants
APP_NAME = "ai-cookbook"
VERSION = "1.0.0"

# Installation paths
CLAUDE_DIR = Path.home() / ".claude"
CLAUDE_COMMANDS_DIR = CLAUDE_DIR / "commands" / "ethpandaops"
CLAUDE_STANDARDS_DIR = CLAUDE_DIR / "ethpandaops" / "code-standards"
CLAUDE_HOOKS_DIR = CLAUDE_DIR / "hooks" / "ethpandaops"

# Source paths (relative to repo root)
REPO_ROOT = Path(__file__).parent.parent.parent.parent
COMMANDS_SOURCE = REPO_ROOT / "claude-code" / "commands"
STANDARDS_SOURCE = REPO_ROOT / "claude-code" / "code-standards"
HOOKS_SOURCE = REPO_ROOT / "claude-code" / "hooks"
SCRIPTS_SOURCE = REPO_ROOT / "scripts"

# UI configuration
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'WHITE': '\033[97m',
    'RESET': '\033[0m',
    'BOLD': '\033[1m',
    'REVERSE': '\033[7m'
}

# Menu configuration
MAIN_MENU_ITEMS = [
    "Claude Commands",
    "Code Standards", 
    "Hooks",
    "Scripts"
]