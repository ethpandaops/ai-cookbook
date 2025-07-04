# Unified Installation System Implementation Plan

## Executive Summary
> This plan unifies four separate installation scripts (`setup.sh`, `install-code-standards.sh`, `install-hooks.py`, and script PATH management) into a single, maintainable Python application called `ai-cookbook`. The new system provides a cohesive user experience with an interactive menu system modeled after the existing `install-hooks.py` interface, while maintaining all existing functionality and improving code organization.

## Goals & Objectives
### Primary Goals
- **Unified Interface**: Single command (`ai-cookbook`) that handles all installation types with consistent UI
- **Maintainable Architecture**: Well-structured Python package in `src/` with proper separation of concerns
- **Feature Parity**: Preserve all functionality from existing scripts without regression
- **User Experience**: Interactive menu system with keyboard navigation and visual feedback

### Secondary Objectives
- **Code Quality**: Follow Python best practices with type hints, error handling, and documentation
- **Extensibility**: Architecture that easily supports adding new installation types
- **Backward Compatibility**: Smooth migration path for existing users
- **Simplified Distribution**: Single entry point that can be installed via `setup.sh`

## Solution Overview
### Approach
Create a Python package structure that separates UI components from business logic, with dedicated installer modules for each installation type. The main application provides a unified menu interface while delegating specific installation tasks to specialized modules.

### Key Components
1. **Main Application**: Entry point with menu system and navigation
2. **UI System**: Terminal interface components for consistent user experience
3. **Installer Modules**: Dedicated modules for commands, code standards, hooks, and scripts
4. **Utilities**: Shared functionality for file operations, backups, and system integration
5. **Configuration**: Centralized settings and constants

### Architecture Diagram
```
ai-cookbook
├── Main Menu
│   ├── Claude Commands → commands.py
│   ├── Code Standards → code_standards.py
│   ├── Hooks → hooks.py
│   └── Scripts → scripts.py
├── UI System (terminal.py, menu.py)
├── Utilities (file_ops.py, backup.py)
└── Configuration (settings.py)
```

### Data Flow
```
User Input → Main Menu → Installer Module → System Files
     ↓
Terminal UI ← Status/Progress ← File Operations
```

### Expected Outcomes
- **Single Installation Command**: Users run `ai-cookbook` instead of multiple scripts
- **Consistent Interface**: All installation types use the same UI patterns and keyboard shortcuts
- **Maintainable Codebase**: Clean separation allows easy modification and extension
- **Preserved Functionality**: All existing features work identically to current scripts
- **Simplified Maintenance**: Single codebase to update instead of multiple shell/Python scripts

## Implementation Tasks

### CRITICAL IMPLEMENTATION RULES
1. **NO PLACEHOLDER CODE**: Every implementation must be production-ready. NEVER write "TODO", "in a real implementation", or similar placeholders unless explicitly requested by the user.
2. **CROSS-DIRECTORY TASKS**: Group related changes across directories into single tasks to ensure consistency. Never create isolated changes that require follow-up work in sibling directories.
3. **COMPLETE IMPLEMENTATIONS**: Each task must fully implement its feature including all consumers, type updates, and integration points.
4. **DETAILED SPECIFICATIONS**: Each task must include EXACTLY what to implement, including specific functions, types, and integration points to avoid "breaking change" confusion.
5. **CONTEXT AWARENESS**: Each task is part of a larger system - specify how it connects to other parts.
6. **MAKE BREAKING CHANGES**: Unless explicitly requested by the user, you MUST make breaking changes.

### Visual Dependency Tree
```
src/
├── pandaops_cookbook/
│   ├── __init__.py (Task #0: Package initialization)
│   ├── main.py (Task #8: Main application entry point)
│   ├── cli.py (Task #7: Command-line interface handling)
│   │
│   ├── ui/
│   │   ├── __init__.py (Task #0: UI package initialization)
│   │   ├── terminal.py (Task #1: Terminal utilities and ANSI handling)
│   │   ├── menu.py (Task #2: Interactive menu system)
│   │   └── components.py (Task #3: Reusable UI components)
│   │
│   ├── installers/
│   │   ├── __init__.py (Task #0: Installers package initialization)
│   │   ├── base.py (Task #1: Base installer class and interfaces)
│   │   ├── commands.py (Task #4: Claude commands installer)
│   │   ├── code_standards.py (Task #5: Code standards installer)
│   │   ├── hooks.py (Task #6: Hooks installer)
│   │   └── scripts.py (Task #4: Scripts PATH installer)
│   │
│   ├── utils/
│   │   ├── __init__.py (Task #0: Utils package initialization)
│   │   ├── file_operations.py (Task #1: File and directory operations)
│   │   ├── backup.py (Task #2: Backup and restore functionality)
│   │   ├── path_utils.py (Task #1: Path handling utilities)
│   │   └── system.py (Task #1: System detection and shell integration)
│   │
│   └── config/
│       ├── __init__.py (Task #0: Config package initialization)
│       └── settings.py (Task #0: Application configuration and constants)
│
├── setup.py (Task #9: Package setup configuration)
├── setup.sh (Task #10: Entry point installer script)
└── README.md (Task #11: Documentation update)
```

### Execution Plan

#### Group A: Foundation (Execute all in parallel)
- [x] **Task #0**: Create package structure and initialization files
  - Folders: `src/pandaops_cookbook/`, `src/pandaops_cookbook/ui/`, `src/pandaops_cookbook/installers/`, `src/pandaops_cookbook/utils/`, `src/pandaops_cookbook/config/`
  - Files: All `__init__.py` files
  - Implements:
    ```python
    # src/pandaops_cookbook/__init__.py
    __version__ = "1.0.0"
    __author__ = "ethPandaOps"
    __description__ = "Unified installation system for ethPandaOps AI cookbook"
    
    # src/pandaops_cookbook/config/settings.py
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
    ```
  - Exports: Package metadata, configuration constants, paths
  - Context: Foundation for all other modules to import from

- [ ] **Task #1**: Create terminal utilities and base UI components
  - Folders: `src/pandaops_cookbook/ui/`, `src/pandaops_cookbook/utils/`
  - Files: `terminal.py`, `file_operations.py`, `path_utils.py`, `system.py`
  - Implements:
    ```python
    # src/pandaops_cookbook/ui/terminal.py
    import sys, termios, tty, os
    from typing import Optional, Tuple
    
    class TerminalController:
        def __init__(self):
            self.original_settings = None
            
        def setup_terminal(self) -> None:
            """Configure terminal for interactive use"""
            
        def restore_terminal(self) -> None:
            """Restore original terminal settings"""
            
        def get_terminal_size(self) -> Tuple[int, int]:
            """Get terminal dimensions"""
            
        def clear_screen(self) -> None:
            """Clear terminal screen"""
            
        def move_cursor(self, row: int, col: int) -> None:
            """Move cursor to position"""
            
        def hide_cursor(self) -> None:
            """Hide terminal cursor"""
            
        def show_cursor(self) -> None:
            """Show terminal cursor"""
            
        def getch(self) -> str:
            """Get single character input"""
            
        def get_key(self) -> str:
            """Get key input (handles arrow keys, etc.)"""
    
    # src/pandaops_cookbook/utils/file_operations.py
    from pathlib import Path
    from typing import List, Optional
    import shutil, json
    
    def ensure_directory(path: Path) -> None:
        """Create directory if it doesn't exist"""
        
    def copy_files(source: Path, dest: Path, patterns: List[str] = None) -> None:
        """Copy files matching patterns from source to dest"""
        
    def read_json_file(path: Path) -> dict:
        """Read and parse JSON file"""
        
    def write_json_file(path: Path, data: dict) -> None:
        """Write data to JSON file"""
        
    def remove_directory(path: Path) -> None:
        """Remove directory and contents"""
        
    def file_exists(path: Path) -> bool:
        """Check if file exists"""
        
    # src/pandaops_cookbook/utils/system.py
    import os, subprocess
    from pathlib import Path
    from typing import Optional, List
    
    def detect_shell() -> str:
        """Detect user's shell (bash, zsh, fish, etc.)"""
        
    def get_shell_profile_path() -> Path:
        """Get path to shell profile file"""
        
    def add_to_path(directory: Path) -> bool:
        """Add directory to PATH in shell profile"""
        
    def is_in_path(directory: Path) -> bool:
        """Check if directory is in PATH"""
        
    def run_command(command: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
        """Run shell command and return result"""
    ```
  - Exports: Terminal control, file operations, system integration
  - Context: Used by all installer modules and UI components

- [ ] **Task #2**: Create backup and restore functionality
  - Folder: `src/pandaops_cookbook/utils/`
  - File: `backup.py`
  - Implements:
    ```python
    from pathlib import Path
    from datetime import datetime
    import shutil, json
    from typing import Optional, List
    
    class BackupManager:
        def __init__(self, backup_dir: Path = None):
            self.backup_dir = backup_dir or Path.home() / ".claude" / "backups"
            
        def create_backup(self, file_path: Path, prefix: str = "backup") -> Path:
            """Create timestamped backup of file"""
            
        def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
            """Restore file from backup"""
            
        def list_backups(self, prefix: str = None) -> List[Path]:
            """List available backups"""
            
        def cleanup_old_backups(self, max_age_days: int = 30) -> None:
            """Remove backups older than max_age_days"""
            
        def backup_json_section(self, file_path: Path, section_key: str) -> Path:
            """Backup specific section of JSON file"""
    ```
  - Exports: BackupManager class for safe file operations
  - Context: Used by installers that modify system files

#### Group B: UI System (Execute all in parallel after Group A)
- [ ] **Task #3**: Create reusable UI components
  - Folder: `src/pandaops_cookbook/ui/`
  - File: `components.py`
  - Imports:
    ```python
    from .terminal import TerminalController
    from ..config.settings import COLORS
    from typing import List, Optional, Callable, Dict, Any
    ```
  - Implements:
    ```python
    class StatusIndicator:
        """Visual status indicators (✓, ✗, ⚠)"""
        @staticmethod
        def installed() -> str:
            return f"{COLORS['GREEN']}✓{COLORS['RESET']}"
            
        @staticmethod
        def not_installed() -> str:
            return f"{COLORS['RED']}✗{COLORS['RESET']}"
            
        @staticmethod
        def warning() -> str:
            return f"{COLORS['YELLOW']}⚠{COLORS['RESET']}"
    
    class ProgressBar:
        """Simple progress bar for operations"""
        def __init__(self, total: int, width: int = 50):
            self.total = total
            self.current = 0
            self.width = width
            
        def update(self, current: int) -> None:
            """Update progress bar"""
            
        def render(self) -> str:
            """Render progress bar string"""
    
    class MessageBox:
        """Display messages and confirmations"""
        @staticmethod
        def info(message: str) -> None:
            """Display info message"""
            
        @staticmethod
        def success(message: str) -> None:
            """Display success message"""
            
        @staticmethod
        def error(message: str) -> None:
            """Display error message"""
            
        @staticmethod
        def confirm(message: str) -> bool:
            """Ask for confirmation"""
    ```
  - Exports: UI components for consistent interface
  - Context: Used by menu system and installer modules

- [ ] **Task #4**: Create interactive menu system
  - Folder: `src/pandaops_cookbook/ui/`
  - File: `menu.py`
  - Imports:
    ```python
    from .terminal import TerminalController
    from .components import StatusIndicator, MessageBox
    from ..config.settings import COLORS, MAIN_MENU_ITEMS
    from typing import List, Dict, Callable, Optional, Any
    ```
  - Implements:
    ```python
    class MenuOption:
        """Single menu option with status and action"""
        def __init__(self, name: str, description: str, action: Callable, 
                     status_checker: Callable[[], str] = None):
            self.name = name
            self.description = description
            self.action = action
            self.status_checker = status_checker
            
        def get_status(self) -> str:
            """Get current status of this option"""
            
        def execute(self) -> Any:
            """Execute the option's action"""
    
    class InteractiveMenu:
        """Interactive menu with keyboard navigation"""
        def __init__(self, title: str, options: List[MenuOption], 
                     terminal: TerminalController):
            self.title = title
            self.options = options
            self.terminal = terminal
            self.selected_index = 0
            self.show_details = False
            
        def render(self) -> None:
            """Render the menu"""
            
        def handle_input(self) -> Optional[str]:
            """Handle keyboard input, returns action or None"""
            
        def run(self) -> None:
            """Run the interactive menu loop"""
            
        def get_selected_option(self) -> MenuOption:
            """Get currently selected option"""
            
        def move_selection(self, direction: int) -> None:
            """Move selection up/down"""
            
        def toggle_details(self) -> None:
            """Toggle details view"""
    
    class SubMenu(InteractiveMenu):
        """Submenu for specific installation types"""
        def __init__(self, title: str, installer_module, terminal: TerminalController):
            self.installer = installer_module
            options = self._build_options()
            super().__init__(title, options, terminal)
            
        def _build_options(self) -> List[MenuOption]:
            """Build options specific to this installer"""
    ```
  - Exports: Menu system for user interaction
  - Context: Used by main application and installer modules

#### Group C: Base Installer Infrastructure (Execute all in parallel after Group B)
- [ ] **Task #5**: Create base installer class and interfaces
  - Folder: `src/pandaops_cookbook/installers/`
  - File: `base.py`
  - Imports:
    ```python
    from abc import ABC, abstractmethod
    from pathlib import Path
    from typing import List, Dict, Optional, Any
    from ..utils.backup import BackupManager
    from ..utils.file_operations import ensure_directory
    from ..config.settings import CLAUDE_DIR
    ```
  - Implements:
    ```python
    class InstallationResult:
        """Result of an installation operation"""
        def __init__(self, success: bool, message: str, details: Dict[str, Any] = None):
            self.success = success
            self.message = message
            self.details = details or {}
    
    class BaseInstaller(ABC):
        """Base class for all installers"""
        def __init__(self, name: str, description: str):
            self.name = name
            self.description = description
            self.backup_manager = BackupManager()
            
        @abstractmethod
        def check_status(self) -> Dict[str, Any]:
            """Check installation status"""
            pass
            
        @abstractmethod
        def install(self) -> InstallationResult:
            """Install the component"""
            pass
            
        @abstractmethod
        def uninstall(self) -> InstallationResult:
            """Uninstall the component"""
            pass
            
        @abstractmethod
        def get_details(self) -> Dict[str, Any]:
            """Get detailed information about this installer"""
            pass
            
        def is_installed(self) -> bool:
            """Check if component is installed"""
            status = self.check_status()
            return status.get('installed', False)
            
        def get_status_string(self) -> str:
            """Get human-readable status string"""
            return "INSTALLED" if self.is_installed() else "NOT INSTALLED"
    
    class InteractiveInstaller(BaseInstaller):
        """Base class for installers with interactive options"""
        def __init__(self, name: str, description: str):
            super().__init__(name, description)
            self._interactive_options = []
            
        def add_interactive_option(self, name: str, description: str, 
                                 action: callable, status_checker: callable = None) -> None:
            """Add an interactive option"""
            
        def get_interactive_options(self) -> List[Dict[str, Any]]:
            """Get list of interactive options"""
    ```
  - Exports: Base classes and interfaces for all installers
  - Context: Foundation for all specific installer implementations

#### Group D: Specific Installers (Execute all in parallel after Group C)
- [ ] **Task #6**: Create Claude commands installer
  - Folder: `src/pandaops_cookbook/installers/`
  - File: `commands.py`
  - Imports:
    ```python
    from .base import BaseInstaller, InstallationResult
    from ..config.settings import CLAUDE_COMMANDS_DIR, COMMANDS_SOURCE
    from ..utils.file_operations import ensure_directory, copy_files, remove_directory
    from ..utils.system import add_to_path, is_in_path
    from pathlib import Path
    from typing import Dict, Any, List
    ```
  - Implements:
    ```python
    class CommandsInstaller(BaseInstaller):
        """Installer for Claude commands"""
        def __init__(self):
            super().__init__(
                name="Claude Commands",
                description="Install Claude Code commands for AI-assisted development"
            )
            
        def check_status(self) -> Dict[str, Any]:
            """Check if commands are installed"""
            commands_installed = CLAUDE_COMMANDS_DIR.exists() and len(list(CLAUDE_COMMANDS_DIR.glob("*.md"))) > 0
            scripts_in_path = is_in_path(COMMANDS_SOURCE.parent / "scripts")
            
            return {
                'installed': commands_installed and scripts_in_path,
                'commands_installed': commands_installed,
                'scripts_in_path': scripts_in_path,
                'command_count': len(list(CLAUDE_COMMANDS_DIR.glob("*.md"))) if commands_installed else 0
            }
            
        def install(self) -> InstallationResult:
            """Install Claude commands and add scripts to PATH"""
            try:
                # Create commands directory
                ensure_directory(CLAUDE_COMMANDS_DIR)
                
                # Copy command files
                copy_files(COMMANDS_SOURCE, CLAUDE_COMMANDS_DIR, ["*.md"])
                
                # Add scripts to PATH
                scripts_dir = COMMANDS_SOURCE.parent / "scripts"
                if not add_to_path(scripts_dir):
                    return InstallationResult(False, "Failed to add scripts to PATH")
                
                return InstallationResult(True, "Claude commands installed successfully")
                
            except Exception as e:
                return InstallationResult(False, f"Installation failed: {str(e)}")
                
        def uninstall(self) -> InstallationResult:
            """Uninstall Claude commands"""
            try:
                if CLAUDE_COMMANDS_DIR.exists():
                    remove_directory(CLAUDE_COMMANDS_DIR)
                    
                return InstallationResult(True, "Claude commands uninstalled successfully")
                
            except Exception as e:
                return InstallationResult(False, f"Uninstallation failed: {str(e)}")
                
        def get_details(self) -> Dict[str, Any]:
            """Get detailed information about commands"""
            commands = []
            if CLAUDE_COMMANDS_DIR.exists():
                for cmd_file in CLAUDE_COMMANDS_DIR.glob("*.md"):
                    commands.append({
                        'name': cmd_file.stem,
                        'file': cmd_file.name,
                        'path': str(cmd_file)
                    })
                    
            return {
                'commands': commands,
                'source_path': str(COMMANDS_SOURCE),
                'install_path': str(CLAUDE_COMMANDS_DIR),
                'scripts_path': str(COMMANDS_SOURCE.parent / "scripts")
            }
            
        def list_available_commands(self) -> List[str]:
            """List all available commands"""
            return [f.stem for f in COMMANDS_SOURCE.glob("*.md")]
    ```
  - Exports: CommandsInstaller class
  - Context: Handles Claude commands installation, used by main menu

- [ ] **Task #7**: Create code standards installer
  - Folder: `src/pandaops_cookbook/installers/`
  - File: `code_standards.py`
  - Imports:
    ```python
    from .base import BaseInstaller, InstallationResult
    from ..config.settings import CLAUDE_STANDARDS_DIR, STANDARDS_SOURCE, CLAUDE_DIR
    from ..utils.file_operations import ensure_directory, copy_files, read_json_file
    from ..utils.backup import BackupManager
    from pathlib import Path
    import re
    from typing import Dict, Any, List
    ```
  - Implements:
    ```python
    class CodeStandardsInstaller(BaseInstaller):
        """Installer for code standards"""
        def __init__(self):
            super().__init__(
                name="Code Standards",
                description="Install ethPandaOps coding standards for various languages"
            )
            self.claude_md_path = CLAUDE_DIR / "CLAUDE.md"
            self.start_marker = "<!-- ETHPANDAOPS_STANDARDS_START -->"
            self.end_marker = "<!-- ETHPANDAOPS_STANDARDS_END -->"
            
        def check_status(self) -> Dict[str, Any]:
            """Check if code standards are installed"""
            standards_installed = CLAUDE_STANDARDS_DIR.exists()
            claude_md_modified = self._check_claude_md_modified()
            
            return {
                'installed': standards_installed and claude_md_modified,
                'standards_copied': standards_installed,
                'claude_md_modified': claude_md_modified,
                'languages': self._get_installed_languages()
            }
            
        def install(self) -> InstallationResult:
            """Install code standards"""
            try:
                # Create backup of CLAUDE.md
                if self.claude_md_path.exists():
                    self.backup_manager.create_backup(self.claude_md_path, "claude_md")
                
                # Copy standards files
                ensure_directory(CLAUDE_STANDARDS_DIR)
                copy_files(STANDARDS_SOURCE, CLAUDE_STANDARDS_DIR)
                
                # Modify CLAUDE.md
                self._modify_claude_md()
                
                return InstallationResult(True, "Code standards installed successfully")
                
            except Exception as e:
                return InstallationResult(False, f"Installation failed: {str(e)}")
                
        def uninstall(self) -> InstallationResult:
            """Uninstall code standards"""
            try:
                # Remove section from CLAUDE.md
                if self.claude_md_path.exists():
                    self.backup_manager.create_backup(self.claude_md_path, "claude_md")
                    self._remove_claude_md_section()
                
                # Remove standards directory
                if CLAUDE_STANDARDS_DIR.exists():
                    remove_directory(CLAUDE_STANDARDS_DIR)
                    
                return InstallationResult(True, "Code standards uninstalled successfully")
                
            except Exception as e:
                return InstallationResult(False, f"Uninstallation failed: {str(e)}")
                
        def get_details(self) -> Dict[str, Any]:
            """Get detailed information about code standards"""
            config = self._load_config()
            return {
                'config': config,
                'available_languages': list(config.keys()) if config else [],
                'installed_languages': self._get_installed_languages(),
                'claude_md_path': str(self.claude_md_path),
                'standards_path': str(CLAUDE_STANDARDS_DIR)
            }
            
        def _load_config(self) -> Dict[str, Any]:
            """Load config.json from standards source"""
            config_path = STANDARDS_SOURCE / "config.json"
            if config_path.exists():
                return read_json_file(config_path)
            return {}
            
        def _check_claude_md_modified(self) -> bool:
            """Check if CLAUDE.md contains ethPandaOps section"""
            if not self.claude_md_path.exists():
                return False
                
            content = self.claude_md_path.read_text()
            return self.start_marker in content and self.end_marker in content
            
        def _modify_claude_md(self) -> None:
            """Add ethPandaOps section to CLAUDE.md"""
            # Implementation details for modifying CLAUDE.md
            
        def _remove_claude_md_section(self) -> None:
            """Remove ethPandaOps section from CLAUDE.md"""
            # Implementation details for removing section
            
        def _get_installed_languages(self) -> List[str]:
            """Get list of installed language standards"""
            if not CLAUDE_STANDARDS_DIR.exists():
                return []
                
            languages = []
            for lang_dir in CLAUDE_STANDARDS_DIR.iterdir():
                if lang_dir.is_dir() and (lang_dir / "CLAUDE.md").exists():
                    languages.append(lang_dir.name)
            return languages
    ```
  - Exports: CodeStandardsInstaller class
  - Context: Handles code standards installation, used by main menu

- [ ] **Task #8**: Create hooks installer
  - Folder: `src/pandaops_cookbook/installers/`
  - File: `hooks.py`
  - Imports:
    ```python
    from .base import InteractiveInstaller, InstallationResult
    from ..config.settings import CLAUDE_HOOKS_DIR, HOOKS_SOURCE, CLAUDE_DIR
    from ..utils.file_operations import ensure_directory, copy_files, read_json_file, write_json_file
    from ..ui.menu import MenuOption
    from pathlib import Path
    from typing import Dict, Any, List
    ```
  - Implements:
    ```python
    class HooksInstaller(InteractiveInstaller):
        """Interactive installer for Claude hooks"""
        def __init__(self):
            super().__init__(
                name="Hooks",
                description="Install Claude Code hooks for automated formatting and linting"
            )
            self.global_settings = CLAUDE_DIR / "settings.json"
            self.local_settings = Path(".claude/settings.local.json")
            self.mode = "global"  # "global" or "local"
            
        def check_status(self) -> Dict[str, Any]:
            """Check hooks installation status"""
            global_hooks = self._get_installed_hooks("global")
            local_hooks = self._get_installed_hooks("local")
            
            return {
                'installed': len(global_hooks) > 0 or len(local_hooks) > 0,
                'global_hooks': global_hooks,
                'local_hooks': local_hooks,
                'mode': self.mode
            }
            
        def install(self) -> InstallationResult:
            """Install all hooks (not typically used - use install_hook instead)"""
            return InstallationResult(True, "Use interactive mode to install specific hooks")
            
        def uninstall(self) -> InstallationResult:
            """Uninstall all hooks"""
            try:
                removed_count = 0
                for hook_name in self.get_available_hooks():
                    result = self.uninstall_hook(hook_name)
                    if result.success:
                        removed_count += 1
                        
                return InstallationResult(True, f"Removed {removed_count} hooks")
                
            except Exception as e:
                return InstallationResult(False, f"Uninstallation failed: {str(e)}")
                
        def get_details(self) -> Dict[str, Any]:
            """Get detailed information about hooks"""
            hooks_info = {}
            for hook_name in self.get_available_hooks():
                hook_info = self._get_hook_info(hook_name)
                hooks_info[hook_name] = hook_info
                
            return {
                'available_hooks': hooks_info,
                'mode': self.mode,
                'global_settings': str(self.global_settings),
                'local_settings': str(self.local_settings)
            }
            
        def get_available_hooks(self) -> List[str]:
            """Get list of available hooks"""
            hooks = []
            for hook_dir in HOOKS_SOURCE.iterdir():
                if hook_dir.is_dir() and (hook_dir / "config.json").exists():
                    hooks.append(hook_dir.name)
            return sorted(hooks)
            
        def install_hook(self, hook_name: str) -> InstallationResult:
            """Install a specific hook"""
            try:
                hook_source = HOOKS_SOURCE / hook_name
                if not hook_source.exists():
                    return InstallationResult(False, f"Hook '{hook_name}' not found")
                
                # Copy hook files
                hook_dest = self._get_hooks_dir() / hook_name
                ensure_directory(hook_dest)
                copy_files(hook_source, hook_dest)
                
                # Update settings.json
                self._add_hook_to_settings(hook_name)
                
                return InstallationResult(True, f"Hook '{hook_name}' installed successfully")
                
            except Exception as e:
                return InstallationResult(False, f"Failed to install hook '{hook_name}': {str(e)}")
                
        def uninstall_hook(self, hook_name: str) -> InstallationResult:
            """Uninstall a specific hook"""
            try:
                # Remove from settings
                self._remove_hook_from_settings(hook_name)
                
                # Remove hook directory
                hook_dir = self._get_hooks_dir() / hook_name
                if hook_dir.exists():
                    remove_directory(hook_dir)
                    
                return InstallationResult(True, f"Hook '{hook_name}' uninstalled successfully")
                
            except Exception as e:
                return InstallationResult(False, f"Failed to uninstall hook '{hook_name}': {str(e)}")
                
        def set_mode(self, mode: str) -> None:
            """Set installation mode (global/local)"""
            if mode in ["global", "local"]:
                self.mode = mode
                
        def _get_hooks_dir(self) -> Path:
            """Get hooks directory based on current mode"""
            if self.mode == "global":
                return CLAUDE_HOOKS_DIR
            else:
                return Path(".claude/hooks/ethpandaops")
                
        def _get_settings_path(self) -> Path:
            """Get settings file path based on current mode"""
            return self.global_settings if self.mode == "global" else self.local_settings
            
        def _get_installed_hooks(self, mode: str) -> List[str]:
            """Get list of installed hooks for given mode"""
            # Implementation to check settings.json files
            
        def _get_hook_info(self, hook_name: str) -> Dict[str, Any]:
            """Get information about a specific hook"""
            config_path = HOOKS_SOURCE / hook_name / "config.json"
            if config_path.exists():
                return read_json_file(config_path)
            return {}
            
        def _add_hook_to_settings(self, hook_name: str) -> None:
            """Add hook to settings.json"""
            # Implementation to modify settings.json
            
        def _remove_hook_from_settings(self, hook_name: str) -> None:
            """Remove hook from settings.json"""
            # Implementation to remove from settings.json
    ```
  - Exports: HooksInstaller class
  - Context: Handles interactive hooks installation, used by main menu

- [ ] **Task #9**: Create scripts installer
  - Folder: `src/pandaops_cookbook/installers/`
  - File: `scripts.py`
  - Imports:
    ```python
    from .base import BaseInstaller, InstallationResult
    from ..config.settings import SCRIPTS_SOURCE
    from ..utils.system import add_to_path, is_in_path
    from pathlib import Path
    from typing import Dict, Any, List
    ```
  - Implements:
    ```python
    class ScriptsInstaller(BaseInstaller):
        """Installer for scripts PATH configuration"""
        def __init__(self):
            super().__init__(
                name="Scripts",
                description="Add ethPandaOps scripts to system PATH"
            )
            
        def check_status(self) -> Dict[str, Any]:
            """Check if scripts are in PATH"""
            in_path = is_in_path(SCRIPTS_SOURCE)
            
            return {
                'installed': in_path,
                'scripts_path': str(SCRIPTS_SOURCE),
                'available_scripts': self._get_available_scripts()
            }
            
        def install(self) -> InstallationResult:
            """Add scripts directory to PATH"""
            try:
                if is_in_path(SCRIPTS_SOURCE):
                    return InstallationResult(True, "Scripts already in PATH")
                
                if add_to_path(SCRIPTS_SOURCE):
                    return InstallationResult(True, "Scripts added to PATH successfully")
                else:
                    return InstallationResult(False, "Failed to add scripts to PATH")
                    
            except Exception as e:
                return InstallationResult(False, f"Installation failed: {str(e)}")
                
        def uninstall(self) -> InstallationResult:
            """Remove scripts from PATH (manual operation)"""
            return InstallationResult(
                True, 
                "Scripts PATH removal requires manual editing of shell profile"
            )
            
        def get_details(self) -> Dict[str, Any]:
            """Get detailed information about scripts"""
            scripts = []
            for script_file in SCRIPTS_SOURCE.glob("*.py"):
                scripts.append({
                    'name': script_file.stem,
                    'file': script_file.name,
                    'path': str(script_file),
                    'executable': script_file.is_file() and script_file.stat().st_mode & 0o111
                })
                
            return {
                'scripts': scripts,
                'scripts_path': str(SCRIPTS_SOURCE),
                'in_path': is_in_path(SCRIPTS_SOURCE)
            }
            
        def _get_available_scripts(self) -> List[str]:
            """Get list of available script files"""
            return [f.name for f in SCRIPTS_SOURCE.glob("*.py")]
    ```
  - Exports: ScriptsInstaller class
  - Context: Handles scripts PATH configuration, used by main menu

#### Group E: Application Layer (Execute all in parallel after Group D)
- [ ] **Task #10**: Create command-line interface handler
  - Folder: `src/pandaops_cookbook/`
  - File: `cli.py`
  - Imports:
    ```python
    import argparse
    from typing import Optional, List
    from .installers.commands import CommandsInstaller
    from .installers.code_standards import CodeStandardsInstaller
    from .installers.hooks import HooksInstaller
    from .installers.scripts import ScriptsInstaller
    from .config.settings import VERSION, APP_NAME
    ```
  - Implements:
    ```python
    class CLIHandler:
        """Handle command-line interface"""
        def __init__(self):
            self.installers = {
                'commands': CommandsInstaller(),
                'code-standards': CodeStandardsInstaller(),
                'hooks': HooksInstaller(),
                'scripts': ScriptsInstaller()
            }
            
        def create_parser(self) -> argparse.ArgumentParser:
            """Create argument parser"""
            parser = argparse.ArgumentParser(
                prog=APP_NAME,
                description="ethPandaOps AI Cookbook unified installer",
                formatter_class=argparse.RawDescriptionHelpFormatter
            )
            
            parser.add_argument('--version', action='version', version=f'{APP_NAME} {VERSION}')
            
            subparsers = parser.add_subparsers(dest='command', help='Available commands')
            
            # Install command
            install_parser = subparsers.add_parser('install', help='Install components')
            install_parser.add_argument('component', 
                                      choices=['commands', 'code-standards', 'hooks', 'scripts', 'all'],
                                      help='Component to install')
            install_parser.add_argument('--hook', help='Specific hook to install (for hooks component)')
            install_parser.add_argument('--mode', choices=['global', 'local'], default='global',
                                      help='Installation mode (for hooks)')
            
            # Uninstall command
            uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall components')
            uninstall_parser.add_argument('component',
                                        choices=['commands', 'code-standards', 'hooks', 'scripts', 'all'],
                                        help='Component to uninstall')
            uninstall_parser.add_argument('--hook', help='Specific hook to uninstall (for hooks component)')
            uninstall_parser.add_argument('--mode', choices=['global', 'local'], default='global',
                                        help='Installation mode (for hooks)')
            
            # Status command
            status_parser = subparsers.add_parser('status', help='Check installation status')
            status_parser.add_argument('component', nargs='?',
                                     choices=['commands', 'code-standards', 'hooks', 'scripts'],
                                     help='Component to check (default: all)')
            
            # List command
            list_parser = subparsers.add_parser('list', help='List available components')
            list_parser.add_argument('component', nargs='?',
                                   choices=['commands', 'code-standards', 'hooks', 'scripts'],
                                   help='Component to list (default: all)')
            
            return parser
            
        def handle_install(self, args) -> int:
            """Handle install command"""
            if args.component == 'all':
                return self._install_all()
            else:
                installer = self.installers.get(args.component)
                if not installer:
                    print(f"Unknown component: {args.component}")
                    return 1
                    
                # Special handling for hooks
                if args.component == 'hooks' and args.hook:
                    if hasattr(installer, 'set_mode'):
                        installer.set_mode(args.mode)
                    result = installer.install_hook(args.hook)
                else:
                    result = installer.install()
                    
                print(result.message)
                return 0 if result.success else 1
                
        def handle_uninstall(self, args) -> int:
            """Handle uninstall command"""
            # Similar to install but for uninstall
            
        def handle_status(self, args) -> int:
            """Handle status command"""
            if args.component:
                installer = self.installers.get(args.component)
                if installer:
                    status = installer.check_status()
                    print(f"{installer.name}: {installer.get_status_string()}")
                    return 0
                else:
                    print(f"Unknown component: {args.component}")
                    return 1
            else:
                # Show status for all components
                for name, installer in self.installers.items():
                    status = installer.check_status()
                    print(f"{installer.name}: {installer.get_status_string()}")
                return 0
                
        def handle_list(self, args) -> int:
            """Handle list command"""
            # Implementation for listing available components
            
        def _install_all(self) -> int:
            """Install all components"""
            success_count = 0
            for name, installer in self.installers.items():
                result = installer.install()
                print(f"{installer.name}: {result.message}")
                if result.success:
                    success_count += 1
                    
            print(f"\nInstalled {success_count}/{len(self.installers)} components successfully")
            return 0 if success_count == len(self.installers) else 1
            
        def run(self, args: Optional[List[str]] = None) -> int:
            """Run CLI with given arguments"""
            parser = self.create_parser()
            parsed_args = parser.parse_args(args)
            
            if parsed_args.command == 'install':
                return self.handle_install(parsed_args)
            elif parsed_args.command == 'uninstall':
                return self.handle_uninstall(parsed_args)
            elif parsed_args.command == 'status':
                return self.handle_status(parsed_args)
            elif parsed_args.command == 'list':
                return self.handle_list(parsed_args)
            else:
                # No command provided, launch interactive mode
                return self._launch_interactive()
                
        def _launch_interactive(self) -> int:
            """Launch interactive mode"""
            from .main import run_interactive
            return run_interactive()
    ```
  - Exports: CLIHandler class for command-line interface
  - Context: Entry point for non-interactive usage

- [ ] **Task #11**: Create main application entry point
  - Folder: `src/pandaops_cookbook/`
  - File: `main.py`
  - Imports:
    ```python
    import sys
    from typing import Optional
    from .ui.terminal import TerminalController
    from .ui.menu import InteractiveMenu, MenuOption
    from .ui.components import MessageBox
    from .installers.commands import CommandsInstaller
    from .installers.code_standards import CodeStandardsInstaller
    from .installers.hooks import HooksInstaller
    from .installers.scripts import ScriptsInstaller
    from .config.settings import APP_NAME, VERSION
    ```
  - Implements:
    ```python
    def create_main_menu(terminal: TerminalController) -> InteractiveMenu:
        """Create the main menu"""
        installers = {
            'commands': CommandsInstaller(),
            'code-standards': CodeStandardsInstaller(),
            'hooks': HooksInstaller(),
            'scripts': ScriptsInstaller()
        }
        
        options = []
        for key, installer in installers.items():
            option = MenuOption(
                name=installer.name,
                description=installer.description,
                action=lambda i=installer: launch_installer_menu(i, terminal),
                status_checker=lambda i=installer: i.get_status_string()
            )
            options.append(option)
            
        # Add utility options
        options.append(MenuOption(
            name="Install All",
            description="Install all components",
            action=lambda: install_all_components(installers, terminal)
        ))
        
        options.append(MenuOption(
            name="Show Status",
            description="Show installation status for all components",
            action=lambda: show_all_status(installers, terminal)
        ))
        
        return InteractiveMenu(f"{APP_NAME} v{VERSION}", options, terminal)
        
    def launch_installer_menu(installer, terminal: TerminalController) -> None:
        """Launch installer-specific menu"""
        if hasattr(installer, 'get_interactive_options'):
            # For interactive installers like hooks
            options = []
            for opt in installer.get_interactive_options():
                options.append(MenuOption(
                    name=opt['name'],
                    description=opt['description'],
                    action=opt['action'],
                    status_checker=opt.get('status_checker')
                ))
            
            submenu = InteractiveMenu(installer.name, options, terminal)
            submenu.run()
        else:
            # For simple installers
            if installer.is_installed():
                if MessageBox.confirm(f"Uninstall {installer.name}?"):
                    result = installer.uninstall()
                    MessageBox.success(result.message) if result.success else MessageBox.error(result.message)
            else:
                if MessageBox.confirm(f"Install {installer.name}?"):
                    result = installer.install()
                    MessageBox.success(result.message) if result.success else MessageBox.error(result.message)
                    
    def install_all_components(installers: dict, terminal: TerminalController) -> None:
        """Install all components"""
        if not MessageBox.confirm("Install all components?"):
            return
            
        results = []
        for name, installer in installers.items():
            result = installer.install()
            results.append((installer.name, result))
            
        # Show results
        success_count = sum(1 for _, result in results if result.success)
        MessageBox.info(f"Installation complete: {success_count}/{len(results)} successful")
        
    def show_all_status(installers: dict, terminal: TerminalController) -> None:
        """Show status for all components"""
        terminal.clear_screen()
        print(f"\n{APP_NAME} v{VERSION} - Installation Status\n")
        
        for name, installer in installers.items():
            status = installer.get_status_string()
            status_color = "GREEN" if installer.is_installed() else "RED"
            print(f"  {installer.name}: {status}")
            
        print("\nPress any key to continue...")
        terminal.getch()
        
    def run_interactive() -> int:
        """Run interactive mode"""
        terminal = TerminalController()
        
        try:
            terminal.setup_terminal()
            main_menu = create_main_menu(terminal)
            main_menu.run()
            return 0
            
        except KeyboardInterrupt:
            print("\nExiting...")
            return 0
        except Exception as e:
            MessageBox.error(f"Error: {str(e)}")
            return 1
        finally:
            terminal.restore_terminal()
            
    def main() -> int:
        """Main entry point"""
        from .cli import CLIHandler
        
        if len(sys.argv) > 1:
            # Command-line mode
            cli = CLIHandler()
            return cli.run()
        else:
            # Interactive mode
            return run_interactive()
            
    if __name__ == "__main__":
        sys.exit(main())
    ```
  - Exports: main() function and interactive menu system
  - Context: Primary entry point for the application

#### Group F: Distribution and Setup (Execute all in parallel after Group E)
- [ ] **Task #12**: Create package setup configuration
  - Folder: `src/`
  - File: `setup.py`
  - Implements:
    ```python
    from setuptools import setup, find_packages
    from pathlib import Path
    
    # Read version from package
    version_file = Path(__file__).parent / "pandaops_cookbook" / "__init__.py"
    version_line = next(line for line in version_file.read_text().splitlines() if line.startswith("__version__"))
    version = version_line.split("=")[1].strip().strip('"\'')
    
    # Read README
    readme_file = Path(__file__).parent.parent / "README.md"
    long_description = readme_file.read_text() if readme_file.exists() else ""
    
    setup(
        name="ai-cookbook",
        version=version,
        author="ethPandaOps",
        author_email="info@ethpandaops.io",
        description="Unified installation system for ethPandaOps AI cookbook",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/ethpandaops/ai-cookbook",
        packages=find_packages(),
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Tools",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
        ],
        python_requires=">=3.8",
        install_requires=[
            # No external dependencies - uses only Python standard library
        ],
        entry_points={
            "console_scripts": [
                "ai-cookbook=pandaops_cookbook.main:main",
            ],
        },
        include_package_data=True,
        package_data={
            "pandaops_cookbook": ["config/*"],
        },
    )
    ```
  - Exports: Package configuration for pip installation
  - Context: Enables pip install and entry point creation

- [ ] **Task #13**: Update setup.sh for simplified installation
  - Folder: Root directory
  - File: `setup.sh`
  - Implements:
    ```bash
    #!/bin/bash
    set -e
    
    # Colors for output
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
    
    # Functions
    print_success() {
        echo -e "${GREEN}✓${NC} $1"
    }
    
    print_error() {
        echo -e "${RED}✗${NC} $1"
    }
    
    print_info() {
        echo -e "${YELLOW}ℹ${NC} $1"
    }
    
    # Check if we're in the right directory
    if [ ! -f "setup.py" ] || [ ! -d "src/pandaops_cookbook" ]; then
        print_error "This script must be run from the root of the ai-cookbook repository"
        exit 1
    fi
    
    # Check Python version
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        print_error "Python 3.8 or higher is required"
        exit 1
    fi
    
    print_info "Installing ai-cookbook..."
    
    # Install package in development mode
    pip3 install -e ./src/
    
    if [ $? -eq 0 ]; then
        print_success "ai-cookbook installed successfully!"
        echo ""
        print_info "You can now run: ai-cookbook"
        print_info "Or use command-line options: ai-cookbook --help"
        echo ""
        print_info "The interactive installer provides the following options:"
        echo "  • Claude Commands - AI-assisted development commands"
        echo "  • Code Standards - Language-specific coding standards"
        echo "  • Hooks - Automated formatting and linting"
        echo "  • Scripts - Add utility scripts to PATH"
        echo ""
        print_info "Run 'ai-cookbook' to get started!"
    else
        print_error "Installation failed"
        exit 1
    fi
    ```
  - Exports: Simplified installation script
  - Context: Single entry point for users to install the unified system

- [ ] **Task #14**: Update documentation
  - Folder: Root directory
  - File: `README.md` (update existing)
  - Implements:
    ```markdown
    # ethPandaOps AI Cookbook
    
    A comprehensive toolkit for AI-assisted development workflows.
    
    ## Quick Start
    
    ```bash
    # Install the unified installer
    ./setup.sh
    
    # Run interactive installer
    ai-cookbook
    
    # Or use command-line interface
    ai-cookbook install all
    ```
    
    ## Features
    
    ### Claude Commands
    Install AI-assisted development commands:
    - `/prime-context` - Read and understand project context
    - `/create-implementation-plan` - Generate detailed implementation plans
    - `/init-project-ai-docs` - Initialize AI documentation
    - And 9 more productivity commands
    
    ### Code Standards
    Language-specific coding standards that Claude automatically applies:
    - **Go**: Comprehensive standards for dependencies, architecture, testing
    - **Python**: Python-specific best practices
    - **Rust**: Memory safety, async/await, error handling
    - **Tailwind CSS**: v4 migration and best practices
    
    ### Hooks
    Automated formatting and linting:
    - **ESLint**: JavaScript/TypeScript formatting
    - **gofmt**: Go code formatting
    - **golangci-lint**: Go linting
    - **TypeScript**: TypeScript formatting
    
    ### Scripts
    Utility scripts for development:
    - `init-ai-docs.py` - AI documentation generator
    - `install-hooks.py` - Legacy hooks installer
    
    ## Installation Options
    
    ### Interactive Mode
    ```bash
    ai-cookbook
    ```
    
    Navigate with arrow keys, press Enter to install/uninstall, 'q' to quit.
    
    ### Command Line
    ```bash
    # Install specific components
    ai-cookbook install commands
    ai-cookbook install code-standards
    ai-cookbook install hooks --hook gofmt --mode global
    ai-cookbook install scripts
    
    # Install everything
    ai-cookbook install all
    
    # Check status
    ai-cookbook status
    
    # List available components
    ai-cookbook list
    ```
    
    ## Migration from Old Scripts
    
    If you previously used the separate installation scripts:
    - `./setup.sh` → `ai-cookbook install commands`
    - `./install-code-standards.sh` → `ai-cookbook install code-standards`
    - `./scripts/install-hooks.py` → `ai-cookbook install hooks`
    
    The unified installer provides the same functionality with better organization.
    
    ## Development
    
    ### Project Structure
    ```
    src/pandaops_cookbook/
    ├── main.py              # Main application entry point
    ├── cli.py               # Command-line interface
    ├── ui/                  # Terminal UI components
    ├── installers/          # Installation modules
    ├── utils/               # Utility functions
    └── config/              # Configuration and settings
    ```
    
    ### Adding New Installers
    1. Create new installer class inheriting from `BaseInstaller`
    2. Implement required methods: `check_status()`, `install()`, `uninstall()`, `get_details()`
    3. Add to main menu in `main.py`
    
    ## Requirements
    
    - Python 3.8+
    - No external dependencies (uses only Python standard library)
    - Claude Code CLI (for commands to work)
    
    ## License
    
    MIT License - see LICENSE file for details.
    ```
  - Exports: Updated documentation reflecting unified installer
  - Context: User-facing documentation for the new system

---

## Implementation Workflow

This plan file serves as the authoritative checklist for implementation. When implementing:

### Required Process
1. **Load Plan**: Read this entire plan file before starting
2. **Sync Tasks**: Create TodoWrite tasks matching the checkboxes below
3. **Execute & Update**: For each task:
   - Mark TodoWrite as `in_progress` when starting
   - Update checkbox `[ ]` to `[x]` when completing
   - Mark TodoWrite as `completed` when done
4. **Maintain Sync**: Keep this file and TodoWrite synchronized throughout

### Critical Rules
- This plan file is the source of truth for progress
- Update checkboxes in real-time as work progresses
- Never lose synchronization between plan file and TodoWrite
- Mark tasks complete only when fully implemented (no placeholders)
- Tasks should be run in parallel, unless there are dependencies, using subtasks, to avoid context bloat.

### Progress Tracking
The checkboxes above represent the authoritative status of each task. Keep them updated as you work.