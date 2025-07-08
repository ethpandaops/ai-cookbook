"""TUI-style update interface matching the main ai-cookbook UI."""

import os
import sys
import termios
import tty
import signal
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from .detector import UpdateStatus
from ..config.settings import ORG_DISPLAY_NAME, VERSION
# Removed BaseInstaller import to avoid circular dependency

# Import the Colors and utility functions from main TUI
from ..tui import Colors, getch, clear_screen


class TUIUpdateUI:
    """TUI-style update interface matching ai-cookbook's main UI."""
    
    def __init__(self):
        self.selected_component = 0
        self.selected_file = 0
        self.current_view = 'main'  # 'main', 'component', 'file'
        self.current_component = None
        self.current_status = None
        self.current_file_list = []
        self.current_file_type = None
        
    def _draw_header(self):
        """Draw the header section."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}🐼 {ORG_DISPLAY_NAME} AI Cookbook - Update Manager{Colors.NC}")
        print(f"Version: {Colors.GREEN}v{VERSION}{Colors.NC}\n")
    
    def _draw_main_view(self, all_updates: Dict[str, Tuple[str, UpdateStatus, Any]]):
        """Draw the main update overview."""
        clear_screen()
        self._draw_header()
        
        # Summary
        total_updated = sum(len(status.updated) for _, status, _ in all_updates.values())
        total_new = sum(len(status.new) for _, status, _ in all_updates.values())
        total_deleted = sum(len(status.deleted) for _, status, _ in all_updates.values())
        
        print(f"{Colors.BOLD}Update Summary{Colors.NC}")
        print(f"{Colors.DIM}Found {total_updated} updates, {total_new} new files, {total_deleted} to remove{Colors.NC}\n")
        
        # Components list
        print(f"{Colors.BOLD}Components with Updates{Colors.NC}")
        print(f"{Colors.DIM}Select a component to view details{Colors.NC}")
        
        components = list(all_updates.keys())
        for i, component in enumerate(components):
            _, status, _ = all_updates[component]
            
            # Format counts
            counts = []
            if len(status.updated) > 0:
                counts.append(f"{len(status.updated)} updated")
            if len(status.new) > 0:
                counts.append(f"{len(status.new)} new")
            if len(status.deleted) > 0:
                counts.append(f"{len(status.deleted)} removed")
            
            count_str = ", ".join(counts)
            display_name = component.replace('_', ' ').title()
            
            if i == self.selected_component:
                print(f"   {Colors.REVERSE}{display_name:<30} {count_str:<50}{Colors.NC}")
            else:
                print(f"   {display_name:<30} {count_str:<50}")
        
        # Divider
        print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
        
        # Selected component description
        selected_name = components[self.selected_component]
        _, status, _ = all_updates[selected_name]
        print(f"\n{Colors.BOLD}Selected:{Colors.NC} {selected_name.replace('_', ' ').title()}")
        
        changes = []
        if len(status.updated) > 0:
            changes.append(f"{len(status.updated)} file{'s' if len(status.updated) != 1 else ''} have been modified")
        if len(status.new) > 0:
            changes.append(f"{len(status.new)} new file{'s' if len(status.new) != 1 else ''} available")
        if len(status.deleted) > 0:
            changes.append(f"{len(status.deleted)} file{'s' if len(status.deleted) != 1 else ''} to remove")
        
        if changes:
            print(f"{Colors.DIM}{', '.join(changes)}{Colors.NC}")
        
        # Actions
        print(f"\n{Colors.BOLD}Actions:{Colors.NC}")
        print(f"  {Colors.CYAN}↑/↓{Colors.NC}     Navigate components")
        print(f"  {Colors.CYAN}Enter/→{Colors.NC} View component details")
        print(f"  {Colors.CYAN}a{Colors.NC}       Apply all updates")
        print(f"  {Colors.CYAN}q/←{Colors.NC}     Cancel")
    
    def _draw_component_view(self, component: str, status: UpdateStatus, installer: Any):
        """Draw the component detail view."""
        clear_screen()
        self._draw_header()
        
        print(f"{Colors.BOLD}{component.replace('_', ' ').title()} Updates{Colors.NC}")
        print(f"{Colors.DIM}Browse files to update{Colors.NC}\n")
        
        # Build file lists
        file_sections = []
        if status.updated:
            file_sections.append(('Updated Files', status.updated, 'update'))
        if status.new:
            file_sections.append(('New Files', status.new, 'new'))
        if status.deleted:
            file_sections.append(('Files to Remove', status.deleted, 'delete'))
        
        # Calculate total files to ensure selected_file is in bounds
        total_files = sum(len(files) for _, files, _ in file_sections)
        if self.selected_file >= total_files:
            self.selected_file = max(0, total_files - 1)
        
        # Display files
        current_index = 0
        for section_title, files, file_type in file_sections:
            print(f"{Colors.BOLD}{section_title}{Colors.NC} ({len(files)})")
            
            for i, file_path in enumerate(files[:10]):  # Show max 10 per section
                is_selected = current_index == self.selected_file
                
                # Add indicators
                if file_type == 'delete' and 'ethpandaops/' in file_path:
                    display_text = f"{file_path} (orphaned)"
                else:
                    display_text = file_path
                
                if is_selected:
                    print(f"   {Colors.REVERSE}{display_text:<80}{Colors.NC}")
                    self.current_file_list = files
                    self.current_file_type = file_type
                else:
                    print(f"   {display_text:<80}")
                
                current_index += 1
            
            if len(files) > 10:
                print(f"   {Colors.DIM}... and {len(files) - 10} more{Colors.NC}")
            print()
        
        # Divider
        print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
        
        # Selected file info
        if self.current_file_list and self.selected_file < len(self.current_file_list):
            selected_file = self.current_file_list[self.selected_file]
            print(f"\n{Colors.BOLD}Selected:{Colors.NC} {selected_file}")
            
            if self.current_file_type == 'update':
                print(f"{Colors.DIM}This file has been modified in the source repository{Colors.NC}")
            elif self.current_file_type == 'new':
                print(f"{Colors.DIM}This is a new file available to install{Colors.NC}")
            elif self.current_file_type == 'delete':
                if 'ethpandaops/' in selected_file:
                    print(f"{Colors.DIM}This file is no longer in the source repository (orphaned){Colors.NC}")
                else:
                    print(f"{Colors.DIM}This file will be removed{Colors.NC}")
        
        # Actions
        print(f"\n{Colors.BOLD}Actions:{Colors.NC}")
        print(f"  {Colors.CYAN}↑/↓{Colors.NC}     Navigate files")
        print(f"  {Colors.CYAN}Enter/→{Colors.NC} View file details")
        print(f"  {Colors.CYAN}a{Colors.NC}       Apply {component.replace('_', ' ')} updates")
        print(f"  {Colors.CYAN}q/←{Colors.NC}     Back to components")
    
    def _draw_file_view(self, component: str, file_path: str, file_type: str, 
                       installer: Any, status: UpdateStatus):
        """Draw the file detail view."""
        clear_screen()
        self._draw_header()
        
        action_map = {'update': 'Update', 'new': 'New File', 'delete': 'Remove'}
        action = action_map.get(file_type, 'Unknown')
        
        print(f"{Colors.BOLD}File Details - {action}{Colors.NC}")
        print(f"{Colors.DIM}{component.replace('_', ' ').title()}{Colors.NC}\n")
        
        print(f"{Colors.BOLD}File:{Colors.NC} {file_path}")
        print(f"{Colors.BOLD}Action:{Colors.NC} {action}")
        
        # Get metadata if available
        if hasattr(installer, 'update_detector') and installer.update_detector:
            file_info = installer.update_detector.metadata.get(file_path)
            if file_info:
                print(f"{Colors.BOLD}Source:{Colors.NC} {file_info.source}")
                if hasattr(file_info, 'source_hash') and file_info.source_hash:
                    print(f"{Colors.BOLD}Hash:{Colors.NC} {file_info.source_hash[:32]}...")
        
        # Show reason for deletion
        if file_type == 'delete' and 'ethpandaops/' in file_path:
            print(f"\n{Colors.YELLOW}Reason:{Colors.NC} This file is no longer in the source repository")
            print(f"{Colors.DIM}It appears to be an orphaned file that should be cleaned up{Colors.NC}")
        
        # Show diff preview for updates
        if file_type == 'update':
            print(f"\n{Colors.BOLD}Changes:{Colors.NC}")
            print(f"{Colors.DIM}A diff will be shown here in a future update{Colors.NC}")
            print(f"{Colors.DIM}For now, the file will be updated to match the source{Colors.NC}")
        
        # Divider
        print(f"\n{Colors.DIM}─────────────────────────────────────────────────────────────────────────────────────{Colors.NC}")
        
        # Actions
        print(f"\n{Colors.BOLD}Actions:{Colors.NC}")
        print(f"  {Colors.CYAN}a{Colors.NC}       Apply this {action.lower()}")
        print(f"  {Colors.CYAN}q/←{Colors.NC}     Back to file list")
    
    def _apply_updates(self, updates_to_apply: Dict[str, UpdateStatus], all_installers: Dict[str, Any]):
        """Apply the specified updates and show progress.
        
        Args:
            updates_to_apply: Dictionary of component -> UpdateStatus to apply
            all_installers: All available installers
        """
        print("\nApplying updates...")
        
        total_updated = 0
        total_installed = 0
        total_deleted = 0
        
        for component_type, status in updates_to_apply.items():
            installer = all_installers[component_type]
            
            # Process updates
            for file_name in status.updated:
                self.show_update_progress(component_type, file_name, 'update')
                
                # Apply the actual update using the installer's methods
                if hasattr(installer, 'install_command'):
                    # Commands installer
                    installer.install_command(file_name)
                elif hasattr(installer, 'apply_hook_update'):
                    # Use the new method that handles project-specific hooks
                    installer.apply_hook_update(file_name)
                elif hasattr(installer, 'install_hook'):
                    # Fallback for other hook-like installers
                    hook_name = file_name.replace('.sh', '')
                    installer.install_hook(hook_name)
                elif hasattr(installer, 'install_language'):
                    # Code standards installer
                    language = file_name.split('/')[0]
                    installer.install_language(language)
                elif hasattr(installer, 'update_detector') and installer.update_detector:
                    # Generic file update
                    installer.update_detector.apply_update(file_name)
                
                total_updated += 1
            
            # Process new files
            for file_name in status.new:
                self.show_update_progress(component_type, file_name, 'install')
                
                # Same logic as updates
                if hasattr(installer, 'install_command'):
                    installer.install_command(file_name)
                elif hasattr(installer, 'apply_hook_update'):
                    # Use the new method that handles project-specific hooks
                    installer.apply_hook_update(file_name)
                elif hasattr(installer, 'install_hook'):
                    # Fallback for other hook-like installers
                    hook_name = file_name.replace('.sh', '')
                    installer.install_hook(hook_name)
                elif hasattr(installer, 'install_language'):
                    # Code standards installer - extract language from path
                    language = file_name.split('/')[0]
                    installer.install_language(language)
                elif hasattr(installer, 'update_detector') and installer.update_detector:
                    # Generic file install
                    installer.update_detector.apply_update(file_name)
                
                total_installed += 1
            
            # Process deletions
            for file_name in status.deleted:
                self.show_update_progress(component_type, file_name, 'delete')
                
                # Handle deletion based on component type
                if 'ethpandaops/' in file_name and hasattr(installer, 'update_detector') and installer.update_detector:
                    # This is an orphaned file in ethpandaops directory
                    file_path = installer.update_detector.install_path / file_name
                    if file_path.exists():
                        # Delete file or directory
                        if file_path.is_dir():
                            import shutil
                            shutil.rmtree(file_path)
                        else:
                            file_path.unlink()
                        
                        # Remove metadata
                        installer.update_detector.remove_metadata(file_name)
                else:
                    # Use installer-specific uninstall methods
                    if hasattr(installer, 'uninstall_command'):
                        # Commands installer
                        installer.uninstall_command(file_name)
                    elif hasattr(installer, 'uninstall_hook'):
                        # Hooks installer - handle both global and project-specific
                        if file_name.startswith('[') and '] ' in file_name:
                            # Project-specific hook like "[platform] ast-grep.sh"
                            # Use apply_hook_update which handles uninstalls too
                            # Actually, for deletions we need a different approach
                            project_end = file_name.index('] ')
                            project_name = file_name[1:project_end]
                            actual_file = file_name[project_end + 2:]
                            hook_name = actual_file.replace('.sh', '')
                            
                            # Find the project and uninstall the hook
                            for project_path in installer.project_registry.get_projects_with_component('hooks'):
                                if project_path.name == project_name:
                                    original_cwd = Path.cwd()
                                    try:
                                        import os
                                        os.chdir(project_path)
                                        installer.uninstall_hook(hook_name, mode="local")
                                    finally:
                                        os.chdir(original_cwd)
                                    break
                        else:
                            # Regular global hook
                            hook_name = file_name.replace('.sh', '')
                            installer.uninstall_hook(hook_name, mode="global")
                    elif hasattr(installer, 'uninstall_language'):
                        # Code standards installer
                        language = file_name.split('/')[0]
                        installer.uninstall_language(language)
                    elif hasattr(installer, 'update_detector') and installer.update_detector:
                        # Generic file deletion
                        installer.update_detector.delete_file(file_name)
                
                total_deleted += 1
        
        self.show_update_complete(total_updated, total_installed, total_deleted)
    
    def check_and_prompt_updates(self, installers: Dict[str, Any]) -> Optional[Dict[str, UpdateStatus]]:
        """Check for updates and provide TUI-style interface.
        
        Args:
            installers: Dictionary of component installers
            
        Returns:
            Dictionary of updates to apply, or None if cancelled
        """
        print("Checking for updates...")
        
        # Check for updates across all installers
        all_updates = {}
        for name, installer in installers.items():
            if hasattr(installer, 'check_updates'):
                status = installer.check_updates()
                if status and status.has_changes:
                    all_updates[name] = (name, status, installer)
        
        if not all_updates:
            print("✅ All components are up to date!")
            return {}
        
        # Interactive loop
        self.selected_component = 0
        self.selected_file = 0
        self.current_view = 'main'
        all_updates_to_apply = {}  # Track what to apply at the end
        
        try:
            while True:
                # Remove already applied updates from the display
                remaining_updates = {}
                for name, (orig_name, status, installer) in all_updates.items():
                    # Create a new status with only remaining changes
                    remaining_updated = [f for f in status.updated if name not in all_updates_to_apply or f not in all_updates_to_apply.get(name, UpdateStatus([], [], [], [])).updated]
                    remaining_new = [f for f in status.new if name not in all_updates_to_apply or f not in all_updates_to_apply.get(name, UpdateStatus([], [], [], [])).new]
                    remaining_deleted = [f for f in status.deleted if name not in all_updates_to_apply or f not in all_updates_to_apply.get(name, UpdateStatus([], [], [], [])).deleted]
                    
                    if remaining_updated or remaining_new or remaining_deleted:
                        remaining_status = UpdateStatus(remaining_updated, remaining_new, remaining_deleted, status.unchanged)
                        remaining_updates[name] = (orig_name, remaining_status, installer)
                
                # If no more updates, return what was selected
                if not remaining_updates:
                    return all_updates_to_apply if all_updates_to_apply else {}
                
                # Adjust selected component if needed
                if self.selected_component >= len(remaining_updates):
                    self.selected_component = max(0, len(remaining_updates) - 1)
                
                if self.current_view == 'main':
                    self._draw_main_view(remaining_updates)
                elif self.current_view == 'component':
                    if self.current_component in remaining_updates:
                        self._draw_component_view(
                            self.current_component, 
                            remaining_updates[self.current_component][1],
                            remaining_updates[self.current_component][2]
                        )
                    else:
                        # Component fully applied, go back to main
                        self.current_view = 'main'
                        continue
                elif self.current_view == 'file':
                    if self.current_file_list and self.selected_file < len(self.current_file_list):
                        self._draw_file_view(
                            self.current_component,
                            self.current_file_list[self.selected_file],
                            self.current_file_type,
                            remaining_updates[self.current_component][2],
                            remaining_updates[self.current_component][1]
                        )
                
                # Get user input
                key = getch()
                
                if key == '\x03':  # Ctrl+C
                    return None
                
                if self.current_view == 'main':
                    if key == 'UP' and self.selected_component > 0:
                        self.selected_component -= 1
                    elif key == 'DOWN' and self.selected_component < len(remaining_updates) - 1:
                        self.selected_component += 1
                    elif key == 'a':  # Apply all updates
                        # Apply all remaining updates
                        updates_dict = {name: status for name, (_, status, _) in remaining_updates.items()}
                        self._apply_updates(updates_dict, installers)
                        # Add to accumulated updates
                        for name, (_, status, _) in remaining_updates.items():
                            if name not in all_updates_to_apply:
                                all_updates_to_apply[name] = status
                            else:
                                # Merge with existing
                                existing = all_updates_to_apply[name]
                                all_updates_to_apply[name] = UpdateStatus(
                                    existing.updated + status.updated,
                                    existing.new + status.new,
                                    existing.deleted + status.deleted,
                                    existing.unchanged
                                )
                    elif key == 'q' or key == 'LEFT':  # Cancel
                        return all_updates_to_apply if all_updates_to_apply else None
                    elif key in ('\r', '\n', 'RIGHT'):  # Enter component view
                        components = list(remaining_updates.keys())
                        self.current_component = components[self.selected_component]
                        self.current_status = remaining_updates[self.current_component][1]
                        self.selected_file = 0
                        self.current_view = 'component'
                
                elif self.current_view == 'component':
                    # Recheck if component still exists in remaining updates
                    if self.current_component not in remaining_updates:
                        self.current_view = 'main'
                        continue
                        
                    # Update current status from remaining updates
                    self.current_status = remaining_updates[self.current_component][1]
                    
                    # Count total files to navigate
                    total_files = (len(self.current_status.updated) + 
                                 len(self.current_status.new) + 
                                 len(self.current_status.deleted))
                    
                    if key == 'UP' and self.selected_file > 0:
                        self.selected_file -= 1
                    elif key == 'DOWN' and self.selected_file < total_files - 1:
                        self.selected_file += 1
                    elif key == 'a':  # Apply component updates
                        # Apply this component's updates
                        component_updates = {self.current_component: self.current_status}
                        self._apply_updates(component_updates, installers)
                        
                        # Add to accumulated updates
                        if self.current_component not in all_updates_to_apply:
                            all_updates_to_apply[self.current_component] = self.current_status
                        else:
                            # Merge with existing
                            existing = all_updates_to_apply[self.current_component]
                            all_updates_to_apply[self.current_component] = UpdateStatus(
                                existing.updated + self.current_status.updated,
                                existing.new + self.current_status.new,
                                existing.deleted + self.current_status.deleted,
                                existing.unchanged
                            )
                        
                        # Go back to main view
                        self.current_view = 'main'
                        self.selected_file = 0
                    elif key == 'q' or key == 'LEFT':  # Back
                        self.current_view = 'main'
                    elif key in ('\r', '\n', 'RIGHT'):  # View file details
                        self.current_view = 'file'
                
                elif self.current_view == 'file':
                    if key == 'a':  # Apply this single file update
                        # Create a custom UpdateStatus with just this file
                        if self.current_file_list and self.selected_file < len(self.current_file_list):
                            file_path = self.current_file_list[self.selected_file]
                            
                            # Create minimal update status for just this file
                            if self.current_file_type == 'update':
                                single_status = UpdateStatus([file_path], [], [], [])
                            elif self.current_file_type == 'new':
                                single_status = UpdateStatus([], [file_path], [], [])
                            elif self.current_file_type == 'delete':
                                single_status = UpdateStatus([], [], [file_path], [])
                            
                            # Apply this single file
                            single_updates = {self.current_component: single_status}
                            self._apply_updates(single_updates, installers)
                            
                            # Add to accumulated updates
                            if self.current_component not in all_updates_to_apply:
                                all_updates_to_apply[self.current_component] = single_status
                            else:
                                # Merge with existing
                                existing = all_updates_to_apply[self.current_component]
                                if self.current_file_type == 'update':
                                    existing.updated.append(file_path)
                                elif self.current_file_type == 'new':
                                    existing.new.append(file_path)
                                elif self.current_file_type == 'delete':
                                    existing.deleted.append(file_path)
                            
                            # Go back to component view
                            self.current_view = 'component'
                            # Adjust selected_file index if it's now out of bounds
                            # The file list will be rebuilt from remaining updates
                            # so we should reset or adjust the selection
                            if self.selected_file > 0:
                                self.selected_file = max(0, self.selected_file - 1)
                    elif key == 'q' or key == 'LEFT':  # Back
                        self.current_view = 'component'
                        
        except KeyboardInterrupt:
            return None
        finally:
            print(Colors.SHOW_CURSOR)
    
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
        colors = {
            'update': Colors.YELLOW,
            'install': Colors.GREEN,
            'delete': Colors.RED
        }
        
        icon = icons.get(action, '•')
        color = colors.get(action, Colors.WHITE)
        
        print(f"  {color}{icon}{Colors.NC} {action.title()} {component_type}/{file_name}")
    
    def show_update_complete(self, total_updated: int, total_installed: int, total_deleted: int):
        """Show completion message after updates.
        
        Args:
            total_updated: Number of files updated
            total_installed: Number of files newly installed
            total_deleted: Number of files deleted
        """
        print(f"\n{Colors.GREEN}✓{Colors.NC} Updates complete!")
        
        parts = []
        if total_updated > 0:
            parts.append(f"{total_updated} updated")
        if total_installed > 0:
            parts.append(f"{total_installed} installed")
        if total_deleted > 0:
            parts.append(f"{total_deleted} deleted")
        
        if parts:
            print(f"  {Colors.DIM}{', '.join(parts)}{Colors.NC}")
        print()