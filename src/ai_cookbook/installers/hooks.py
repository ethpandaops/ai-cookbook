"""Hooks installer for PandaOps Cookbook."""

import json
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

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class HooksInstaller(InteractiveInstaller):
    """Installer for Claude Code hooks integration.
    
    Manages installation of hooks that run automated checks after file edits.
    Supports both global and local installation modes.
    """
    
    def __init__(self):
        """Initialize hooks installer."""
        super().__init__(
            name="Hooks",
            description="Install Claude Code hooks for automated checks"
        )
        self.hooks_source = PROJECT_ROOT / "claude-code" / "hooks"
        self.current_mode = "global"  # Default to global mode
        
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
            'current_mode': self.current_mode
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
            
            # Read hook configuration
            config = read_json_file(hook_config)
            hook_type = config.get('hook_type', 'PostToolUse')
            matcher = config.get('matcher', '')
            
            # Add hook to settings
            self._add_hook_to_settings(hook_name, hook_type, matcher, str(installed_hook_path), mode)
            
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
        installed_hooks = self._get_installed_hooks(self.current_mode)
        available_hooks = status['available_hooks']
        
        # Add install options for available hooks
        for hook_name in available_hooks:
            if hook_name not in installed_hooks:
                hook_info = self._get_hook_info(hook_name)
                description = hook_info.get('description', 'No description available') if hook_info else 'No description available'
                self.add_interactive_option(
                    f"Install {hook_name}",
                    description,
                    lambda h=hook_name: self.install_hook(h)
                )
                
        # Add uninstall options for installed hooks
        for hook_name in installed_hooks:
            self.add_interactive_option(
                f"Uninstall {hook_name}",
                f"Remove {hook_name} hook from {self.current_mode} configuration",
                lambda h=hook_name: self.uninstall_hook(h)
            )
            
        # Add install all option if there are uninstalled hooks
        uninstalled = [h for h in available_hooks if h not in installed_hooks]
        if uninstalled:
            self.add_interactive_option(
                "Install all hooks",
                f"Install all {len(uninstalled)} available hooks in {self.current_mode} mode",
                self._install_all_hooks
            )
            
        # Add uninstall all option if there are installed hooks
        if installed_hooks:
            self.add_interactive_option(
                "Uninstall all hooks",
                f"Remove all {len(installed_hooks)} installed hooks from {self.current_mode} configuration",
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
                for hook_type, entries in settings['hooks'].items():
                    for entry in entries:
                        for hook in entry.get('hooks', []):
                            command = hook.get('command', '')
                            # Extract hook name from command path
                            if command.endswith('.sh'):
                                hook_name = Path(command).stem
                                if hook_name not in hooks:
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