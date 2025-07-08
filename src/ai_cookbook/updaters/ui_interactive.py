"""Interactive text-based UI for exploring and applying updates."""

import os
import sys
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
from .detector import UpdateStatus
# Removed BaseInstaller import to avoid circular dependency


class InteractiveUpdateUI:
    """Interactive UI for exploring updates with navigation and details."""
    
    def __init__(self):
        """Initialize the interactive update UI."""
        self.terminal_width = shutil.get_terminal_size((80, 24)).columns
        self.selected_index = 0
        self.show_details = False
        self.current_file_index = 0
        
    def _clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _get_input_char(self) -> str:
        """Get a single character input from user."""
        if os.name == 'nt':  # Windows
            import msvcrt
            return msvcrt.getch().decode('utf-8', errors='ignore').lower()
        else:  # Unix/Linux/Mac
            import termios, tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                char = sys.stdin.read(1).lower()
                # Handle arrow keys
                if char == '\x1b':  # ESC sequence
                    char += sys.stdin.read(2)
                    if char == '\x1b[A':  # Up arrow
                        return 'up'
                    elif char == '\x1b[B':  # Down arrow
                        return 'down'
                    elif char == '\x1b[C':  # Right arrow
                        return 'right'
                    elif char == '\x1b[D':  # Left arrow
                        return 'left'
                return char
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def _center_text(self, text: str, width: Optional[int] = None) -> str:
        """Center text within given width."""
        if width is None:
            width = self.terminal_width
        return text.center(width)
    
    def _truncate(self, text: str, max_width: int) -> str:
        """Truncate text to fit within max width."""
        if len(text) <= max_width:
            return text
        return text[:max_width-3] + "..."
    
    def _format_component_line(self, component: str, status: UpdateStatus, is_selected: bool) -> str:
        """Format a single component line for the main view."""
        # Calculate counts
        updated = len(status.updated)
        new = len(status.new)
        deleted = len(status.deleted)
        
        # Build status indicators
        indicators = []
        if updated > 0:
            indicators.append(f"↻{updated}")
        if new > 0:
            indicators.append(f"+{new}")
        if deleted > 0:
            indicators.append(f"-{deleted}")
        
        status_str = " ".join(indicators)
        
        # Format the line
        prefix = "▶ " if is_selected else "  "
        component_display = component.replace('_', ' ').title()
        
        # Calculate spacing
        component_width = 25
        status_width = 15
        
        line = f"{prefix}{component_display:<{component_width}}{status_str:>{status_width}}"
        
        # Add description if selected
        if is_selected:
            descriptions = []
            if updated > 0:
                descriptions.append(f"{updated} file{'s' if updated != 1 else ''} to update")
            if new > 0:
                descriptions.append(f"{new} new file{'s' if new != 1 else ''}")
            if deleted > 0:
                descriptions.append(f"{deleted} file{'s' if deleted != 1 else ''} to remove")
            
            if descriptions:
                desc = " - " + ", ".join(descriptions)
                line += self._truncate(desc, self.terminal_width - len(line) - 2)
        
        return line
    
    def _get_file_diff(self, installer: Any, file_path: str) -> Optional[str]:
        """Get diff between source and installed file."""
        if not hasattr(installer, 'update_detector') or not installer.update_detector:
            return None
        
        detector = installer.update_detector
        source_file = detector.source_path / file_path
        installed_file = detector.install_path / file_path
        
        if not source_file.exists() or not installed_file.exists():
            return None
        
        try:
            # Try to use git diff for better output
            result = subprocess.run(
                ['git', 'diff', '--no-index', '--color=always', str(installed_file), str(source_file)],
                capture_output=True,
                text=True
            )
            if result.returncode in (0, 1):  # 0 = no diff, 1 = has diff
                return result.stdout
        except:
            # Fallback to simple diff
            try:
                result = subprocess.run(
                    ['diff', '-u', str(installed_file), str(source_file)],
                    capture_output=True,
                    text=True
                )
                if result.returncode in (0, 1):
                    return result.stdout
            except:
                pass
        
        return None
    
    def _show_file_details(self, component: str, installer: Any, 
                          status: UpdateStatus, file_type: str, file_index: int) -> bool:
        """Show detailed information about a specific file.
        
        Returns:
            True to continue showing details, False to go back
        """
        self._clear_screen()
        
        # Get the file based on type and index
        if file_type == 'updated' and file_index < len(status.updated):
            file_path = status.updated[file_index]
            action = "Update"
        elif file_type == 'new' and file_index < len(status.new):
            file_path = status.new[file_index]
            action = "New"
        elif file_type == 'deleted' and file_index < len(status.deleted):
            file_path = status.deleted[file_index]
            action = "Delete"
        else:
            return False
        
        # Header
        print("=" * self.terminal_width)
        print(self._center_text(f"File Details: {component.title()} - {file_path}"))
        print("=" * self.terminal_width)
        print()
        
        # File info
        print(f"Action: {action}")
        print(f"Path: {file_path}")
        
        # Get metadata if available
        if hasattr(installer, 'update_detector') and installer.update_detector:
            file_info = installer.update_detector.metadata.get(file_path)
            if file_info:
                print(f"Source: {file_info.source}")
                if hasattr(file_info, 'source_hash') and file_info.source_hash:
                    print(f"Hash: {file_info.source_hash[:16]}...")
                if hasattr(file_info, 'source_mtime') and file_info.source_mtime:
                    from datetime import datetime
                    mtime = datetime.fromtimestamp(file_info.source_mtime)
                    print(f"Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # For orphaned files
        if action == "Delete" and 'ethpandaops/' in file_path:
            print("\nReason: Orphaned file (no longer in source repository)")
        
        print()
        
        # Show diff for updates
        if action == "Update":
            print("Changes:")
            print("-" * self.terminal_width)
            diff = self._get_file_diff(installer, file_path)
            if diff:
                # Limit diff output
                lines = diff.split('\n')[:50]
                for line in lines:
                    print(line)
                if len(diff.split('\n')) > 50:
                    print(f"\n... and {len(diff.split('\n')) - 50} more lines ...")
            else:
                print("(Unable to generate diff)")
        
        # For new files, show content preview
        elif action == "New" and hasattr(installer, 'hooks_source'):
            source_file = installer.hooks_source / file_path.replace('.sh', '') / 'hook.sh'
            if source_file.exists():
                print("Content preview:")
                print("-" * self.terminal_width)
                try:
                    with open(source_file, 'r') as f:
                        lines = f.readlines()[:20]
                        for line in lines:
                            print(line.rstrip())
                        if len(f.readlines()) > 20:
                            print("\n... (truncated) ...")
                except:
                    print("(Unable to read file)")
        
        # Navigation
        print()
        print("-" * self.terminal_width)
        print("Press 'b' to go back, 'q' to quit")
        
        while True:
            char = self._get_input_char()
            if char in ('b', 'left', '\x1b'):  # back
                return True
            elif char in ('q', '\x03'):  # quit
                return False
    
    def _show_component_details(self, component: str, installer: Any, 
                               status: UpdateStatus) -> bool:
        """Show detailed view for a specific component.
        
        Returns:
            True to continue, False to go back to main view
        """
        file_lists = []
        if status.updated:
            file_lists.append(('updated', 'Updated Files', status.updated))
        if status.new:
            file_lists.append(('new', 'New Files', status.new))
        if status.deleted:
            file_lists.append(('deleted', 'Files to Remove', status.deleted))
        
        list_index = 0
        file_index = 0
        
        while True:
            self._clear_screen()
            
            # Header
            print("=" * self.terminal_width)
            print(self._center_text(f"{component.replace('_', ' ').title()} Details"))
            print("=" * self.terminal_width)
            print()
            
            # Display current file list
            if list_index < len(file_lists):
                file_type, title, files = file_lists[list_index]
                
                print(f"{title} ({len(files)} files):")
                print("-" * self.terminal_width)
                
                # Show files with pagination
                start_idx = max(0, file_index - 5)
                end_idx = min(len(files), start_idx + 15)
                
                if start_idx > 0:
                    print("  ...")
                
                for i in range(start_idx, end_idx):
                    prefix = "▶ " if i == file_index else "  "
                    file_path = files[i]
                    
                    # Add indicators for special files
                    if file_type == 'deleted' and 'ethpandaops/' in file_path:
                        file_display = f"{file_path} (orphaned)"
                    else:
                        file_display = file_path
                    
                    print(f"{prefix}{self._truncate(file_display, self.terminal_width - 4)}")
                
                if end_idx < len(files):
                    print("  ...")
            
            # Navigation hints
            print()
            print("-" * self.terminal_width)
            nav_parts = ["↑↓: Navigate files", "←→: Switch sections"]
            if file_lists:
                nav_parts.append("Enter: View details")
            nav_parts.extend(["b: Back", "q: Quit"])
            print(self._center_text(" | ".join(nav_parts)))
            
            # Handle input
            char = self._get_input_char()
            
            if char in ('q', '\x03'):  # quit
                return False
            elif char in ('b', '\x1b'):  # back
                return True
            elif char == 'up' and file_lists:
                _, _, files = file_lists[list_index]
                if file_index > 0:
                    file_index -= 1
            elif char == 'down' and file_lists:
                _, _, files = file_lists[list_index]
                if file_index < len(files) - 1:
                    file_index += 1
            elif char == 'left' and list_index > 0:
                list_index -= 1
                file_index = 0
            elif char == 'right' and list_index < len(file_lists) - 1:
                list_index += 1
                file_index = 0
            elif char in ('\r', '\n') and file_lists:  # enter
                file_type, _, _ = file_lists[list_index]
                if not self._show_file_details(component, installer, status, file_type, file_index):
                    return False
    
    def check_and_prompt_updates(self, installers: Dict[str, Any]) -> Optional[Dict[str, UpdateStatus]]:
        """Check for updates and provide interactive exploration.
        
        Args:
            installers: Dictionary of component installers
            
        Returns:
            Dictionary of updates to apply, or None if cancelled
        """
        # Check for updates across all installers
        print("Checking for updates...")
        all_updates = {}
        update_list = []  # List of (component, status) tuples for ordering
        
        for name, installer in installers.items():
            if hasattr(installer, 'check_updates'):
                status = installer.check_updates()
                if status and status.has_changes:
                    all_updates[name] = status
                    update_list.append((name, status))
        
        if not all_updates:
            print("✅ All components are up to date!")
            return {}
        
        # Interactive selection loop
        self.selected_index = 0
        
        while True:
            self._clear_screen()
            
            # Header
            print("=" * self.terminal_width)
            print(self._center_text("🐼 AI Cookbook Update Manager 🐼"))
            print("=" * self.terminal_width)
            print()
            
            # Summary
            total_updated = sum(len(s.updated) for _, s in update_list)
            total_new = sum(len(s.new) for _, s in update_list)
            total_deleted = sum(len(s.deleted) for _, s in update_list)
            
            print(self._center_text(f"Found {total_updated} updates, {total_new} new files, {total_deleted} to remove"))
            print()
            
            # Component list
            print("Components with updates:")
            print("-" * self.terminal_width)
            
            for i, (component, status) in enumerate(update_list):
                is_selected = i == self.selected_index
                line = self._format_component_line(component, status, is_selected)
                print(line)
            
            # Navigation
            print()
            print("-" * self.terminal_width)
            print(self._center_text("↑↓: Navigate | Enter: View Details | y: Apply All | n: Cancel"))
            
            # Handle input
            char = self._get_input_char()
            
            if char in ('q', 'n', '\x03', '\x1b'):  # quit/no
                return None
            elif char == 'y':  # yes - apply all
                return all_updates
            elif char == 'up' and self.selected_index > 0:
                self.selected_index -= 1
            elif char == 'down' and self.selected_index < len(update_list) - 1:
                self.selected_index += 1
            elif char in ('\r', '\n', 'right'):  # enter - show details
                component, status = update_list[self.selected_index]
                installer = installers[component]
                if not self._show_component_details(component, installer, status):
                    return None
    
    def show_update_progress(self, component_type: str, file_name: str, action: str):
        """Show progress for an individual update.
        
        Args:
            component_type: Type of component being updated
            file_name: Name of the file being processed
            action: Action being performed ('update', 'install', 'delete')
        """
        icons = {
            'update': '↻',
            'install': '+',
            'delete': '-'
        }
        
        icon = icons.get(action, '•')
        action_color = {
            'update': '\033[33m',  # yellow
            'install': '\033[32m',  # green
            'delete': '\033[31m'   # red
        }.get(action, '')
        reset_color = '\033[0m'
        
        print(f"  {action_color}{icon} {action.title()} {component_type}/{file_name}{reset_color}")
    
    def show_update_complete(self, total_updated: int, total_installed: int, total_deleted: int):
        """Show completion message after updates.
        
        Args:
            total_updated: Number of files updated
            total_installed: Number of files newly installed
            total_deleted: Number of files deleted
        """
        print()
        print("=" * self.terminal_width)
        parts = []
        if total_updated > 0:
            parts.append(f"{total_updated} updated")
        if total_installed > 0:
            parts.append(f"{total_installed} installed")
        if total_deleted > 0:
            parts.append(f"{total_deleted} deleted")
        
        if parts:
            message = f"✅ Updates complete: {', '.join(parts)}"
            print(self._center_text(message))
        print("=" * self.terminal_width)
        print()