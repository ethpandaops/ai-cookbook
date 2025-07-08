"""Hooks installer for PandaOps Cookbook."""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..installers.base import InteractiveInstaller, InstallationResult
from ..utils.file_operations import (
    ensure_directory, copy_files, file_exists, directory_exists,
    list_files, read_json_file, write_json_file
)
from ..utils.system import run_command
from ..config.settings import CLAUDE_DIR
from ..updaters.detector import UpdateStatus

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class HooksInstaller(InteractiveInstaller):
    """Installer for Claude Code hooks integration.
    
    Manages installation of hooks that run automated checks after file edits.
    Supports both global and local installation modes.
    """
    
    def __init__(self) -> None:
        """Initialize hooks installer."""
        super().__init__(
            name="Hooks",
            description="Install Claude Code hooks for automated checks"
        )
        self.hooks_source = PROJECT_ROOT / "claude-code" / "hooks"
        self.current_mode = "global"  # Default to global mode
        
        # Initialize update detector for hooks in ethpandaops directory
        from ..config.settings import CLAUDE_HOOKS_DIR
        self.initialize_update_detector(self.hooks_source, CLAUDE_HOOKS_DIR)
        
        # Initialize project registry for tracking local installations
        from ..project_registry import ProjectRegistry
        self.project_registry = ProjectRegistry()
        
    def check_status(self) -> Dict[str, Any]:
        """Check installation status of hooks.
        
        Returns:
            Dictionary with status information:
            - installed: Whether any hooks are installed
            - global_hooks: List of globally installed hooks
            - local_hooks: List of locally installed hooks
            - available_hooks: List of available hooks to install
            - mode: Current installation mode
        """
        global_hooks = self._get_installed_hooks("global")
        local_hooks = self._get_installed_hooks("local")
        available_hooks = self.get_available_hooks()
        
        return {
            'installed': bool(global_hooks or local_hooks),
            'global_hooks': global_hooks,
            'local_hooks': local_hooks,
            'available_hooks': available_hooks,
            'mode': self.current_mode,
            'global_settings': str(self._get_settings_path("global")),
            'local_settings': str(self._get_settings_path("local"))
        }
        
    def install(self) -> InstallationResult:
        """Install all hooks (interactive mode message).
        
        Returns:
            InstallationResult with message directing to interactive mode
        """
        return InstallationResult(
            False,
            "Hooks installation requires interactive mode. Use the interactive menu to install specific hooks.",
            {'hint': 'Select this installer from the main menu for interactive options'}
        )
        
    def uninstall(self) -> InstallationResult:
        """Uninstall all hooks.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            removed_hooks = []
            errors = []
            
            # Uninstall from both global and local
            for mode in ["global", "local"]:
                installed_hooks = self._get_installed_hooks(mode)
                for hook_name in installed_hooks:
                    try:
                        self.uninstall_hook(hook_name, mode)
                        removed_hooks.append(f"{hook_name} ({mode})")
                    except Exception as e:
                        errors.append(f"Failed to uninstall {hook_name} ({mode}): {str(e)}")
            
            if errors:
                return InstallationResult(
                    False,
                    "Some hooks could not be uninstalled",
                    {'removed': removed_hooks, 'errors': errors}
                )
            
            if not removed_hooks:
                return InstallationResult(
                    True,
                    "No hooks were installed",
                    {}
                )
                
            return InstallationResult(
                True,
                f"Successfully uninstalled {len(removed_hooks)} hooks",
                {'removed': removed_hooks}
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Uninstallation failed: {str(e)}"
            )
            
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about hooks.
        
        Returns:
            Dictionary with detailed installer information
        """
        status = self.check_status()
        
        # Get detailed info for each available hook
        hook_details = {}
        for hook_name in status['available_hooks']:
            hook_info = self._get_hook_info(hook_name)
            if hook_info:
                hook_details[hook_name] = hook_info
                
        # Add installation status to hook details
        for hook_name in hook_details:
            hook_details[hook_name]['installed_global'] = hook_name in status['global_hooks']
            hook_details[hook_name]['installed_local'] = hook_name in status['local_hooks']
                
        return {
            'name': self.name,
            'description': self.description,
            'installed': status['installed'],
            'global_hooks': status['global_hooks'],
            'local_hooks': status['local_hooks'],
            'available_hooks': status['available_hooks'],
            'status': status,
            'paths': {
                'hooks_source': str(self.hooks_source),
                'global_hooks_dir': str(self._get_hooks_dir("global")),
                'local_hooks_dir': str(self._get_hooks_dir("local")),
                'global_settings': status['global_settings'],
                'local_settings': status['local_settings']
            },
            'hooks': hook_details,
            'current_mode': self.current_mode,
            'mode_display': f"Current mode: {self.current_mode.upper()}"
        }
        
    def get_hook_info(self, hook_name: str) -> Dict[str, Any]:
        """Get information about a specific hook (public method for TUI).
        
        Args:
            hook_name: Name of the hook
            
        Returns:
            Dictionary with hook information
        """
        hook_info = self._get_hook_info(hook_name)
        if hook_info:
            return hook_info
        return {
            'description': 'No description available',
            'hook_type': 'PostToolUse',
            'matcher': 'No matcher'
        }
        
    def get_available_hooks(self) -> List[str]:
        """Get list of available hooks.
        
        Returns:
            List of available hook names
        """
        hooks = []
        if self.hooks_source.exists():
            for hook_dir in self.hooks_source.iterdir():
                if hook_dir.is_dir():
                    config_file = hook_dir / "config.json"
                    hook_script = hook_dir / "hook.sh"
                    if config_file.exists() and hook_script.exists():
                        hooks.append(hook_dir.name)
        return sorted(hooks)
        
    def install_hook(self, hook_name: str, mode: Optional[str] = None) -> InstallationResult:
        """Install a specific hook.
        
        Args:
            hook_name: Name of the hook to install
            mode: Installation mode ("global" or "local"), uses current_mode if not specified
            
        Returns:
            InstallationResult indicating success/failure
        """
        if mode is None:
            mode = self.current_mode
            
        try:
            hook_dir = self.hooks_source / hook_name
            hook_config = hook_dir / "config.json"
            hook_script = hook_dir / "hook.sh"
            
            # Validate hook files
            if not hook_script.exists():
                return InstallationResult(
                    False,
                    f"Hook '{hook_name}' missing hook.sh"
                )
                
            if not hook_config.exists():
                return InstallationResult(
                    False,
                    f"Hook '{hook_name}' missing config.json"
                )
                
            # Check dependencies
            deps_result = self._check_hook_dependencies(hook_name)
            if not deps_result['success']:
                return InstallationResult(
                    False,
                    f"Dependencies not met for {hook_name}",
                    deps_result
                )
                
            # Get paths for the mode
            hooks_dir = self._get_hooks_dir(mode)
            settings_path = self._get_settings_path(mode)
            
            # Create directories
            ensure_directory(hooks_dir)
            ensure_directory(settings_path.parent)
            
            # Copy hook script
            installed_hook_path = hooks_dir / f"{hook_name}.sh"
            shutil.copy2(hook_script, installed_hook_path)
            installed_hook_path.chmod(0o755)
            
            # Update metadata for the hook
            if 'ethpandaops' in str(hooks_dir):
                # For local installations, create a separate update detector
                if mode == "local":
                    from ..updaters.detector import UpdateDetector
                    local_detector = UpdateDetector(self.hooks_source, hooks_dir)
                    hook_file_name = f"{hook_name}.sh"
                    local_detector.update_metadata(hook_file_name, hook_script)
                elif self.update_detector:
                    # Store just the installed filename, not the source path
                    hook_file_name = f"{hook_name}.sh"
                    # Pass the source hook.sh file, not the hook directory
                    self.update_detector.update_metadata(hook_file_name, hook_script)
            
            # Read hook configuration
            config = read_json_file(hook_config)
            hook_type = config.get('hook_type', 'PostToolUse')
            matcher = config.get('matcher', '')
            
            # Add hook to settings
            self._add_hook_to_settings(hook_name, hook_type, matcher, str(installed_hook_path), mode)
            
            # Register project if installing locally
            if mode == "local":
                self.project_registry.register_project(Path.cwd(), ['hooks'])
            
            return InstallationResult(
                True,
                f"Successfully installed hook: {hook_name} ({mode})",
                {
                    'hook': hook_name,
                    'mode': mode,
                    'location': str(installed_hook_path),
                    'hook_type': hook_type
                }
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install hook {hook_name}: {str(e)}"
            )
            
    def uninstall_hook(self, hook_name: str, mode: Optional[str] = None) -> InstallationResult:
        """Uninstall a specific hook.
        
        Args:
            hook_name: Name of the hook to uninstall
            mode: Installation mode ("global" or "local"), uses current_mode if not specified
            
        Returns:
            InstallationResult indicating success/failure
        """
        if mode is None:
            mode = self.current_mode
            
        try:
            hooks_dir = self._get_hooks_dir(mode)
            installed_hook_path = hooks_dir / f"{hook_name}.sh"
            
            # Remove from settings
            self._remove_hook_from_settings(hook_name, mode)
            
            # Remove hook script
            if installed_hook_path.exists():
                installed_hook_path.unlink()
            
            # Remove metadata
            if 'ethpandaops' in str(hooks_dir):
                hook_file_name = f"{hook_name}.sh"
                if mode == "local":
                    from ..updaters.detector import UpdateDetector
                    local_detector = UpdateDetector(self.hooks_source, hooks_dir)
                    local_detector.remove_metadata(hook_file_name)
                elif self.update_detector:
                    self.update_detector.remove_metadata(hook_file_name)
            
            # Check if this was the last local hook and unregister project if so
            if mode == "local":
                remaining_hooks = self._get_installed_hooks("local")
                if not remaining_hooks:
                    self.project_registry.unregister_project(Path.cwd(), ['hooks'])
                
            return InstallationResult(
                True,
                f"Successfully uninstalled hook: {hook_name} ({mode})",
                {'hook': hook_name, 'mode': mode}
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall hook {hook_name}: {str(e)}"
            )
            
    def set_mode(self, mode: str) -> None:
        """Set installation mode.
        
        Args:
            mode: Installation mode ("global" or "local")
        """
        if mode in ["global", "local"]:
            self.current_mode = mode
            self.refresh_options()
            
    def build_interactive_options(self) -> None:
        """Build interactive options based on current state."""
        self.clear_interactive_options()
        
        # Add mode toggle option
        other_mode = "local" if self.current_mode == "global" else "global"
        self.add_interactive_option(
            f"Switch to {other_mode} mode",
            f"Change installation mode from {self.current_mode} to {other_mode}",
            lambda: self.set_mode(other_mode)
        )
        
        # Get current status
        status = self.check_status()
        local_hooks = self._get_installed_hooks("local")
        global_hooks = self._get_installed_hooks("global")
        available_hooks = status['available_hooks']
        
        # Import Colors for styling
        from ..tui import Colors
        
        # Add install/uninstall options for each hook
        for hook_name in available_hooks:
            hook_info = self._get_hook_info(hook_name)
            base_description = hook_info.get('description', 'No description available') if hook_info else 'No description available'
            
            # Check installation status
            is_local = hook_name in local_hooks
            is_global = hook_name in global_hooks
            
            # Build status indicators
            status_parts = []
            if is_global:
                status_parts.append(f"{Colors.CYAN}[GLOBAL]{Colors.NC}")
            if is_local:
                status_parts.append(f"{Colors.GREEN}[LOCAL]{Colors.NC}")
            
            status_suffix = f" {' '.join(status_parts)}" if status_parts else ""
            
            # In LOCAL mode
            if self.current_mode == "local":
                if not is_local:
                    # Can install locally regardless of global status
                    self.add_interactive_option(
                        f"Install {hook_name}{status_suffix}",
                        base_description,
                        lambda h=hook_name: self.install_hook(h, mode="local")
                    )
                else:
                    # Can only uninstall from local
                    self.add_interactive_option(
                        f"Uninstall {hook_name} (local only){status_suffix}",
                        f"Remove {hook_name} hook from local configuration",
                        lambda h=hook_name: self.uninstall_hook(h, mode="local")
                    )
            
            # In GLOBAL mode
            elif self.current_mode == "global":
                if not is_global:
                    # Can install globally regardless of local status
                    self.add_interactive_option(
                        f"Install {hook_name}{status_suffix}",
                        base_description,
                        lambda h=hook_name: self.install_hook(h, mode="global")
                    )
                else:
                    # Can only uninstall from global
                    self.add_interactive_option(
                        f"Uninstall {hook_name}{status_suffix}",
                        f"Remove {hook_name} hook from global configuration",
                        lambda h=hook_name: self.uninstall_hook(h, mode="global")
                    )
            
        # Add install all option if there are uninstalled hooks in current mode
        current_mode_hooks = local_hooks if self.current_mode == "local" else global_hooks
        uninstalled_here = [h for h in available_hooks if h not in current_mode_hooks]
        if uninstalled_here:
            self.add_interactive_option(
                f"Install all hooks ({self.current_mode})",
                f"Install all {len(uninstalled_here)} available hooks in {self.current_mode} mode",
                self._install_all_hooks
            )
            
        # Add uninstall all option if there are installed hooks in current mode
        if current_mode_hooks:
            self.add_interactive_option(
                f"Uninstall all {self.current_mode} hooks",
                f"Remove all {len(current_mode_hooks)} hooks from {self.current_mode} configuration",
                self._uninstall_all_hooks
            )
            
    def _install_all_hooks(self) -> InstallationResult:
        """Install all available hooks."""
        status = self.check_status()
        installed_hooks = self._get_installed_hooks(self.current_mode)
        available_hooks = status['available_hooks']
        uninstalled = [h for h in available_hooks if h not in installed_hooks]
        
        results = []
        for hook_name in uninstalled:
            result = self.install_hook(hook_name)
            results.append((hook_name, result))
            
        successful = [h for h, r in results if r.success]
        failed = [h for h, r in results if not r.success]
        
        if failed:
            return InstallationResult(
                False,
                f"Installed {len(successful)} hooks, {len(failed)} failed",
                {'successful': successful, 'failed': failed}
            )
        
        return InstallationResult(
            True,
            f"Successfully installed {len(successful)} hooks",
            {'installed': successful}
        )
        
    def _uninstall_all_hooks(self) -> InstallationResult:
        """Uninstall all hooks for current mode."""
        installed_hooks = self._get_installed_hooks(self.current_mode)
        
        results = []
        for hook_name in installed_hooks:
            result = self.uninstall_hook(hook_name)
            results.append((hook_name, result))
            
        successful = [h for h, r in results if r.success]
        failed = [h for h, r in results if not r.success]
        
        if failed:
            return InstallationResult(
                False,
                f"Uninstalled {len(successful)} hooks, {len(failed)} failed",
                {'successful': successful, 'failed': failed}
            )
        
        return InstallationResult(
            True,
            f"Successfully uninstalled {len(successful)} hooks",
            {'uninstalled': successful}
        )
        
    def _get_hooks_dir(self, mode: str) -> Path:
        """Get hooks directory based on mode.
        
        Args:
            mode: Installation mode ("global" or "local")
            
        Returns:
            Path to hooks directory
        """
        if mode == "local":
            return Path.cwd() / ".claude" / "hooks" / "ethpandaops"
        else:
            return CLAUDE_DIR / "hooks" / "ethpandaops"
            
    def _get_settings_path(self, mode: str) -> Path:
        """Get settings file path based on mode.
        
        Args:
            mode: Installation mode ("global" or "local")
            
        Returns:
            Path to settings file
        """
        if mode == "local":
            return Path.cwd() / ".claude" / "settings.local.json"
        else:
            return CLAUDE_DIR / "settings.json"
            
    def _get_installed_hooks(self, mode: str) -> List[str]:
        """Get list of installed hooks for mode.
        
        Args:
            mode: Installation mode ("global" or "local")
            
        Returns:
            List of installed hook names
        """
        settings_path = self._get_settings_path(mode)
        if not settings_path.exists():
            return []
            
        try:
            settings = read_json_file(settings_path)
            hooks = []
            
            if 'hooks' in settings:
                hooks_dir = self._get_hooks_dir(mode)
                for hook_type, entries in settings['hooks'].items():
                    for entry in entries:
                        for hook in entry.get('hooks', []):
                            command = hook.get('command', '')
                            # Extract hook name from command path
                            if command.endswith('.sh'):
                                hook_name = Path(command).stem
                                hook_file = hooks_dir / f"{hook_name}.sh"
                                
                                # Only include if file actually exists
                                if hook_file.exists() and hook_name not in hooks:
                                    hooks.append(hook_name)
                                    
            return sorted(hooks)
            
        except Exception:
            return []
            
    def _get_hook_info(self, hook_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific hook.
        
        Args:
            hook_name: Name of the hook
            
        Returns:
            Dictionary with hook information or None if not found
        """
        config_file = self.hooks_source / hook_name / "config.json"
        if config_file.exists():
            try:
                return read_json_file(config_file)
            except Exception:
                pass
        return None
        
    def check_updates(self) -> Optional[UpdateStatus]:
        """Check for updates to hooks in all locations.
        
        This checks both global hooks and all registered local project hooks,
        combining them into a single UpdateStatus.
        
        Returns:
            UpdateStatus containing all hook updates across all locations
        """
        # First get global updates using parent class method
        global_status = super().check_updates()
        
        # Check for updates in all registered projects
        project_updates = self.check_updates_in_projects()
        
        # If no updates anywhere, return None
        if not global_status and not project_updates:
            return None
        
        # Start with global updates or empty lists
        all_updated = list(global_status.updated) if global_status else []
        all_new = list(global_status.new) if global_status else []
        all_deleted = list(global_status.deleted) if global_status else []
        all_unchanged = list(global_status.unchanged) if global_status else []
        
        # Add project updates with project path prefix
        for project_path, project_status in project_updates.items():
            project_name = Path(project_path).name
            # Prefix files with project info to distinguish them
            for file in project_status.updated:
                all_updated.append(f"[{project_name}] {file}")
            for file in project_status.new:
                all_new.append(f"[{project_name}] {file}")
            for file in project_status.deleted:
                all_deleted.append(f"[{project_name}] {file}")
        
        return UpdateStatus(all_updated, all_new, all_deleted, all_unchanged)
    
    def check_updates_in_projects(self) -> Dict[str, Any]:
        """Check for updates in all registered projects with local hooks.
        
        Returns:
            Dictionary mapping project paths to their update status
        """
        from ..updaters.detector import UpdateDetector
        
        project_updates = {}
        projects_with_hooks = self.project_registry.get_projects_with_component('hooks')
        
        for project_path in projects_with_hooks:
            # Create UpdateDetector for this project's local hooks
            local_hooks_dir = project_path / ".claude" / "hooks" / "ethpandaops"
            
            if local_hooks_dir.exists():
                # Initialize a temporary update detector for this project
                detector = UpdateDetector(self.hooks_source, local_hooks_dir)
                update_status = detector.check_updates(installed_only=True, check_orphaned=True)
                
                if update_status.has_changes:
                    project_updates[str(project_path)] = update_status
        
        return project_updates
    
    def apply_hook_update(self, file_name: str) -> bool:
        """Apply a hook update, handling both global and project-specific hooks.
        
        Args:
            file_name: The file name, possibly with [project] prefix
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if this is a project-specific hook
            if file_name.startswith('[') and '] ' in file_name:
                # Extract project name and hook file
                project_end = file_name.index('] ')
                project_name = file_name[1:project_end]
                actual_file = file_name[project_end + 2:]
                hook_name = actual_file.replace('.sh', '')
                
                # Find the project path from registry
                for project_path in self.project_registry.get_projects_with_component('hooks'):
                    if project_path.name == project_name:
                        # Update this specific hook in the project
                        original_cwd = Path.cwd()
                        try:
                            os.chdir(project_path)
                            result = self.install_hook(hook_name, mode="local")
                            if not result.success:
                                print(f"  [Error] Failed to update hook '{hook_name}' in project '{project_name}': {result.message}")
                            return result.success
                        except Exception as e:
                            print(f"  [Error] Exception updating hook '{hook_name}' in project '{project_name}': {str(e)}")
                            return False
                        finally:
                            os.chdir(original_cwd)
                
                print(f"  [Warning] Could not find project '{project_name}' for hook update")
                return False
            else:
                # Regular global hook
                hook_name = file_name.replace('.sh', '')
                result = self.install_hook(hook_name, mode="global")
                if not result.success:
                    print(f"  [Error] Failed to update global hook '{hook_name}': {result.message}")
                return result.success
        except Exception as e:
            print(f"  [Error] Exception in apply_hook_update for '{file_name}': {str(e)}")
            return False
    
    def update_hooks_in_project(self, project_path: Path) -> InstallationResult:
        """Update hooks in a specific project.
        
        Args:
            project_path: Path to the project
            
        Returns:
            InstallationResult with update details
        """
        from ..updaters.detector import UpdateDetector
        
        local_hooks_dir = project_path / ".claude" / "hooks" / "ethpandaops"
        
        if not local_hooks_dir.exists():
            return InstallationResult(
                False,
                f"No local hooks found in project: {project_path}"
            )
        
        # Create UpdateDetector for this project
        detector = UpdateDetector(self.hooks_source, local_hooks_dir)
        update_status = detector.check_updates(installed_only=True, check_orphaned=True)
        
        if not update_status.has_changes:
            return InstallationResult(
                True,
                f"No updates needed for hooks in {project_path}"
            )
        
        # Apply updates
        updated_count = 0
        errors = []
        
        # Update changed files
        for hook_file in update_status.updated:
            try:
                hook_name = hook_file.replace('.sh', '')
                source_file = self.hooks_source / hook_name / "hook.sh"
                dest_file = local_hooks_dir / hook_file
                
                if source_file.exists():
                    shutil.copy2(source_file, dest_file)
                    dest_file.chmod(0o755)
                    detector.update_metadata(hook_file, source_file)
                    updated_count += 1
            except Exception as e:
                errors.append(f"Failed to update {hook_file}: {str(e)}")
        
        # Add new files
        for hook_file in update_status.new:
            try:
                hook_name = hook_file.replace('.sh', '')
                # Install the hook in local mode for this project
                original_cwd = Path.cwd()
                os.chdir(project_path)
                result = self.install_hook(hook_name, mode="local")
                os.chdir(original_cwd)
                
                if result.success:
                    updated_count += 1
                else:
                    errors.append(f"Failed to install {hook_file}: {result.message}")
            except Exception as e:
                errors.append(f"Failed to add {hook_file}: {str(e)}")
        
        # Remove deleted files
        for hook_file in update_status.deleted:
            try:
                dest_file = local_hooks_dir / hook_file
                if dest_file.exists():
                    dest_file.unlink()
                    detector.remove_metadata(hook_file)
                    updated_count += 1
            except Exception as e:
                errors.append(f"Failed to remove {hook_file}: {str(e)}")
        
        if errors:
            return InstallationResult(
                False,
                f"Updated {updated_count} hooks in {project_path}, but {len(errors)} errors occurred",
                {'errors': errors, 'updated': updated_count}
            )
        
        return InstallationResult(
            True,
            f"Successfully updated {updated_count} hooks in {project_path}",
            {'updated': updated_count}
        )
    
    def sync_hooks_with_files(self, mode: Optional[str] = None, include_projects: bool = True) -> InstallationResult:
        """Synchronize hooks settings with actual files on disk.
        
        Removes hooks from settings if their files don't exist.
        Adds hooks to settings if files exist but aren't configured.
        
        Args:
            mode: Installation mode, or None to check both
            include_projects: Whether to also sync hooks in registered projects
            
        Returns:
            InstallationResult with sync details
        """
        if mode is None:
            modes_to_check = ['global', 'local']
        else:
            modes_to_check = [mode]
        
        results = {
            'removed_from_settings': [],
            'orphaned_files': [],
            'added_to_settings': []
        }
        
        # First sync current directory
        for check_mode in modes_to_check:
            settings_path = self._get_settings_path(check_mode)
            if not settings_path.exists():
                continue
            
            try:
                settings = read_json_file(settings_path)
                hooks_dir = self._get_hooks_dir(check_mode)
                modified = False
                
                # Check hooks in settings
                if 'hooks' in settings:
                    # Create new structure without missing hooks
                    new_hooks = {}
                    
                    for hook_type, entries in settings['hooks'].items():
                        new_entries = []
                        
                        for entry in entries:
                            new_hooks_list = []
                            for hook in entry.get('hooks', []):
                                command = hook.get('command', '')
                                if command.endswith('.sh'):
                                    hook_file = Path(command)
                                    if hook_file.exists():
                                        # Keep this hook
                                        new_hooks_list.append(hook)
                                    else:
                                        # Mark for removal
                                        modified = True
                                        results['removed_from_settings'].append({
                                            'mode': check_mode,
                                            'hook': hook_file.stem,
                                            'reason': 'File not found'
                                        })
                                else:
                                    # Keep non-.sh hooks as-is
                                    new_hooks_list.append(hook)
                            
                            # Only keep entry if it has hooks
                            if new_hooks_list:
                                new_entry = entry.copy()
                                new_entry['hooks'] = new_hooks_list
                                new_entries.append(new_entry)
                        
                        # Only keep hook type if it has entries
                        if new_entries:
                            new_hooks[hook_type] = new_entries
                    
                    # Update settings with cleaned hooks
                    if modified:
                        settings['hooks'] = new_hooks
                
                # Save modified settings
                if modified:
                    write_json_file(settings_path, settings)
                
                # Check for orphaned files (files without settings entries)
                if hooks_dir.exists():
                    for hook_file in hooks_dir.glob('*.sh'):
                        if hook_file.name != '.ai-cookbook-meta.json':
                            # Check if this hook is in settings
                            hook_name = hook_file.stem
                            if hook_name not in self._get_installed_hooks(check_mode):
                                # Hook file exists but not in settings - try to add it
                                try:
                                    # Check if we have the source config to get hook details
                                    hook_source_dir = self.hooks_source / hook_name
                                    if hook_source_dir.exists():
                                        config_file = hook_source_dir / "config.json"
                                        if config_file.exists():
                                            config = read_json_file(config_file)
                                            hook_type = config.get('hook_type', 'PostToolUse')
                                            matcher = config.get('matcher', '')
                                            
                                            # Add to settings
                                            self._add_hook_to_settings(hook_name, hook_type, matcher, 
                                                                     str(hook_file), check_mode)
                                            results['added_to_settings'].append({
                                                'mode': check_mode,
                                                'hook': hook_name,
                                                'file': str(hook_file)
                                            })
                                            modified = True
                                        else:
                                            # No config found, add to orphaned
                                            results['orphaned_files'].append({
                                                'mode': check_mode,
                                                'file': str(hook_file),
                                                'hook': hook_name,
                                                'reason': 'No config.json found'
                                            })
                                    else:
                                        # No source directory, add to orphaned
                                        results['orphaned_files'].append({
                                            'mode': check_mode,
                                            'file': str(hook_file),
                                            'hook': hook_name,
                                            'reason': 'No source directory found'
                                        })
                                except Exception as e:
                                    results['orphaned_files'].append({
                                        'mode': check_mode,
                                        'file': str(hook_file),
                                        'hook': hook_name,
                                        'reason': f'Failed to add to settings: {str(e)}'
                                    })
                
            except Exception as e:
                return InstallationResult(
                    False,
                    f"Failed to sync hooks: {str(e)}"
                )
        
        # Now sync project-specific hooks if requested
        if include_projects and 'local' in modes_to_check:
            projects_with_hooks = self.project_registry.get_projects_with_component('hooks')
            
            for project_path in projects_with_hooks:
                # Skip current directory as we already checked it
                if project_path == Path.cwd():
                    continue
                
                try:
                    # Change to project directory temporarily
                    original_cwd = Path.cwd()
                    os.chdir(project_path)
                    
                    # Sync local hooks for this project
                    project_settings_path = self._get_settings_path('local')
                    if project_settings_path.exists():
                        # Run sync for this project
                        project_sync = self.sync_hooks_with_files(mode='local', include_projects=False)
                        
                        # Merge results
                        if project_sync.details.get('removed_from_settings'):
                            for item in project_sync.details['removed_from_settings']:
                                item['project'] = str(project_path)
                                results['removed_from_settings'].append(item)
                        
                        if project_sync.details.get('added_to_settings'):
                            for item in project_sync.details['added_to_settings']:
                                item['project'] = str(project_path)
                                results['added_to_settings'].append(item)
                        
                        if project_sync.details.get('orphaned_files'):
                            for item in project_sync.details['orphaned_files']:
                                item['project'] = str(project_path)
                                results['orphaned_files'].append(item)
                    
                    os.chdir(original_cwd)
                    
                except Exception as e:
                    # Make sure we restore the directory
                    if 'original_cwd' in locals():
                        os.chdir(original_cwd)
                    # Log but don't fail the whole sync
                    results['orphaned_files'].append({
                        'project': str(project_path),
                        'mode': 'local',
                        'hook': 'unknown',
                        'reason': f'Failed to sync project: {str(e)}'
                    })
        
        # Summary
        total_changes = len(results['removed_from_settings']) + len(results['orphaned_files']) + len(results['added_to_settings'])
        if total_changes > 0:
            parts = []
            if results['removed_from_settings']:
                parts.append(f"{len(results['removed_from_settings'])} removed from settings")
            if results['added_to_settings']:
                parts.append(f"{len(results['added_to_settings'])} added to settings")
            if results['orphaned_files']:
                parts.append(f"{len(results['orphaned_files'])} orphaned files found")
            
            return InstallationResult(
                True,
                f"Synchronized hooks: {', '.join(parts)}",
                results
            )
        else:
            return InstallationResult(
                True,
                "Hooks are already synchronized",
                results
            )
    
    def _check_hook_dependencies(self, hook_name: str) -> Dict[str, Any]:
        """Check if hook dependencies are met.
        
        Args:
            hook_name: Name of the hook
            
        Returns:
            Dictionary with success status and details
        """
        deps_script = self.hooks_source / hook_name / "deps.sh"
        if deps_script.exists():
            try:
                result = run_command(["bash", str(deps_script)], check=False)
                return {
                    'success': result.returncode == 0,
                    'output': (result.stdout or '') + (result.stderr or ''),
                    'return_code': result.returncode
                }
            except Exception as e:
                return {
                    'success': False,
                    'output': f'Error running dependencies check: {str(e)}',
                    'return_code': -1
                }
        return {'success': True, 'output': 'No dependencies to check'}
        
    def _add_hook_to_settings(self, hook_name: str, hook_type: str, matcher: str, 
                             command_path: str, mode: str) -> None:
        """Add hook to settings.json.
        
        Args:
            hook_name: Name of the hook
            hook_type: Type of hook (e.g., "PostToolUse")
            matcher: Matcher pattern for the hook
            command_path: Path to the hook command
            mode: Installation mode ("global" or "local")
        """
        settings_path = self._get_settings_path(mode)
        
        # Initialize settings file if needed
        if not settings_path.exists():
            settings = {"hooks": {}}
            write_json_file(settings_path, settings)
        else:
            settings = read_json_file(settings_path)
            
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
        
        # Use relative path for local installations
        if mode == "local":
            try:
                command_path = str(Path(command_path).relative_to(Path.cwd()))
            except ValueError:
                # If paths are on different drives (Windows), use absolute path
                pass
                
        # Add new hook configuration
        new_entry = {
            "matcher": matcher,
            "hooks": [{
                "type": "command",
                "command": command_path
            }]
        }
        settings['hooks'][hook_type].append(new_entry)
        
        # Write updated settings
        write_json_file(settings_path, settings)
        
    def _remove_hook_from_settings(self, hook_name: str, mode: str) -> None:
        """Remove hook from settings.json.
        
        Args:
            hook_name: Name of the hook
            mode: Installation mode ("global" or "local")
        """
        settings_path = self._get_settings_path(mode)
        if not settings_path.exists():
            return
            
        settings = read_json_file(settings_path)
        
        if 'hooks' in settings:
            for hook_type, entries in settings['hooks'].items():
                settings['hooks'][hook_type] = [
                    entry for entry in entries
                    if not any(hook_name in h.get('command', '') for h in entry.get('hooks', []))
                ]
                
            # Remove empty hook type arrays
            settings['hooks'] = {k: v for k, v in settings['hooks'].items() if v}
            
        # Write updated settings
        write_json_file(settings_path, settings)