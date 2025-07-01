#!/usr/bin/env python3
"""
Claude Code Hooks Setup
Install and manage hooks for Claude Code
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import tempfile
import termios
import tty
import select
import signal

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    WHITE = '\033[1;37m'
    GRAY = '\033[0;90m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    REVERSE = '\033[7m'
    CLEAR_LINE = '\033[2K'
    MOVE_UP = '\033[A'
    HIDE_CURSOR = '\033[?25l'
    SHOW_CURSOR = '\033[?25h'

# Configuration paths
SCRIPT_DIR = Path(__file__).parent.parent.absolute()
HOOKS_DIR = SCRIPT_DIR / "claude-code" / "hooks"

# Global configuration
CLAUDE_DIR = Path.home() / ".claude"
CLAUDE_CONFIG_FILE = CLAUDE_DIR / "settings.json"
USER_HOOKS_DIR = CLAUDE_DIR / "hooks" / "ethpandaops"

# Local configuration
LOCAL_CLAUDE_DIR = Path.cwd() / ".claude"
LOCAL_CONFIG_FILE = LOCAL_CLAUDE_DIR / "settings.json"
LOCAL_HOOKS_DIR = LOCAL_CLAUDE_DIR / "hooks" / "ethpandaops"

# Installation mode
class InstallMode:
    GLOBAL = "global"
    LOCAL = "local"

# Global flag for terminal resize
terminal_resized = False

def handle_resize(signum, frame):
    """Handle terminal resize signal"""
    global terminal_resized
    terminal_resized = True

# Set up signal handler for terminal resize
signal.signal(signal.SIGWINCH, handle_resize)

def get_paths(mode: str = InstallMode.GLOBAL):
    """Get configuration paths based on installation mode"""
    if mode == InstallMode.LOCAL:
        return LOCAL_CLAUDE_DIR, LOCAL_CONFIG_FILE, LOCAL_HOOKS_DIR
    else:
        return CLAUDE_DIR, CLAUDE_CONFIG_FILE, USER_HOOKS_DIR

def log(message: str):
    """Log a message with blue prefix"""
    print(f"{Colors.BLUE}[HOOKS]{Colors.NC} {message}")

def success(message: str):
    """Log a success message with green prefix"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def warn(message: str):
    """Log a warning message with yellow prefix"""
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {message}")

def error(message: str):
    """Log an error message with red prefix"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def info(message: str):
    """Log an info message with cyan prefix"""
    print(f"{Colors.CYAN}[INFO]{Colors.NC} {message}")

def backup_settings(mode: str = InstallMode.GLOBAL, quiet: bool = False):
    """Backup settings.json file"""
    claude_dir, config_file, _ = get_paths(mode)
    if config_file.exists():
        backup_dir = claude_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"settings.json.backup.{timestamp}"
        shutil.copy2(config_file, backup_file)
        if not quiet:
            log(f"Created backup: {backup_file}")

def check_dependencies() -> bool:
    """Check if jq is installed"""
    try:
        subprocess.run(["jq", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        error("jq is required but not installed")
        print("Install jq:")
        print("  macOS:    brew install jq")
        print("  Ubuntu:   sudo apt-get install jq")
        print("  Fedora:   sudo dnf install jq")
        return False

def get_available_hooks() -> List[str]:
    """Get list of available hooks"""
    hooks = []
    if HOOKS_DIR.exists():
        for hook_dir in HOOKS_DIR.iterdir():
            if hook_dir.is_dir():
                config_file = hook_dir / "config.json"
                hook_script = hook_dir / "hook.sh"
                if config_file.exists() and hook_script.exists():
                    hooks.append(hook_dir.name)
    return sorted(hooks)

def get_hook_info(hook_name: str) -> str:
    """Get hook description from config.json"""
    config_file = HOOKS_DIR / hook_name / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('description', 'No description available')
        except Exception:
            pass
    return "No description available"

def check_hook_dependencies(hook_name: str) -> Tuple[bool, str]:
    """Check if hook dependencies are met"""
    deps_script = HOOKS_DIR / hook_name / "deps.sh"
    if deps_script.exists():
        try:
            result = subprocess.run(
                ["bash", str(deps_script)],
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    return True, ""

def install_hook(hook_name: str, mode: str = InstallMode.GLOBAL, quiet: bool = False) -> bool:
    """Install a specific hook"""
    claude_dir, config_file, hooks_dir = get_paths(mode)
    
    hook_dir = HOOKS_DIR / hook_name
    hook_config = hook_dir / "config.json"
    hook_script = hook_dir / "hook.sh"
    
    # Validate hook files
    if not hook_script.exists():
        error(f"Hook '{hook_name}' missing hook.sh")
        return False
    
    if not hook_config.exists():
        error(f"Hook '{hook_name}' missing config.json")
        return False
    
    # Check dependencies
    deps_ok, deps_msg = check_hook_dependencies(hook_name)
    if not deps_ok:
        error(f"Dependencies not met for {hook_name}")
        if deps_msg:
            print(deps_msg)
        return False
    
    # Create directories
    claude_dir.mkdir(exist_ok=True)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize settings.json if needed
    if not config_file.exists():
        with open(config_file, 'w') as f:
            json.dump({"hooks": {}}, f, indent=2)
        if not quiet:
            log(f"Created new settings.json in {mode} mode")
    
    # Backup current settings
    backup_settings(mode=mode, quiet=quiet)
    
    # Copy hook script
    installed_hook_path = hooks_dir / f"{hook_name}.sh"
    shutil.copy2(hook_script, installed_hook_path)
    installed_hook_path.chmod(0o755)
    
    # Read hook configuration
    with open(hook_config, 'r') as f:
        config = json.load(f)
    
    hook_type = config.get('hook_type', 'PostToolUse')
    matcher = config.get('matcher', '')
    
    # Update settings.json
    with open(config_file, 'r') as f:
        settings = json.load(f)
    
    # Ensure hooks structure exists
    if 'hooks' not in settings:
        settings['hooks'] = {}
    if hook_type not in settings['hooks']:
        settings['hooks'][hook_type] = []
    
    # Remove existing entry for this hook
    settings['hooks'][hook_type] = [
        entry for entry in settings['hooks'][hook_type]
        if not any(hook_name in h.get('command', '') for h in entry.get('hooks', []))
    ]
    
    # Add new hook configuration
    new_entry = {
        "matcher": matcher,
        "hooks": [{
            "type": "command",
            "command": str(installed_hook_path)
        }]
    }
    settings['hooks'][hook_type].append(new_entry)
    
    # Write updated settings
    with open(config_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    if not quiet:
        success(f"Installed hook: {hook_name} ({mode})")
        info(f"Hook location: {installed_hook_path}")
    return True

def uninstall_hook(hook_name: str, mode: str = InstallMode.GLOBAL, quiet: bool = False) -> bool:
    """Uninstall a specific hook"""
    _, config_file, hooks_dir = get_paths(mode)
    installed_hook_path = hooks_dir / f"{hook_name}.sh"
    
    if not config_file.exists():
        if not quiet:
            warn(f"No settings.json found in {mode} mode")
        return True
    
    # Backup current settings
    backup_settings(mode=mode, quiet=quiet)
    
    # Remove from settings.json
    with open(config_file, 'r') as f:
        settings = json.load(f)
    
    if 'hooks' in settings:
        for hook_type, entries in settings['hooks'].items():
            settings['hooks'][hook_type] = [
                entry for entry in entries
                if not any(hook_name in h.get('command', '') for h in entry.get('hooks', []))
            ]
        
        # Remove empty hook type arrays
        settings['hooks'] = {k: v for k, v in settings['hooks'].items() if v}
    
    # Write updated settings
    with open(config_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    # Remove hook script
    if installed_hook_path.exists():
        installed_hook_path.unlink()
        if not quiet:
            log(f"Removed hook script: {installed_hook_path}")
    
    if not quiet:
        success(f"Uninstalled hook: {hook_name} ({mode})")
    return True

def uninstall_all_hooks():
    """Uninstall all hooks"""
    if not CLAUDE_CONFIG_FILE.exists():
        warn("No settings.json found")
        return
    
    log("Uninstalling all hooks...")
    print()
    
    # Get list of installed hooks
    installed_hooks = get_installed_hooks()
    
    if not installed_hooks:
        warn("No hooks to uninstall")
        return
    
    # Uninstall each hook
    for hook in installed_hooks:
        log(f"Uninstalling {hook}...")
        uninstall_hook(hook)
        print()
    
    # Clean up hooks directory if empty
    if USER_HOOKS_DIR.exists() and not any(USER_HOOKS_DIR.iterdir()):
        USER_HOOKS_DIR.rmdir()
    
    success("All hooks uninstalled")

def get_installed_hooks(mode: str = InstallMode.GLOBAL) -> List[str]:
    """Get list of installed hooks"""
    _, config_file, _ = get_paths(mode)
    
    if not config_file.exists():
        return []
    
    installed = set()
    with open(config_file, 'r') as f:
        settings = json.load(f)
    
    if 'hooks' in settings:
        for entries in settings['hooks'].values():
            for entry in entries:
                for hook in entry.get('hooks', []):
                    command = hook.get('command', '')
                    if '/ethpandaops/' in command:
                        hook_name = Path(command).stem
                        installed.add(hook_name)
    
    return sorted(list(installed))

def list_installed_hooks(mode: str = None):
    """List all installed hooks"""
    available_hooks = get_available_hooks()
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}Hooks{Colors.NC}")
    print(f"{Colors.DIM}{'─' * 5}{Colors.NC}")
    
    if not available_hooks:
        print(f"  {Colors.DIM}No hooks available{Colors.NC}")
        return
    
    # Get installed hooks for both modes if mode not specified
    if mode is None:
        global_hooks = get_installed_hooks(InstallMode.GLOBAL)
        local_hooks = get_installed_hooks(InstallMode.LOCAL)
    else:
        # If mode specified, only check that mode
        if mode == InstallMode.GLOBAL:
            global_hooks = get_installed_hooks(InstallMode.GLOBAL)
            local_hooks = []
        else:
            global_hooks = []
            local_hooks = get_installed_hooks(InstallMode.LOCAL)
    
    # Display each hook with its status
    for hook in available_hooks:
        desc = get_hook_info(hook)
        if len(desc) > 50:
            desc = desc[:47] + "..."
        
        # Determine installation status
        is_global = hook in global_hooks
        is_local = hook in local_hooks
        
        if is_global and is_local:
            # Installed in both
            status = f"{Colors.GREEN}[global, local]{Colors.NC}"
            hook_display = f"{Colors.GREEN}{hook}{Colors.NC}"
        elif is_global:
            # Only global
            status = f"{Colors.GREEN}[global]{Colors.NC}"
            hook_display = f"{Colors.GREEN}{hook}{Colors.NC}"
        elif is_local:
            # Only local
            status = f"{Colors.GREEN}[local]{Colors.NC}"
            hook_display = f"{Colors.GREEN}{hook}{Colors.NC}"
        else:
            # Not installed
            status = f"{Colors.GRAY}[not installed]{Colors.NC}"
            hook_display = f"{hook}"
        
        print(f"  {hook_display:<15} {status:<25} {Colors.DIM}{desc}{Colors.NC}")
    
    # Add blank line at the end
    print()

def show_hook_details(hook_name: str):
    """Show detailed information about a hook"""
    hook_dir = HOOKS_DIR / hook_name
    hook_config = hook_dir / "config.json"
    
    if not hook_config.exists():
        error(f"Hook '{hook_name}' not found")
        return
    
    with open(hook_config, 'r') as f:
        config = json.load(f)
    
    desc = config.get('description', 'No description')
    hook_type = config.get('hook_type', 'PostToolUse')
    matcher = config.get('matcher', 'No matcher')
    
    print()
    # Hook name as main heading
    print(f"{Colors.BOLD}{Colors.GREEN}{hook_name}{Colors.NC}")
    print(f"{Colors.DIM}{'─' * len(hook_name)}{Colors.NC}")
    
    # Description
    print(f"\n{Colors.CYAN}Description:{Colors.NC}")
    print(f"  {desc}")
    
    # Hook type
    print(f"\n{Colors.CYAN}Hook Type:{Colors.NC}")
    print(f"  {hook_type}")
    
    # Matcher
    print(f"\n{Colors.CYAN}Matcher:{Colors.NC}")
    print(f"  {matcher}")
    
    # Script path
    print(f"\n{Colors.CYAN}Script:{Colors.NC}")
    print(f"  file://{hook_dir}/hook.sh")
    
    # Check dependencies
    deps_script = hook_dir / "deps.sh"
    if deps_script.exists():
        print(f"\n{Colors.CYAN}Dependencies:{Colors.NC}")
        deps_ok, _ = check_hook_dependencies(hook_name)
        if deps_ok:
            print(f"  {Colors.GREEN}✓{Colors.NC} All dependencies met")
        else:
            print(f"  {Colors.YELLOW}⚠{Colors.NC}  Missing dependencies (run deps.sh for details)")
            print(f"  → file://{deps_script}")
    
    # Check if installed
    global_installed = hook_name in get_installed_hooks(InstallMode.GLOBAL)
    local_installed = hook_name in get_installed_hooks(InstallMode.LOCAL)
    
    print(f"\n{Colors.CYAN}Status:{Colors.NC}")
    if global_installed and local_installed:
        print(f"  {Colors.GREEN}✓{Colors.NC} Installed (both global and local)")
    elif global_installed:
        print(f"  {Colors.GREEN}✓{Colors.NC} Installed (global)")
    elif local_installed:
        print(f"  {Colors.GREEN}✓{Colors.NC} Installed (local)")
    else:
        print(f"  {Colors.YELLOW}○{Colors.NC} Not installed")
    
    # Add blank line at the end
    print()

def getch(timeout=None):
    """Get a single character from stdin with optional timeout"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        
        # Check if input is available
        if timeout is not None:
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if not rlist:
                return None
        
        ch = sys.stdin.read(1)
        # Handle arrow keys (they send escape sequences)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
                elif ch3 == 'C':
                    return 'RIGHT'
                elif ch3 == 'D':
                    return 'LEFT'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def select_install_mode() -> str:
    """Ask user to select installation mode"""
    global terminal_resized
    selected = 0  # Default to global
    force_redraw = True
    
    try:
        while True:
            # Check if terminal was resized
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
            
            if force_redraw:
                # Clear screen and draw menu
                print(Colors.HIDE_CURSOR)
                print("\033[2J\033[H", end='')  # Clear screen
                
                print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 Select Installation Mode{Colors.NC}\n")
                
                # Global option
                if selected == 0:
                    print(f"{Colors.REVERSE}{Colors.BOLD} ► Global {Colors.NC}")
                    print(f"   {Colors.GREEN}Install hooks for all projects{Colors.NC}")
                    print(f"   {Colors.DIM}~/.claude/{Colors.NC}")
                else:
                    print(f"   {Colors.BOLD}Global{Colors.NC}")
                    print(f"   {Colors.DIM}Install hooks for all projects{Colors.NC}")
                    print(f"   {Colors.DIM}~/.claude/{Colors.NC}")
                
                print()
                
                # Local option
                if selected == 1:
                    print(f"{Colors.REVERSE}{Colors.BOLD} ► Local {Colors.NC}")
                    print(f"   {Colors.BLUE}Install hooks for current directory only{Colors.NC}")
                    print(f"   {Colors.DIM}.claude/ (in {Path.cwd().name}){Colors.NC}")
                else:
                    print(f"   {Colors.BOLD}Local{Colors.NC}")
                    print(f"   {Colors.DIM}Install hooks for current directory only{Colors.NC}")
                    print(f"   {Colors.DIM}.claude/ (in {Path.cwd().name}){Colors.NC}")
                
                print()
                print(f"\n{Colors.DIM}↑/↓: Navigate  ENTER: Select  q: Quit{Colors.NC}")
                
                force_redraw = False
            
            # Get user input with timeout
            key = getch(timeout=0.1)
            
            if key is None:
                # Timeout - check if we need to redraw due to resize
                if terminal_resized:
                    continue
            elif key == 'q' or key == '\x03':  # q or Ctrl+C
                print(Colors.SHOW_CURSOR)
                sys.exit(0)
            elif key == 'UP' and selected > 0:
                selected = 0
                force_redraw = True
            elif key == 'DOWN' and selected < 1:
                selected = 1
                force_redraw = True
            elif key == '\r' or key == '\n':  # Enter
                return InstallMode.GLOBAL if selected == 0 else InstallMode.LOCAL
            elif key == '1':
                return InstallMode.GLOBAL
            elif key == '2':
                return InstallMode.LOCAL
                    
    except KeyboardInterrupt:
        print(Colors.SHOW_CURSOR)
        sys.exit(0)
    except Exception:
        print(Colors.SHOW_CURSOR)
        sys.exit(0)

def draw_menu(hooks: List[str], selected: int, installed_hooks: List[str], mode: str, show_details: bool = False):
    """Draw the interactive menu"""
    print(Colors.HIDE_CURSOR, end='')
    
    # Clear screen and reset cursor
    print("\033[2J\033[H", end='')
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 ethPandaOps Claude Code Hooks Installer{Colors.NC}")
    mode_display = f"{Colors.GREEN}[GLOBAL]{Colors.NC}" if mode == InstallMode.GLOBAL else f"{Colors.BLUE}[LOCAL: {Path.cwd().name}]{Colors.NC}"
    print(f"Mode: {mode_display}\n")
    
    # Hooks list
    for i, hook in enumerate(hooks):
        is_selected = i == selected
        is_installed = hook in installed_hooks
        
        # Hook name and description
        desc = get_hook_info(hook)
        if len(desc) > 50:
            desc = desc[:47] + "..."
        
        # Selection indicator
        if is_selected:
            # Same reverse style for both installed and uninstalled when selected
            if is_installed:
                # Show checkmark outside reverse, and [INSTALLED] in green after reverse
                print(f" {Colors.GREEN}✓{Colors.NC} {Colors.REVERSE}{hook:<20} {desc:<50}{Colors.NC} {Colors.GREEN}[INSTALLED]{Colors.NC}")
            else:
                print(f"   {Colors.REVERSE}{hook:<20} {desc:<50}{Colors.NC} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
            
            if show_details:
                # Show additional details for selected hook
                hook_dir = HOOKS_DIR / hook
                
                # Get full description
                full_desc = get_hook_info(hook)
                print(f"\n{Colors.DIM}     Description: {Colors.NC}{full_desc}")
                print(f"{Colors.DIM}     Path: file://{hook_dir}/hook.sh{Colors.NC}")
                
                # Check dependencies
                deps_ok, _ = check_hook_dependencies(hook)
                if deps_ok:
                    print(f"{Colors.DIM}     Dependencies: {Colors.GREEN}✓ All met{Colors.NC}")
                else:
                    print(f"{Colors.DIM}     Dependencies: {Colors.YELLOW}⚠ Missing{Colors.NC}")
                print()
        else:
            if is_installed:
                # Not selected + installed: green checkmark, normal text
                print(f" {Colors.GREEN}✓{Colors.NC} {hook:<20} {desc:<50} {Colors.GREEN}[INSTALLED]{Colors.NC}")
            else:
                # Not selected + not installed: dimmed
                print(f"   {Colors.DIM}{hook:<20} {desc:<50} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
    
    # Add a bit of spacing before footer
    print()
    print()
    
    # Footer with action hint
    print(f"{Colors.DIM}────────────────────────────────────────────────────────────────────────{Colors.NC}")
    selected_hook = hooks[selected]
    if selected_hook in installed_hooks:
        print(f"{Colors.YELLOW}Press ENTER to uninstall '{selected_hook}'{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Press ENTER to install '{selected_hook}'{Colors.NC}")
    
    # Navigation instructions at the very bottom
    print(f"\n{Colors.DIM}↑/↓: Navigate  ENTER: Install/Uninstall  d: Details  a: Install All  r: Remove All  m: Change Mode  q: Quit{Colors.NC}")

def interactive_install():
    """Interactive hook installation with arrow key navigation"""
    global terminal_resized
    
    available_hooks = get_available_hooks()
    
    if not available_hooks:
        error("No hooks available to install")
        return
    
    # Ask for installation mode
    mode = select_install_mode()
    
    selected = 0
    show_details = False
    force_redraw = True
    
    try:
        clear_screen()
        while True:
            # Check if terminal was resized
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
                clear_screen()
            
            # Get current installed hooks
            installed_hooks = get_installed_hooks(mode)
            
            # Redraw menu if needed
            if force_redraw:
                draw_menu(available_hooks, selected, installed_hooks, mode, show_details)
                force_redraw = False
            
            # Get user input with short timeout to check for resize
            key = getch(timeout=0.1)
            
            if key is None:
                # Timeout - check if we need to redraw due to resize
                if terminal_resized:
                    continue
            elif key == 'q' or key == '\x03':  # q or Ctrl+C
                print(Colors.SHOW_CURSOR)
                return
            elif key == 'UP' and selected > 0:
                selected -= 1
                show_details = False
                force_redraw = True
            elif key == 'DOWN' and selected < len(available_hooks) - 1:
                selected += 1
                show_details = False
                force_redraw = True
            elif key == 'd':
                show_details = not show_details
                force_redraw = True
            elif key == 'm':  # Change mode
                mode = select_install_mode()
                clear_screen()
                force_redraw = True
            elif key == '\r' or key == '\n':  # Enter
                selected_hook = available_hooks[selected]
                
                if selected_hook in installed_hooks:
                    # Uninstall
                    uninstall_hook(selected_hook, mode=mode, quiet=True)
                else:
                    # Install
                    install_hook(selected_hook, mode=mode, quiet=True)
                force_redraw = True
            elif key == 'a':  # Install all
                for hook in available_hooks:
                    if hook not in installed_hooks:
                        install_hook(hook, mode=mode, quiet=True)
                force_redraw = True
            elif key == 'r':  # Remove all
                for hook in installed_hooks:
                    uninstall_hook(hook, mode=mode, quiet=True)
                force_redraw = True
    except KeyboardInterrupt:
        pass
    finally:
        print(Colors.SHOW_CURSOR)
        print()

def install_all_hooks():
    """Install all available hooks"""
    available_hooks = get_available_hooks()
    
    if not available_hooks:
        error("No hooks available to install")
        return
    
    log("Installing all available hooks...")
    print()
    
    for hook in available_hooks:
        log(f"Installing {hook}...")
        install_hook(hook)
        print()
    
    success("All hooks installed successfully")

def main():
    """Main entry point"""
    # Show initial banner only if not in interactive mode
    show_banner = len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help'])
    
    if show_banner:
        print()
        print("╔══════════════════════════════════════════════╗")
        print("║       🐼 ethPandaOps Claude Code Hooks       ║")
        print("╚══════════════════════════════════════════════╝")
        print()
        print("📁 Hooks location: ~/.claude/hooks/ethpandaops/")
        print("⚙️  Settings file:  ~/.claude/settings.json")
        print()
        print("⚠️  WARNING: Hooks execute code automatically.")
        print("   Always inspect before installing!")
        print()
    
    if not check_dependencies():
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description='Claude Code Hooks Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     Interactive mode
  %(prog)s --all               Install all hooks (asks for mode)
  %(prog)s --all --local       Install all hooks locally
  %(prog)s --install gofmt     Install specific hook (asks for mode)
  %(prog)s -i gofmt --global   Install hook globally
  %(prog)s --list              List all installed hooks
  %(prog)s --list --local      List local hooks only
  %(prog)s --uninstall gofmt   Uninstall specific hook
  %(prog)s --uninstall all     Uninstall all hooks
  %(prog)s --show gofmt        Show hook details
        """
    )
    
    parser.add_argument('-i', '--install', metavar='HOOK',
                        help='Install specific hook')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Install all available hooks')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List installed hooks')
    parser.add_argument('-u', '--uninstall', metavar='HOOK',
                        help='Uninstall hook (use "all" to uninstall all)')
    parser.add_argument('-s', '--show', metavar='HOOK',
                        help='Show hook details')
    parser.add_argument('-g', '--global', dest='mode', action='store_const', const='global',
                        help='Use global installation')
    parser.add_argument('-L', '--local', dest='mode', action='store_const', const='local',
                        help='Use local installation (current directory)')
    
    args = parser.parse_args()
    
    # Check if any arguments were provided
    if len(sys.argv) == 1:
        # No arguments - enter interactive mode
        interactive_install()
        return
    
    # Determine mode
    mode = None
    if args.mode:
        mode = InstallMode.GLOBAL if args.mode == 'global' else InstallMode.LOCAL
    
    # Validate and execute commands
    if args.list:
        list_installed_hooks(mode)
    elif args.show:
        # Validate hook exists
        available = get_available_hooks()
        if args.show not in available:
            error(f"Hook '{args.show}' not found")
            print(f"Available hooks: {', '.join(available)}")
            print()
            sys.exit(1)
        show_hook_details(args.show)
        print()
    elif args.uninstall:
        if args.uninstall == 'all':
            if mode is None:
                mode = select_install_mode()
            # Get all installed hooks for the mode
            installed = get_installed_hooks(mode)
            if not installed:
                warn(f"No hooks installed in {mode} mode")
                print()
                sys.exit(0)
            for hook in installed:
                uninstall_hook(hook, mode=mode)
            print()
        else:
            # Validate hook exists
            available = get_available_hooks()
            if args.uninstall not in available:
                error(f"Hook '{args.uninstall}' not found")
                print(f"Available hooks: {', '.join(available)}")
                print()
                sys.exit(1)
            
            if mode is None:
                # Check where hook is installed
                global_installed = args.uninstall in get_installed_hooks(InstallMode.GLOBAL)
                local_installed = args.uninstall in get_installed_hooks(InstallMode.LOCAL)
                
                if global_installed and local_installed:
                    # Installed in both - need to ask
                    error(f"Hook '{args.uninstall}' is installed in both global and local modes")
                    print("Please specify mode with --global or --local")
                    print()
                    sys.exit(1)
                elif global_installed:
                    mode = InstallMode.GLOBAL
                    info(f"Uninstalling '{args.uninstall}' from global mode")
                elif local_installed:
                    mode = InstallMode.LOCAL
                    info(f"Uninstalling '{args.uninstall}' from local mode")
                else:
                    warn(f"Hook '{args.uninstall}' is not installed")
                    print()
                    sys.exit(0)
            else:
                # Mode specified - check if actually installed
                if args.uninstall not in get_installed_hooks(mode):
                    warn(f"Hook '{args.uninstall}' is not installed in {mode} mode")
                    print()
                    sys.exit(0)
            
            uninstall_hook(args.uninstall, mode=mode)
            print()
    elif args.all:
        if mode is None:
            mode = select_install_mode()
        available_hooks = get_available_hooks()
        if not available_hooks:
            error("No hooks available to install")
            print()
            sys.exit(1)
        already_installed = 0
        for hook in available_hooks:
            if hook not in get_installed_hooks(mode):
                install_hook(hook, mode=mode)
            else:
                already_installed += 1
        if already_installed == len(available_hooks):
            info(f"All hooks already installed in {mode} mode")
        print()
    elif args.install:
        # Validate hook exists
        available = get_available_hooks()
        if args.install not in available:
            error(f"Hook '{args.install}' not found")
            print(f"Available hooks: {', '.join(available)}")
            print()
            sys.exit(1)
        
        if mode is None:
            # Check if already installed somewhere
            global_installed = args.install in get_installed_hooks(InstallMode.GLOBAL)
            local_installed = args.install in get_installed_hooks(InstallMode.LOCAL)
            
            if global_installed and local_installed:
                info(f"Hook '{args.install}' is already installed in both global and local modes")
                print()
                sys.exit(0)
            elif global_installed or local_installed:
                where = "global" if global_installed else "local"
                info(f"Hook '{args.install}' is already installed in {where} mode")
                print("Use --global or --local to install in the other mode")
                print()
                sys.exit(0)
            else:
                # Not installed anywhere - ask for mode
                mode = select_install_mode()
        else:
            # Check if already installed in specified mode
            if args.install in get_installed_hooks(mode):
                info(f"Hook '{args.install}' is already installed in {mode} mode")
                print()
                sys.exit(0)
        
        install_hook(args.install, mode=mode)
        print()
    else:
        # This shouldn't happen with argparse, but just in case
        parser.print_help()
        print()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Colors.SHOW_CURSOR)
        sys.exit(0)