#!/usr/bin/env python3
"""
Terminal UI for ai-cookbook - separate from click
"""

import os
import sys
import termios
import tty
import select
import signal
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any

from .config.settings import ORG_NAME, ORG_DISPLAY_NAME, VERSION
from .installers.commands import CommandsInstaller
from .installers.code_standards import CodeStandardsInstaller
from .installers.hooks import HooksInstaller
from .installers.scripts import ScriptsInstaller
from .installers.recommended import RecommendedToolsInstaller
from .installers.uninstall_all import UninstallAllInstaller

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
    REVERSE = '\033[7m'
    CLEAR_LINE = '\033[2K'
    HIDE_CURSOR = '\033[?25l'
    SHOW_CURSOR = '\033[?25h'

# Global state
terminal_resized = False

def signal_handler(signum: int, frame: Any) -> None:
    """Handle terminal resize"""
    global terminal_resized
    terminal_resized = True

# Set up signal handler for terminal resize
signal.signal(signal.SIGWINCH, signal_handler)

def getch(timeout=None):
    """Get a single character from stdin with optional timeout"""
    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
    except (OSError, termios.error):
        # Not a real terminal - fallback to regular input
        if timeout is not None:
            return None
        return sys.stdin.read(1)
    
    try:
        # Handle different Python versions
        if hasattr(tty, 'cbreak'):
            tty.cbreak(fd)
        else:
            tty.setcbreak(fd)
        
        if timeout is not None:
            # Use select to implement timeout
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                return None
        
        ch = sys.stdin.read(1)
        
        # Handle arrow keys and special characters
        if ch == '\x1b':  # ESC sequence
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

def clear_screen() -> None:
    """Clear the terminal screen"""
    print("\033[2J\033[H", end='')

def get_installers() -> Dict[str, Any]:
    """Get all installer instances"""
    return {
        'recommended': RecommendedToolsInstaller(),
        'commands': CommandsInstaller(),
        'code-standards': CodeStandardsInstaller(), 
        'hooks': HooksInstaller(),
        'scripts': ScriptsInstaller(),
        'uninstall': UninstallAllInstaller()
    }

def draw_base_menu(
    title: str,
    items: List[str],
    selected: int,
    get_item_status: Callable[[str], str],
    get_item_display: Callable[[str, bool], str],
    header_info: Optional[Dict[str, str]] = None,
    show_details: bool = False,
    detail_func: Optional[Callable[[str, bool], None]] = None
) -> None:
    """Base menu drawing function for all submenus.
    
    Args:
        title: Menu title to display
        items: List of items to display
        selected: Index of currently selected item
        get_item_status: Function to get status text for an item
        get_item_display: Function to get display text for an item
        header_info: Optional additional header information
        show_details: Whether to show details for selected item
        detail_func: Optional function to display item details
    """
    print(Colors.HIDE_CURSOR, end='')
    clear_screen()
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 {title}{Colors.NC}")
    
    # Additional header info
    if header_info:
        for key, value in header_info.items():
            print(f"{key}: {value}")
    
    print(f"Available Items: {len(items)}\n")
    
    # Draw items
    for i, item in enumerate(items):
        is_selected = i == selected
        status = get_item_status(item)
        display = get_item_display(item, is_selected)
        
        # Selection indicator and item display
        if is_selected:
            print(f"{Colors.CYAN}→{Colors.NC} {display} {status}")
            
            if show_details and detail_func:
                detail_func(item, True)
                print()
        else:
            print(f"  {display} {status}")

def draw_menu(installer_names: List[str], selected: int, installers: Dict[str, Any], show_details: bool = False) -> None:
    """Draw the interactive menu"""
    print(Colors.HIDE_CURSOR, end='')
    
    # Clear screen and reset cursor
    clear_screen()
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 {ORG_DISPLAY_NAME} AI Cookbook Installer{Colors.NC}")
    print(f"Version: {Colors.GREEN}v{VERSION}{Colors.NC}\n")
    
    # Draw each section based on the installer type
    current_section = None
    
    for idx, name in enumerate(installer_names):
        installer = installers[name]
        is_selected = idx == selected
        
        # Add section headers
        if name == 'recommended' and current_section != 'quick':
            current_section = 'quick'
            print(f"{Colors.BOLD}Quick Setup{Colors.NC}")
            print(f"{Colors.DIM}One-click configuration for the team{Colors.NC}")
        elif name in ['commands', 'code-standards', 'hooks', 'scripts'] and current_section != 'tools':
            current_section = 'tools'
            print(f"\n{Colors.BOLD}Tools{Colors.NC}")
            print(f"{Colors.DIM}Individual component management{Colors.NC}")
        elif name == 'uninstall' and current_section != 'danger':
            current_section = 'danger'
            print(f"\n{Colors.BOLD}Danger Zone{Colors.NC}")
            print(f"{Colors.DIM}Complete removal options{Colors.NC}")
        
        # Draw the menu item
        if name == 'recommended':
            if is_selected:
                print(f" 🎯 {Colors.REVERSE}{installer.name:<80}{Colors.NC}")
            else:
                print(f" 🎯 {installer.name:<80}")
        elif name == 'uninstall':
            if is_selected:
                print(f" {Colors.REVERSE}🗑  {installer.name:<77}{Colors.NC}")
            else:
                print(f" {Colors.RED}🗑  {installer.name:<77}{Colors.NC}")
        else:
            # Regular tools
            if is_selected:
                print(f"   {Colors.REVERSE}{installer.name:<80}{Colors.NC}")
                
                if show_details:
                    # Show additional details for selected component
                    details = installer.get_details()
                    print(f"\n{Colors.DIM}     Description: {Colors.NC}{installer.description}")
                    
                    # Show component-specific details
                    if name == 'commands' and 'installed_commands' in details:
                        count = len(details['installed_commands'])
                        print(f"{Colors.DIM}     Commands: {Colors.NC}{count} installed")
                    elif name == 'code-standards' and 'installed_languages' in details:
                        langs = details['installed_languages']
                        if langs:
                            print(f"{Colors.DIM}     Languages: {Colors.NC}{', '.join(langs)}")
                    elif name == 'hooks':
                        if 'global_hooks' in details and 'local_hooks' in details:
                            global_count = len(details['global_hooks'])
                            local_count = len(details['local_hooks'])
                            print(f"{Colors.DIM}     Hooks: {Colors.NC}{global_count} global, {local_count} local")
                    elif name == 'scripts' and 'available_scripts' in details:
                        count = len(details['available_scripts'])
                        print(f"{Colors.DIM}     Scripts: {Colors.NC}{count} available")
                    
                    print()
            else:
                print(f"   {installer.name:<80}")
    
    # Current item description
    current_installer = installers[installer_names[selected]]
    print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
    
    # Show description for selected item
    print(f"\n{Colors.BOLD}Selected:{Colors.NC} {current_installer.name}")
    print(f"{Colors.DIM}{current_installer.description}{Colors.NC}")
    
    print(f"\n{Colors.BOLD}Actions:{Colors.NC}")
    print(f"  {Colors.CYAN}↑/↓{Colors.NC}     Navigate components")
    print(f"  {Colors.CYAN}Enter/→{Colors.NC} Open component submenu")
    print(f"  {Colors.CYAN}d{Colors.NC}       Toggle details view")
    print(f"  {Colors.CYAN}a{Colors.NC}       Install all components")
    print(f"  {Colors.CYAN}r{Colors.NC}       Uninstall all components")
    print(f"  {Colors.CYAN}s{Colors.NC}       Show status")
    print(f"  {Colors.CYAN}q/←{Colors.NC}     Quit")

def run_interactive() -> None:
    """Interactive component installation with arrow key navigation"""
    global terminal_resized
    
    # Check if we're in a proper terminal
    if not sys.stdin.isatty():
        print("Error: ai-cookbook requires a terminal (TTY) to run")
        print("Please run this from a proper terminal/shell environment")
        return
    
    installers = get_installers()
    # Order the menu items properly: recommended, tools, then uninstall
    installer_names = ['recommended', 'commands', 'code-standards', 'hooks', 'scripts', 'uninstall']
    
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
            
            # Redraw menu if needed
            if force_redraw:
                draw_menu(installer_names, selected, installers, show_details)
                force_redraw = False
            
            # Get user input with short timeout to check for resize
            key = getch(timeout=0.1)
            
            if key is None:
                # Timeout - check if we need to redraw due to resize
                if terminal_resized:
                    continue
            elif key == 'q' or key == '\x03' or key == 'LEFT':  # q or Ctrl+C or left arrow
                print(Colors.SHOW_CURSOR)
                return
            elif key == 'UP' and selected > 0:
                selected -= 1
                show_details = False
                force_redraw = True
            elif key == 'DOWN' and selected < len(installer_names) - 1:
                selected += 1
                show_details = False
                force_redraw = True
            elif key == 'd':
                show_details = not show_details
                force_redraw = True
            elif key == 's':  # Show status
                show_status_screen(installers)
                force_redraw = True
            elif key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
                selected_name = installer_names[selected]
                installer = installers[selected_name]
                
                # Launch submenu for this component
                run_component_menu(selected_name, installer)
                force_redraw = True
                
            elif key == 'a':  # Install all
                install_all_components(installers)
                force_redraw = True
            elif key == 'r':  # Remove all
                uninstall_all_components(installers)
                force_redraw = True
                
    except KeyboardInterrupt:
        pass
    finally:
        print(Colors.SHOW_CURSOR)
        print()

def show_status_screen(installers: Dict[str, Any]) -> None:
    """Show detailed status screen"""
    clear_screen()
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 {ORG_DISPLAY_NAME} AI Cookbook - Installation Status{Colors.NC}\n")
    
    for name, installer in installers.items():
        status = "INSTALLED" if installer.is_installed() else "NOT INSTALLED"
        color = Colors.GREEN if installer.is_installed() else Colors.RED
        symbol = '✓' if installer.is_installed() else '✗'
        
        print(f" {color}{symbol}{Colors.NC} {installer.name:<20} {color}{status}{Colors.NC}")
        
        # Show details
        details = installer.get_details()
        if name == 'commands' and 'installed_commands' in details:
            count = len(details['installed_commands'])
            print(f"   {Colors.DIM}Commands: {count} available{Colors.NC}")
        elif name == 'code-standards' and 'installed_languages' in details:
            langs = details['installed_languages']
            if langs:
                print(f"   {Colors.DIM}Languages: {', '.join(langs)}{Colors.NC}")
        elif name == 'hooks':
            if 'global_hooks' in details and 'local_hooks' in details:
                global_count = len(details['global_hooks'])
                local_count = len(details['local_hooks'])
                print(f"   {Colors.DIM}Hooks: {global_count} global, {local_count} local{Colors.NC}")
        elif name == 'scripts' and 'available_scripts' in details:
            count = len(details['available_scripts'])
            print(f"   {Colors.DIM}Scripts: {count} available{Colors.NC}")
        print()
    
    print(f"{Colors.DIM}Press any key to return to main menu...{Colors.NC}")
    getch()

def install_all_components(installers: Dict[str, Any]) -> None:
    """Install all components with progress display"""
    clear_screen()
    print(f"\n{Colors.BOLD}{Colors.CYAN}Installing All Components{Colors.NC}\n")
    
    results = []
    for name, installer in installers.items():
        if not installer.is_installed():
            print(f"Installing {installer.name}...")
            result = installer.install()
            results.append((installer.name, result))
            
            if result.success:
                print(f"{Colors.GREEN}✓ {result.message}{Colors.NC}")
            else:
                print(f"{Colors.RED}✗ {result.message}{Colors.NC}")
            print()
    
    # Summary
    success_count = sum(1 for _, result in results if result.success)
    total_count = len(results)
    
    if results:
        print(f"{Colors.BOLD}Summary: {success_count}/{total_count} components installed successfully{Colors.NC}")
    else:
        print(f"{Colors.YELLOW}All components are already installed{Colors.NC}")

def uninstall_all_components(installers: Dict[str, Any]) -> None:
    """Uninstall all components with progress display"""
    clear_screen()
    print(f"\n{Colors.BOLD}{Colors.CYAN}Uninstalling All Components{Colors.NC}\n")
    
    results = []
    for name, installer in installers.items():
        if installer.is_installed():
            print(f"Uninstalling {installer.name}...")
            result = installer.uninstall()
            results.append((installer.name, result))
            
            if result.success:
                print(f"{Colors.GREEN}✓ {result.message}{Colors.NC}")
            else:
                print(f"{Colors.RED}✗ {result.message}{Colors.NC}")
            print()
    
    # Summary
    success_count = sum(1 for _, result in results if result.success)
    total_count = len(results)
    
    if results:
        print(f"{Colors.BOLD}Summary: {success_count}/{total_count} components uninstalled successfully{Colors.NC}")
    else:
        print(f"{Colors.YELLOW}No components were installed{Colors.NC}")

def run_component_menu(component_name: str, installer: Any) -> None:
    """Run component-specific submenu"""
    global terminal_resized
    
    try:
        if component_name == 'hooks':
            run_hooks_menu(installer)
        elif component_name == 'commands':
            run_commands_menu(installer)
        elif component_name == 'code-standards':
            run_code_standards_menu(installer)
        elif component_name == 'scripts':
            run_scripts_menu(installer)
        elif component_name == 'recommended':
            run_recommended_menu(installer)
        elif component_name == 'uninstall':
            run_uninstall_menu(installer)
        else:
            # Fallback - direct install/uninstall
            if installer.is_installed():
                result = installer.uninstall()
            else:
                result = installer.install()
            # Action is instant, return immediately
    except Exception as e:
        # Show error inline without clearing
        print(f"\n{Colors.RED}Error: {e}{Colors.NC}")

def run_hooks_menu(installer: Any) -> None:
    """Run hooks component submenu with individual hook management"""
    global terminal_resized
    
    # Get available hooks
    available_hooks = installer.get_available_hooks()
    
    if not available_hooks:
        clear_screen()
        print(f"\n{Colors.YELLOW}No hooks available{Colors.NC}")
        print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
        getch()
        return
    
    # Start in global mode by default
    mode = "global"
    installer.set_mode(mode)
    
    selected = 0
    show_details = False
    force_redraw = True
    
    try:
        clear_screen()
        while True:
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
                clear_screen()
            
            if force_redraw:
                draw_hooks_menu(available_hooks, selected, installer, show_details, mode)
                force_redraw = False
            
            key = getch(timeout=0.1)
            
            if key is None:
                if terminal_resized:
                    continue
            elif key == 'q' or key == '\x03' or key == 'LEFT':  # q or Ctrl+C or left arrow
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
            elif key == 'm':  # Toggle mode
                mode = "local" if mode == "global" else "global"
                installer.set_mode(mode)
                force_redraw = True
            elif key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
                selected_hook = available_hooks[selected]
                details = installer.get_details()
                
                if mode == "global":
                    installed_hooks = details.get('global_hooks', [])
                else:
                    installed_hooks = details.get('local_hooks', [])
                
                if selected_hook in installed_hooks:
                    # Uninstall hook
                    result = installer.uninstall_hook(selected_hook, mode)
                else:
                    # Install hook
                    result = installer.install_hook(selected_hook, mode)
                
                # Show error if installation failed
                if not result.success:
                    print(f"\n{Colors.RED}Error: {result.message}{Colors.NC}")
                    if result.details:
                        print(f"{Colors.DIM}Details: {result.details}{Colors.NC}")
                    print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
                    getch()
                
                force_redraw = True
            elif key == 'a':  # Install all
                results = []
                details = installer.get_details()
                installed_hooks = details.get(f'{mode}_hooks', [])
                
                for hook in available_hooks:
                    if hook not in installed_hooks:
                        result = installer.install_hook(hook, mode)
                        results.append((hook, result))
                
                force_redraw = True
            elif key == 'r':  # Remove all
                results = []
                details = installer.get_details()
                installed_hooks = details.get(f'{mode}_hooks', [])
                
                for hook in installed_hooks:
                    result = installer.uninstall_hook(hook, mode)
                    results.append((hook, result))
                
                force_redraw = True
    except KeyboardInterrupt:
        pass
    finally:
        print(Colors.SHOW_CURSOR)


def draw_hooks_menu(hooks: List[str], selected: int, installer: Any, show_details: bool = False, mode: str = "global") -> None:
    """Draw the hooks submenu"""
    # Get current installation status
    details = installer.get_details()
    global_hooks = details.get('global_hooks', [])
    local_hooks = details.get('local_hooks', [])
    
    # Calculate maximum hook name length for alignment
    max_hook_length = max(len(hook) for hook in hooks) if hooks else 30
    max_hook_length = max(max_hook_length, 20)  # Ensure minimum width
    
    def get_item_status(hook: str) -> str:
        is_global = hook in global_hooks
        is_local = hook in local_hooks
        
        # Build status indicators
        status_parts = []
        if is_global:
            status_parts.append(f"{Colors.CYAN}[GLOBAL]{Colors.NC}")
        if is_local:
            status_parts.append(f"{Colors.GREEN}[LOCAL]{Colors.NC}")
        return " ".join(status_parts) if status_parts else f"{Colors.GRAY}[NOT INSTALLED]{Colors.NC}"
    
    def get_item_display(hook: str, is_selected: bool) -> str:
        # Determine if installed in current mode
        if mode == "global":
            is_installed = hook in global_hooks
        else:
            is_installed = hook in local_hooks
        
        prefix = f"{Colors.GREEN}✓{Colors.NC} " if is_installed else "  "
        
        if is_selected:
            return f"{prefix}{Colors.REVERSE}{hook:<{max_hook_length}}{Colors.NC}"
        else:
            if is_installed:
                return f"{prefix}{hook:<{max_hook_length}}"
            else:
                return f"{prefix}{Colors.DIM}{hook:<{max_hook_length}}{Colors.NC}"
    
    def show_hook_details(hook: str, is_installed: bool) -> None:
        hook_info = installer.get_hook_info(hook)
        desc = hook_info.get('description', 'No description available')
        print(f"\n{Colors.DIM}     {desc}{Colors.NC}")
        print(f"{Colors.DIM}     Type: {hook_info.get('hook_type', 'PostToolUse')}{Colors.NC}")
        print(f"{Colors.DIM}     Matcher: {hook_info.get('matcher', 'No matcher')}{Colors.NC}")
        
        # Check if installed in current mode
        if mode == "global" and hook in global_hooks:
            hooks_dir = installer._get_hooks_dir(mode)
            print(f"{Colors.DIM}     Location: {hooks_dir}/{hook}.sh{Colors.NC}")
        elif mode == "local" and hook in local_hooks:
            hooks_dir = installer._get_hooks_dir(mode)
            print(f"{Colors.DIM}     Location: {hooks_dir}/{hook}.sh{Colors.NC}")
    
    # Header info
    mode_color = Colors.GREEN if mode == "global" else Colors.BLUE
    header_info = {
        "Mode": f"{mode_color}[{mode.upper()}]{Colors.NC} (press 'm' to toggle)"
    }
    
    draw_base_menu(
        title="Claude Code Hooks",
        items=hooks,
        selected=selected,
        get_item_status=get_item_status,
        get_item_display=get_item_display,
        header_info=header_info,
        show_details=show_details,
        detail_func=show_hook_details
    )
    
    # Footer
    print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
    selected_hook = hooks[selected]
    
    if mode == "global":
        is_installed = selected_hook in global_hooks
    else:
        is_installed = selected_hook in local_hooks
    
    if is_installed:
        print(f"{Colors.YELLOW}Press Enter/→ to uninstall '{selected_hook}' from {mode}{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Press Enter/→ to install '{selected_hook}' in {mode} mode{Colors.NC}")
    
    print(f"\n{Colors.DIM}↑/↓: Navigate  Enter/→: Install/Uninstall  d: Details  m: Toggle Mode  a: Install All  r: Remove All  q/←: Back{Colors.NC}")


def show_operation_result(result: Any, item_name: str, operation: str) -> None:
    """Show result of a single operation"""
    # Operations are now instant - no need to show result

def show_batch_results(results: Any, operation: str) -> None:
    """Show results of batch operations"""
    # Batch operations are now instant - no need to show results


def run_commands_menu(installer: Any) -> None:
    """Run commands component submenu with individual command management"""
    global terminal_resized
    
    # Get available commands from the installer
    status = installer.check_status()
    available_commands = status.get('available_commands', [])
    
    if not available_commands:
        clear_screen()
        print(f"\n{Colors.YELLOW}No commands available{Colors.NC}")
        print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
        getch()
        return
    
    selected = 0
    show_details = False
    force_redraw = True
    
    try:
        clear_screen()
        while True:
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
                clear_screen()
            
            if force_redraw:
                draw_commands_menu(available_commands, selected, installer, show_details)
                force_redraw = False
            
            key = getch(timeout=0.1)
            
            if key is None:
                if terminal_resized:
                    continue
            elif key == 'q' or key == '\x03' or key == 'LEFT':  # q or Ctrl+C or left arrow
                print(Colors.SHOW_CURSOR)
                return
            elif key == 'UP' and selected > 0:
                selected -= 1
                show_details = False
                force_redraw = True
            elif key == 'DOWN' and selected < len(available_commands) - 1:
                selected += 1
                show_details = False
                force_redraw = True
            elif key == 'd':
                show_details = not show_details
                force_redraw = True
            elif key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
                selected_command = available_commands[selected]
                
                # Toggle installation for selected command
                status = installer.check_status()
                installed_commands = status.get('installed_commands', [])
                
                if selected_command in installed_commands:
                    # Uninstall command
                    result = installer.uninstall_command(selected_command)
                else:
                    # Install command
                    result = installer.install_command(selected_command)
                
                # Show result briefly
                if result:
                    show_operation_result(result, selected_command, "install" if selected_command not in installed_commands else "uninstall")
                
                force_redraw = True
            elif key == 'a':  # Install all
                results = []
                status = installer.check_status()
                installed_commands = status.get('installed_commands', [])
                for command in available_commands:
                    if command not in installed_commands:
                        result = installer.install_command(command)
                        results.append((command, result))
                show_batch_results(results, "install")
                force_redraw = True
            elif key == 'r':  # Remove all
                results = []
                status = installer.check_status()
                installed_commands = status.get('installed_commands', [])
                for command in installed_commands:
                    result = installer.uninstall_command(command)
                    results.append((command, result))
                show_batch_results(results, "uninstall")
                force_redraw = True
    except KeyboardInterrupt:
        pass
    finally:
        print(Colors.SHOW_CURSOR)

def draw_commands_menu(commands: List[str], selected: int, installer: Any, show_details: bool = False) -> None:
    """Draw the commands submenu"""
    # Get current installation status
    status = installer.check_status()
    installed_commands = status.get('installed_commands', [])
    
    # Calculate maximum command name length for alignment
    max_cmd_length = max(len(cmd) for cmd in commands) if commands else 30
    max_cmd_length = max(max_cmd_length, 35)  # Ensure minimum width
    
    def get_item_status(command: str) -> str:
        is_installed = command in installed_commands
        if is_installed:
            return f"{Colors.GREEN}[INSTALLED]{Colors.NC}"
        else:
            return f"{Colors.GRAY}[NOT INSTALLED]{Colors.NC}"
    
    def get_item_display(command: str, is_selected: bool) -> str:
        is_installed = command in installed_commands
        prefix = f"{Colors.GREEN}✓{Colors.NC} " if is_installed else "  "
        
        if is_selected:
            return f"{prefix}{Colors.REVERSE}{command:<{max_cmd_length}}{Colors.NC}"
        else:
            if is_installed:
                return f"{prefix}{command:<{max_cmd_length}}"
            else:
                return f"{prefix}{Colors.DIM}{command:<{max_cmd_length}}{Colors.NC}"
    
    def show_command_details(command: str, is_installed: bool) -> None:
        print(f"\n{Colors.DIM}     Claude command template for automation{Colors.NC}")
        if command in installed_commands:
            target_dir = status.get('commands_dir', '') + f"/{command}"
            print(f"{Colors.DIM}     Location: {target_dir}{Colors.NC}")
    
    draw_base_menu(
        title="Claude Commands",
        items=commands,
        selected=selected,
        get_item_status=get_item_status,
        get_item_display=get_item_display,
        show_details=show_details,
        detail_func=show_command_details
    )
    
    # Footer
    print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
    selected_command = commands[selected]
    if selected_command in installed_commands:
        print(f"{Colors.YELLOW}Press Enter/→ to uninstall '{selected_command}'{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Press Enter/→ to install '{selected_command}'{Colors.NC}")
    
    print(f"\n{Colors.DIM}↑/↓: Navigate  Enter/→: Install/Uninstall  d: Details  a: Install All  r: Remove All  q/←: Back{Colors.NC}")

def run_code_standards_menu(installer: Any) -> None:
    """Run code standards component submenu with individual language management"""
    global terminal_resized
    
    # Get available languages from the installer
    status = installer.check_status()
    available_languages = status.get('available_languages', [])
    
    if not available_languages:
        clear_screen()
        print(f"\n{Colors.YELLOW}No language standards available{Colors.NC}")
        print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
        getch()
        return
    
    selected = 0
    show_details = False
    force_redraw = True
    
    try:
        clear_screen()
        while True:
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
                clear_screen()
            
            if force_redraw:
                draw_code_standards_menu(available_languages, selected, installer, show_details)
                force_redraw = False
            
            key = getch(timeout=0.1)
            
            if key is None:
                if terminal_resized:
                    continue
            elif key == 'q' or key == '\x03' or key == 'LEFT':  # q or Ctrl+C or left arrow
                print(Colors.SHOW_CURSOR)
                return
            elif key == 'UP' and selected > 0:
                selected -= 1
                show_details = False
                force_redraw = True
            elif key == 'DOWN' and selected < len(available_languages) - 1:
                selected += 1
                show_details = False
                force_redraw = True
            elif key == 'd':
                show_details = not show_details
                force_redraw = True
            elif key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
                selected_language = available_languages[selected]
                
                # Toggle installation for selected language
                status = installer.check_status()
                installed_languages = status.get('installed_languages', [])
                
                if selected_language in installed_languages:
                    # Uninstall language
                    result = installer.uninstall_language(selected_language)
                else:
                    # Install language
                    result = installer.install_language(selected_language)
                
                # Show result briefly
                if result:
                    show_operation_result(result, selected_language, "install" if selected_language not in installed_languages else "uninstall")
                
                force_redraw = True
            elif key == 'a':  # Install all
                results = []
                status = installer.check_status()
                installed_languages = status.get('installed_languages', [])
                for language in available_languages:
                    if language not in installed_languages:
                        result = installer.install_language(language)
                        results.append((language, result))
                show_batch_results(results, "install")
                force_redraw = True
            elif key == 'r':  # Remove all
                results = []
                status = installer.check_status()
                installed_languages = status.get('installed_languages', [])
                for language in installed_languages:
                    result = installer.uninstall_language(language)
                    results.append((language, result))
                show_batch_results(results, "uninstall")
                force_redraw = True
    except KeyboardInterrupt:
        pass
    finally:
        print(Colors.SHOW_CURSOR)

def draw_code_standards_menu(languages: List[str], selected: int, installer: Any, show_details: bool = False) -> None:
    """Draw the code standards submenu"""
    # Get current installation status
    status = installer.check_status()
    installed_languages = status.get('installed_languages', [])
    
    def get_item_status(language: str) -> str:
        is_installed = language in installed_languages
        if is_installed:
            return f"{Colors.GREEN}[INSTALLED]{Colors.NC}"
        else:
            return f"{Colors.GRAY}[NOT INSTALLED]{Colors.NC}"
    
    def get_item_display(language: str, is_selected: bool) -> str:
        is_installed = language in installed_languages
        prefix = f"{Colors.GREEN}✓{Colors.NC} " if is_installed else "  "
        
        if is_selected:
            return f"{prefix}{Colors.REVERSE}{language:<20}{Colors.NC}"
        else:
            if is_installed:
                return f"{prefix}{language:<20}"
            else:
                return f"{prefix}{Colors.DIM}{language:<20}{Colors.NC}"
    
    def show_language_details(language: str, is_installed: bool) -> None:
        print(f"\n{Colors.DIM}     Standards for {language} programming language{Colors.NC}")
        if language in installed_languages:
            target_dir = status.get('standards_dir', '') + f"/{language}"
            print(f"{Colors.DIM}     Location: {target_dir}{Colors.NC}")
    
    draw_base_menu(
        title="Code Standards",
        items=languages,
        selected=selected,
        get_item_status=get_item_status,
        get_item_display=get_item_display,
        show_details=show_details,
        detail_func=show_language_details
    )
    
    # Footer
    print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
    selected_language = languages[selected]
    if selected_language in installed_languages:
        print(f"{Colors.YELLOW}Press Enter/→ to uninstall '{selected_language}' standards{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Press Enter/→ to install '{selected_language}' standards{Colors.NC}")
    
    print(f"\n{Colors.DIM}↑/↓: Navigate  Enter/→: Install/Uninstall  d: Details  a: Install All  r: Remove All  q/←: Back{Colors.NC}")

def run_scripts_menu(installer: Any) -> None:
    """Run scripts component submenu"""
    details = installer.get_details()
    available_scripts = details.get('available_scripts', [])
    
    clear_screen()
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 Scripts PATH{Colors.NC}")
    print(f"Available: {len(available_scripts)}\n")
    
    for script in available_scripts:
        print(f"   {script}")
    
    print(f"\n{Colors.DIM}Scripts PATH is managed as a single unit.{Colors.NC}")
    
    if installer.is_installed():
        print(f"\n{Colors.YELLOW}Press Enter/→ to remove scripts from PATH{Colors.NC}")
        action_text = "remove from PATH"
    else:
        print(f"\n{Colors.GREEN}Press Enter/→ to add scripts to PATH{Colors.NC}")
        action_text = "add to PATH"
    
    print(f"{Colors.DIM}Press q or ← to go back{Colors.NC}")
    
    key = getch()
    if key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
        if installer.is_installed():
            result = installer.uninstall()
        else:
            result = installer.install()
        # Action is instant, return immediately


def run_uninstall_menu(installer: Any) -> None:
    """Run uninstall everything menu with confirmation screen"""
    global terminal_resized
    
    force_redraw = True
    confirmed = False
    
    try:
        while True:
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
            
            if force_redraw:
                clear_screen()
                
                # Header
                print(f"\n{Colors.BOLD}{Colors.RED}🗑️  Uninstall Everything{Colors.NC}")
                print(f"{Colors.YELLOW}⚠️  This will remove all {ORG_DISPLAY_NAME} AI Cookbook components{Colors.NC}\n")
                
                # Get current status
                status = installer.check_status()
                
                if status['total_items'] == 0:
                    print(f"{Colors.GREEN}✓ No {ORG_DISPLAY_NAME} components are currently installed{Colors.NC}")
                    print(f"\n{Colors.DIM}Press any key to return...{Colors.NC}")
                    getch()
                    break
                
                # Show what will be removed
                print(f"{Colors.BOLD}The following will be removed:{Colors.NC}")
                print("=" * 60)
                
                # Show installed components
                for component, items in status['components_installed'].items():
                    if component == 'hooks' and items:
                        print(f"\n{Colors.BOLD}{component.replace('_', ' ').title()}:{Colors.NC}")
                        if items.get('global'):
                            print("  Global hooks:")
                            for hook in items['global']:
                                print(f"    • {hook}")
                        if items.get('local'):
                            print("  Local hooks:")
                            for hook in items['local']:
                                print(f"    • {hook}")
                    elif items:
                        print(f"\n{Colors.BOLD}{component.replace('_', ' ').title()}:{Colors.NC}")
                        for item in items:
                            print(f"  • {item}")
                
                # Show local projects
                if status['local_projects']:
                    print(f"\n{Colors.BOLD}Local Projects:{Colors.NC}")
                    for project in status['local_projects']:
                        print(f"  • {project}")
                
                # Show directories that will be cleaned
                print(f"\n{Colors.BOLD}Directories to be removed:{Colors.NC}")
                print(f"  • ~/.claude/{ORG_NAME}/")
                print(f"  • ~/.claude/commands/{ORG_NAME}/")
                print(f"  • ~/.claude/hooks/{ORG_NAME}/")
                
                print(f"\n{Colors.BOLD}Files to be cleaned:{Colors.NC}")
                print(f"  • ~/.claude/CLAUDE.md ({ORG_DISPLAY_NAME} entries)")
                print("  • ~/.claude/settings.json (hook entries)")
                print("  • ~/.claude/.ai-cookbook-projects.json")
                print("  • Local project .claude/settings.json files")
                
                print("\n" + "=" * 60)
                print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  This action cannot be undone!{Colors.NC}")
                
                if not confirmed:
                    print(f"\n{Colors.BOLD}Are you sure you want to uninstall everything?{Colors.NC}")
                    print(f"\n  {Colors.RED}[y]{Colors.NC} Yes, uninstall everything")
                    print(f"  {Colors.GREEN}[n]{Colors.NC} No, go back")
                    print(f"\n{Colors.DIM}Press y to confirm, n or ← to cancel{Colors.NC}")
                
                force_redraw = False
            
            if confirmed:
                # Run the uninstallation
                print(f"\n{Colors.YELLOW}🔧 Uninstalling all components...{Colors.NC}")
                print("=" * 60)
                result = installer.uninstall(skip_confirmation=True)
                
                # Show result and wait for user to read it
                if result.success:
                    print(f"\n{Colors.GREEN}✅ {result.message}{Colors.NC}")
                else:
                    print(f"\n{Colors.RED}❌ {result.message}{Colors.NC}")
                
                print(f"\n{Colors.DIM}Press any key to return to main menu...{Colors.NC}")
                getch()
                break
            
            # Get user input
            key = getch()
            
            if key in ['n', 'q', 'LEFT', '\x03']:  # n, q, left arrow, or Ctrl+C
                break
            elif key == 'y':
                confirmed = True
                force_redraw = True
                
    except KeyboardInterrupt:
        pass

def run_recommended_menu(installer: Any) -> None:
    """Run recommended tools submenu with interactive options"""
    global terminal_resized
    
    # Build options dynamically
    installer.build_interactive_options()
    options = installer.get_interactive_options()
    
    if not options:
        clear_screen()
        print(f"\n{Colors.YELLOW}No recommended tools options available{Colors.NC}")
        print(f"{Colors.DIM}Press any key to continue...{Colors.NC}")
        getch()
        return
    
    selected = 0
    force_redraw = True
    
    try:
        while True:
            # Check if terminal was resized
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
            
            # Redraw menu if needed
            if force_redraw:
                clear_screen()
                print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 Recommended Tools{Colors.NC}")
                print(f"Team-curated configuration for consistent AI development\n")
                
                # Show recommended tools list
                try:
                    config = installer._load_config()
                    if config:
                        for category, tools in config.items():
                            if category and tools:  # Skip empty categories
                                print(f"{Colors.BOLD}{category.title()}:{Colors.NC}")
                                for tool in tools:
                                    print(f"  • {tool}")
                                print()
                except Exception:
                    print(f"{Colors.DIM}Could not load tools configuration{Colors.NC}\n")
                
                # Show options
                for i, option in enumerate(options):
                    is_selected = i == selected
                    name = option['name']
                    desc = option['description']
                    
                    if is_selected:
                        print(f" {Colors.REVERSE}  {name:<30} {desc:<50}  {Colors.NC}")
                    else:
                        print(f"   {name:<30} {Colors.DIM}{desc}{Colors.NC}")
                
                print(f"\n{Colors.DIM}Press Enter/→ to select, q/← to go back{Colors.NC}")
                force_redraw = False
            
            # Get user input
            key = getch()
            
            if key == 'q' or key == 'LEFT':  # q or left arrow
                break
            elif key == 'UP':
                selected = (selected - 1) % len(options)
                force_redraw = True
            elif key == 'DOWN':
                selected = (selected + 1) % len(options)
                force_redraw = True
            elif key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
                # Execute selected option
                option = options[selected]
                action = option.get('action')
                
                if action:
                    try:
                        # For recommended tools installation, we want to see the output
                        if option['name'] == "✅ Install Recommended Tools":
                            clear_screen()
                            result = action()
                            # Wait for user to read the output
                            print(f"\n{Colors.DIM}Press any key to return to main menu...{Colors.NC}")
                            getch()
                            # Return to main menu after installation
                            break
                        else:
                            result = action()
                        
                        # Rebuild options as state may have changed
                        installer.build_interactive_options()
                        options = installer.get_interactive_options()
                        if not options:
                            break
                        
                        selected = min(selected, len(options) - 1)
                        force_redraw = True
                        
                    except Exception as e:
                        # Show error inline without clearing screen
                        print(f"\n{Colors.RED}Error: {e}{Colors.NC}")
                        force_redraw = True
                        
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run_interactive()