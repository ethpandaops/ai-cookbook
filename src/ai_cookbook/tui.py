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
from typing import List, Dict, Optional

from .installers.commands import CommandsInstaller
from .installers.code_standards import CodeStandardsInstaller
from .installers.hooks import HooksInstaller
from .installers.scripts import ScriptsInstaller
from .installers.recommended import RecommendedToolsInstaller

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

def signal_handler(signum, frame):
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

def clear_screen():
    """Clear the terminal screen"""
    print("\033[2J\033[H", end='')

def get_installers():
    """Get all installer instances"""
    return {
        'recommended': RecommendedToolsInstaller(),
        'commands': CommandsInstaller(),
        'code-standards': CodeStandardsInstaller(), 
        'hooks': HooksInstaller(),
        'scripts': ScriptsInstaller()
    }

def draw_menu(installer_names: List[str], selected: int, installers: Dict, show_details: bool = False):
    """Draw the interactive menu"""
    print(Colors.HIDE_CURSOR, end='')
    
    # Clear screen and reset cursor
    clear_screen()
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 ethPandaOps AI Cookbook Installer{Colors.NC}")
    print(f"Version: {Colors.GREEN}v1.0.0{Colors.NC}\n")
    
    # Quick Setup section
    print(f"{Colors.BOLD}Quick Setup{Colors.NC}")
    print(f"{Colors.DIM}One-click configuration for the team{Colors.NC}")
    
    # Show recommended installer first
    recommended_installer = installers['recommended']
    is_recommended_selected = selected == 0
    
    if is_recommended_selected:
        print(f" 🎯 {Colors.REVERSE}{recommended_installer.name:<80}{Colors.NC}")
    else:
        print(f" 🎯 {recommended_installer.name:<80}")
    
    # Tools section
    print(f"\n{Colors.BOLD}Tools{Colors.NC}")
    print(f"{Colors.DIM}Individual component management{Colors.NC}")
    
    # Show other installers
    tool_installers = [name for name in installer_names if name != 'recommended']
    for i, name in enumerate(tool_installers):
        installer = installers[name]
        # Adjust selection index (add 1 because recommended is index 0)
        is_selected = (i + 1) == selected
        
        # Selection indicator for tools (no descriptions or status)
        if is_selected:
            print(f"   {Colors.REVERSE}{installer.name:<80}{Colors.NC}")
            
            if show_details:
                # Show additional details for selected component
                details = installer.get_details()
                print(f"\n{Colors.DIM}     Description: {Colors.NC}{installer.description}")
                
                # Show component-specific details
                if name == 'commands':
                    if 'installed_commands' in details:
                        count = len(details['installed_commands'])
                        print(f"{Colors.DIM}     Commands: {Colors.NC}{count} installed")
                elif name == 'code-standards':
                    if 'installed_languages' in details:
                        langs = details['installed_languages']
                        if langs:
                            print(f"{Colors.DIM}     Languages: {Colors.NC}{', '.join(langs)}")
                elif name == 'hooks':
                    if 'global_hooks' in details and 'local_hooks' in details:
                        global_count = len(details['global_hooks'])
                        local_count = len(details['local_hooks'])
                        print(f"{Colors.DIM}     Hooks: {Colors.NC}{global_count} global, {local_count} local")
                elif name == 'scripts':
                    if 'available_scripts' in details:
                        count = len(details['available_scripts'])
                        print(f"{Colors.DIM}     Scripts: {Colors.NC}{count} available")
                
                print()
        else:
            # Non-selected tools (clean, no status)
            print(f"   {installer.name:<80}")
    
    # Current item description (only for tools, not recommended)
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

def run_interactive():
    """Interactive component installation with arrow key navigation"""
    global terminal_resized
    
    # Check if we're in a proper terminal
    if not sys.stdin.isatty():
        print("Error: ai-cookbook requires a terminal (TTY) to run")
        print("Please run this from a proper terminal/shell environment")
        return
    
    installers = get_installers()
    installer_names = list(installers.keys())
    
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

def show_status_screen(installers):
    """Show detailed status screen"""
    clear_screen()
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 ethPandaOps AI Cookbook - Installation Status{Colors.NC}\n")
    
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

def install_all_components(installers):
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
    
    print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
    getch()

def uninstall_all_components(installers):
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
    
    print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
    getch()

def run_component_menu(component_name: str, installer):
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
        else:
            # Fallback - direct install/uninstall
            if installer.is_installed():
                result = installer.uninstall()
            else:
                result = installer.install()
            
            clear_screen()
            print(f"\n{Colors.CYAN}{installer.name}{Colors.NC}\n")
            if result.success:
                print(f"{Colors.GREEN}✓ {result.message}{Colors.NC}")
            else:
                print(f"{Colors.RED}✗ {result.message}{Colors.NC}")
            print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
            getch()
    except Exception as e:
        clear_screen()
        print(f"\n{Colors.RED}Error: {e}{Colors.NC}")
        print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
        getch()

def run_hooks_menu(installer):
    """Run hooks component submenu similar to install-hooks.py"""
    global terminal_resized
    
    # Get available hooks from the installer
    details = installer.get_details()
    available_hooks = details.get('available_hooks', [])
    
    if not available_hooks:
        clear_screen()
        print(f"\n{Colors.YELLOW}No hooks available{Colors.NC}")
        print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
        getch()
        return
    
    # Ask for installation mode first (like install-hooks.py)
    mode = select_hooks_mode()
    if mode is None:
        return  # User cancelled
    
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
            elif key == 'm':  # Change mode
                new_mode = select_hooks_mode()
                if new_mode:
                    mode = new_mode
                    installer.set_mode(mode)
                force_redraw = True
            elif key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
                selected_hook = available_hooks[selected]
                
                # Toggle installation for selected hook
                details = installer.get_details()
                global_hooks = details.get('global_hooks', [])
                local_hooks = details.get('local_hooks', [])
                
                if selected_hook in global_hooks or selected_hook in local_hooks:
                    # Uninstall hook - determine which mode it's installed in
                    if selected_hook in global_hooks and selected_hook in local_hooks:
                        # Installed in both - uninstall from current mode
                        result = installer.uninstall_hook(selected_hook, mode)
                    elif selected_hook in global_hooks:
                        result = installer.uninstall_hook(selected_hook, "global")
                    else:
                        result = installer.uninstall_hook(selected_hook, "local")
                else:
                    # Install hook in current mode
                    result = installer.install_hook(selected_hook, mode)
                
                # Show result briefly
                if result:
                    show_operation_result(result, selected_hook, "install" if selected_hook not in global_hooks and selected_hook not in local_hooks else "uninstall")
                
                force_redraw = True
            elif key == 'a':  # Install all
                results = []
                for hook in available_hooks:
                    details = installer.get_details()
                    global_hooks = details.get('global_hooks', [])
                    local_hooks = details.get('local_hooks', [])
                    if hook not in global_hooks and hook not in local_hooks:
                        result = installer.install_hook(hook, mode)
                        results.append((hook, result))
                show_batch_results(results, "install")
                force_redraw = True
            elif key == 'r':  # Remove all
                results = []
                details = installer.get_details()
                all_installed = set(details.get('global_hooks', [])) | set(details.get('local_hooks', []))
                for hook in all_installed:
                    # Determine which mode to uninstall from
                    hook_mode = mode if hook in details.get(f'{mode}_hooks', []) else ("global" if hook in details.get('global_hooks', []) else "local")
                    result = installer.uninstall_hook(hook, hook_mode)
                    results.append((hook, result))
                show_batch_results(results, "uninstall")
                force_redraw = True
    except KeyboardInterrupt:
        pass
    finally:
        print(Colors.SHOW_CURSOR)

def select_hooks_mode():
    """Ask user to select installation mode for hooks"""
    global terminal_resized
    selected = 0  # Default to global
    force_redraw = True
    
    try:
        while True:
            if terminal_resized:
                terminal_resized = False
                force_redraw = True
            
            if force_redraw:
                print(Colors.HIDE_CURSOR)
                clear_screen()
                
                print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 Select Hooks Installation Mode{Colors.NC}\n")
                
                # Global option
                if selected == 0:
                    print(f"{Colors.REVERSE}{Colors.BOLD} ► Global {Colors.NC}")
                    print(f"   {Colors.GREEN}Install hooks for all projects{Colors.NC}")
                    print(f"   {Colors.DIM}~/.claude/settings.json{Colors.NC}")
                else:
                    print(f"   {Colors.BOLD}Global{Colors.NC}")
                    print(f"   {Colors.DIM}Install hooks for all projects{Colors.NC}")
                    print(f"   {Colors.DIM}~/.claude/settings.json{Colors.NC}")
                
                print()
                
                # Local option
                if selected == 1:
                    print(f"{Colors.REVERSE}{Colors.BOLD} ► Local {Colors.NC}")
                    print(f"   {Colors.BLUE}Install hooks for current directory only{Colors.NC}")
                    print(f"   {Colors.DIM}.claude/settings.local.json{Colors.NC}")
                else:
                    print(f"   {Colors.BOLD}Local{Colors.NC}")
                    print(f"   {Colors.DIM}Install hooks for current directory only{Colors.NC}")
                    print(f"   {Colors.DIM}.claude/settings.local.json{Colors.NC}")
                
                print()
                print(f"\n{Colors.DIM}↑/↓: Navigate  Enter/→: Select  q/←: Cancel{Colors.NC}")
                
                force_redraw = False
            
            key = getch(timeout=0.1)
            
            if key is None:
                if terminal_resized:
                    continue
            elif key == 'q' or key == '\x03' or key == 'LEFT':  # q or Ctrl+C or left arrow
                print(Colors.SHOW_CURSOR)
                return None
            elif key == 'UP' and selected > 0:
                selected = 0
                force_redraw = True
            elif key == 'DOWN' and selected < 1:
                selected = 1
                force_redraw = True
            elif key == '\r' or key == '\n' or key == 'RIGHT':  # Enter or right arrow
                print(Colors.SHOW_CURSOR)
                return "global" if selected == 0 else "local"
                    
    except KeyboardInterrupt:
        print(Colors.SHOW_CURSOR)
        return None

def show_operation_result(result, item_name, operation):
    """Show result of a single operation"""
    if result.success:
        print(f"\n{Colors.GREEN}✓ {operation.title()}ed {item_name}: {result.message}{Colors.NC}")
    else:
        print(f"\n{Colors.RED}✗ Failed to {operation} {item_name}: {result.message}{Colors.NC}")
    print(f"{Colors.DIM}Press any key to continue...{Colors.NC}")
    getch()

def show_batch_results(results, operation):
    """Show results of batch operations"""
    clear_screen()
    print(f"\n{Colors.BOLD}{Colors.CYAN}Batch {operation.title()} Results{Colors.NC}\n")
    
    successful = 0
    for item_name, result in results:
        if result.success:
            print(f"{Colors.GREEN}✓ {item_name}: {result.message}{Colors.NC}")
            successful += 1
        else:
            print(f"{Colors.RED}✗ {item_name}: {result.message}{Colors.NC}")
    
    total = len(results)
    if total > 0:
        print(f"\n{Colors.BOLD}Summary: {successful}/{total} operations successful{Colors.NC}")
    
    print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
    getch()

def draw_hooks_menu(hooks: list, selected: int, installer, show_details: bool = False, mode: str = "global"):
    """Draw the hooks submenu"""
    print(Colors.HIDE_CURSOR, end='')
    clear_screen()
    
    # Get current hook status
    details = installer.get_details()
    global_hooks = details.get('global_hooks', [])
    local_hooks = details.get('local_hooks', [])
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 Claude Code Hooks{Colors.NC}")
    mode_display = f"{Colors.GREEN}[GLOBAL]{Colors.NC}" if mode == "global" else f"{Colors.BLUE}[LOCAL]{Colors.NC}"
    print(f"Mode: {mode_display} | Available Hooks: {len(hooks)}\n")
    
    # Hooks list
    for i, hook in enumerate(hooks):
        is_selected = i == selected
        is_global = hook in global_hooks
        is_local = hook in local_hooks
        
        # Get hook description
        hook_info = installer.get_hook_info(hook)
        desc = hook_info.get('description', 'No description available')
        if len(desc) > 50:
            desc = desc[:47] + "..."
        
        # Selection indicator
        if is_selected:
            if is_global and is_local:
                print(f" {Colors.GREEN}✓{Colors.NC} {Colors.REVERSE}{hook:<20} {desc:<50}{Colors.NC} {Colors.GREEN}[GLOBAL, LOCAL]{Colors.NC}")
            elif is_global:
                print(f" {Colors.GREEN}✓{Colors.NC} {Colors.REVERSE}{hook:<20} {desc:<50}{Colors.NC} {Colors.GREEN}[GLOBAL]{Colors.NC}")
            elif is_local:
                print(f" {Colors.GREEN}✓{Colors.NC} {Colors.REVERSE}{hook:<20} {desc:<50}{Colors.NC} {Colors.GREEN}[LOCAL]{Colors.NC}")
            else:
                print(f"   {Colors.REVERSE}{hook:<20} {desc:<50}{Colors.NC} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
            
            if show_details:
                print(f"\n{Colors.DIM}     Description: {Colors.NC}{hook_info.get('description', 'No description')}")
                print(f"{Colors.DIM}     Hook Type: {Colors.NC}{hook_info.get('hook_type', 'PostToolUse')}")
                print(f"{Colors.DIM}     Matcher: {Colors.NC}{hook_info.get('matcher', 'No matcher')}")
                print()
        else:
            if is_global and is_local:
                print(f" {Colors.GREEN}✓{Colors.NC} {hook:<20} {desc:<50} {Colors.GREEN}[GLOBAL, LOCAL]{Colors.NC}")
            elif is_global:
                print(f" {Colors.GREEN}✓{Colors.NC} {hook:<20} {desc:<50} {Colors.GREEN}[GLOBAL]{Colors.NC}")
            elif is_local:
                print(f" {Colors.GREEN}✓{Colors.NC} {hook:<20} {desc:<50} {Colors.GREEN}[LOCAL]{Colors.NC}")
            else:
                print(f"   {Colors.DIM}{hook:<20} {desc:<50} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
    
    # Footer
    print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
    selected_hook = hooks[selected]
    if selected_hook in global_hooks or selected_hook in local_hooks:
        print(f"{Colors.YELLOW}Press Enter/→ to uninstall '{selected_hook}'{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Press Enter/→ to install '{selected_hook}'{Colors.NC}")
    
    print(f"\n{Colors.DIM}↑/↓: Navigate  Enter/→: Install/Uninstall  d: Details  a: Install All  r: Remove All  m: Change Mode  q/←: Back{Colors.NC}")

def run_commands_menu(installer):
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

def draw_commands_menu(commands: list, selected: int, installer, show_details: bool = False):
    """Draw the commands submenu"""
    print(Colors.HIDE_CURSOR, end='')
    clear_screen()
    
    # Get current installation status
    status = installer.check_status()
    installed_commands = status.get('installed_commands', [])
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 Claude Commands{Colors.NC}")
    print(f"Available Commands: {len(commands)}\n")
    
    # Calculate maximum command name length for alignment
    max_cmd_length = max(len(cmd) for cmd in commands) if commands else 30
    max_cmd_length = max(max_cmd_length, 35)  # Ensure minimum width
    
    # Commands list
    for i, command in enumerate(commands):
        is_selected = i == selected
        is_installed = command in installed_commands
        
        # Selection indicator
        if is_selected:
            if is_installed:
                print(f" {Colors.GREEN}✓{Colors.NC} {Colors.REVERSE}{command:<{max_cmd_length}}{Colors.NC} {Colors.GREEN}[INSTALLED]{Colors.NC}")
            else:
                print(f"   {Colors.REVERSE}{command:<{max_cmd_length}}{Colors.NC} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
            
            if show_details:
                print(f"\n{Colors.DIM}     Claude command template for automation{Colors.NC}")
                if is_installed:
                    target_dir = status.get('commands_dir', '') + f"/{command}"
                    print(f"{Colors.DIM}     Location: {target_dir}{Colors.NC}")
                print()
        else:
            if is_installed:
                print(f" {Colors.GREEN}✓{Colors.NC} {command:<{max_cmd_length}} {Colors.GREEN}[INSTALLED]{Colors.NC}")
            else:
                print(f"   {Colors.DIM}{command:<{max_cmd_length}} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
    
    # Footer
    print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
    selected_command = commands[selected]
    if selected_command in installed_commands:
        print(f"{Colors.YELLOW}Press Enter/→ to uninstall '{selected_command}'{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Press Enter/→ to install '{selected_command}'{Colors.NC}")
    
    print(f"\n{Colors.DIM}↑/↓: Navigate  Enter/→: Install/Uninstall  d: Details  a: Install All  r: Remove All  q/←: Back{Colors.NC}")

def run_code_standards_menu(installer):
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

def draw_code_standards_menu(languages: list, selected: int, installer, show_details: bool = False):
    """Draw the code standards submenu"""
    print(Colors.HIDE_CURSOR, end='')
    clear_screen()
    
    # Get current installation status
    status = installer.check_status()
    installed_languages = status.get('installed_languages', [])
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 Code Standards{Colors.NC}")
    print(f"Available Languages: {len(languages)}\n")
    
    # Languages list
    for i, language in enumerate(languages):
        is_selected = i == selected
        is_installed = language in installed_languages
        
        # Selection indicator
        if is_selected:
            if is_installed:
                print(f" {Colors.GREEN}✓{Colors.NC} {Colors.REVERSE}{language:<20}{Colors.NC} {Colors.GREEN}[INSTALLED]{Colors.NC}")
            else:
                print(f"   {Colors.REVERSE}{language:<20}{Colors.NC} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
            
            if show_details:
                print(f"\n{Colors.DIM}     Standards for {language} programming language{Colors.NC}")
                if is_installed:
                    target_dir = status.get('standards_dir', '') + f"/{language}"
                    print(f"{Colors.DIM}     Location: {target_dir}{Colors.NC}")
                print()
        else:
            if is_installed:
                print(f" {Colors.GREEN}✓{Colors.NC} {language:<20} {Colors.GREEN}[INSTALLED]{Colors.NC}")
            else:
                print(f"   {Colors.DIM}{language:<20} {Colors.GRAY}[NOT INSTALLED]{Colors.NC}")
    
    # Footer
    print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
    selected_language = languages[selected]
    if selected_language in installed_languages:
        print(f"{Colors.YELLOW}Press Enter/→ to uninstall '{selected_language}' standards{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Press Enter/→ to install '{selected_language}' standards{Colors.NC}")
    
    print(f"\n{Colors.DIM}↑/↓: Navigate  Enter/→: Install/Uninstall  d: Details  a: Install All  r: Remove All  q/←: Back{Colors.NC}")

def run_scripts_menu(installer):
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
        
        clear_screen()
        print(f"\n{Colors.CYAN}Scripts {action_text.title()}{Colors.NC}\n")
        if result.success:
            print(f"{Colors.GREEN}✓ {result.message}{Colors.NC}")
        else:
            print(f"{Colors.RED}✗ {result.message}{Colors.NC}")
        print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
        getch()


def run_recommended_menu(installer):
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
                        result = action()
                        
                        # Show result
                        clear_screen()
                        print(f"\n{Colors.CYAN}{option['name']}{Colors.NC}\n")
                        
                        if result and hasattr(result, 'success'):
                            if result.success:
                                print(f"{Colors.GREEN}✓ {result.message}{Colors.NC}")
                            else:
                                print(f"{Colors.RED}✗ {result.message}{Colors.NC}")
                        else:
                            print(f"{Colors.GREEN}✓ Action completed{Colors.NC}")
                        
                        print(f"\n{Colors.DIM}Press any key to continue...{Colors.NC}")
                        getch()
                        
                        # Rebuild options as state may have changed
                        installer.build_interactive_options()
                        options = installer.get_interactive_options()
                        if not options:
                            break
                        
                        selected = min(selected, len(options) - 1)
                        force_redraw = True
                        
                    except Exception as e:
                        clear_screen()
                        print(f"\n{Colors.RED}Error: {e}{Colors.NC}")
                        print(f"{Colors.DIM}Press any key to continue...{Colors.NC}")
                        getch()
                        force_redraw = True
                        
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run_interactive()