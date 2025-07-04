"""Claude commands installer for PandaOps Cookbook."""

from pathlib import Path
from typing import Dict, Any, List
import shutil

from ..installers.base import BaseInstaller, InstallationResult
from ..utils.file_operations import (
    ensure_directory, copy_files, directory_exists, 
    list_files, remove_directory, make_executable
)
from ..utils.system import add_to_path, is_in_path, detect_shell, get_shell_profile_path
from ..config.settings import CLAUDE_DIR, CLAUDE_COMMANDS_DIR

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class CommandsInstaller(BaseInstaller):
    """Installer for Claude commands integration."""
    
    def __init__(self):
        """Initialize commands installer."""
        super().__init__(
            name="Claude Commands",
            description="Install Claude commands and scripts to PATH"
        )
        self.commands_source = PROJECT_ROOT / "claude-code" / "commands"
        self.scripts_source = PROJECT_ROOT / "scripts"
        self.scripts_bin = Path.home() / ".pandaops" / "bin"
        
    def check_status(self) -> Dict[str, Any]:
        """Check installation status of Claude commands.
        
        Returns:
            Dictionary with status information:
            - installed: Whether commands are installed
            - commands_installed: Whether command files are in place
            - scripts_in_path: Whether scripts directory is in PATH
            - installed_commands: List of installed command files
            - available_scripts: List of available scripts
        """
        commands_installed = CLAUDE_COMMANDS_DIR.exists() and \
                           len(list(CLAUDE_COMMANDS_DIR.glob("*.md"))) > 0
        scripts_in_path = is_in_path(self.scripts_bin)
        
        installed_commands = []
        if commands_installed:
            installed_commands = [f.name for f in list_files(CLAUDE_COMMANDS_DIR, "*.md")]
            
        available_scripts = []
        if directory_exists(self.scripts_bin):
            available_scripts = [f.name for f in list_files(self.scripts_bin, "*.py")]
        
        # Get available commands from source
        available_commands = []
        if directory_exists(self.commands_source):
            available_commands = [f.name for f in list_files(self.commands_source, "*.md")]
        
        return {
            'installed': commands_installed and scripts_in_path,
            'commands_installed': commands_installed,
            'scripts_in_path': scripts_in_path,
            'installed_commands': installed_commands,
            'installed_items': installed_commands,  # For compatibility with recommended installer
            'available_commands': available_commands,
            'available_scripts': available_scripts,
            'commands_dir': str(CLAUDE_COMMANDS_DIR),
            'scripts_dir': str(self.scripts_bin)
        }
        
    def install(self) -> InstallationResult:
        """Install all available commands.
        
        Returns:
            InstallationResult indicating success/failure
        """
        status = self.check_status()
        available_commands = status.get('available_commands', [])
        installed_commands = status.get('installed_commands', [])
        
        results = []
        for command in available_commands:
            if command not in installed_commands:
                result = self.install_command(command)
                results.append((command, result))
        
        successful = [cmd for cmd, result in results if result.success]
        failed = [cmd for cmd, result in results if not result.success]
        
        if not results:
            return InstallationResult(
                True,
                "All commands are already installed"
            )
        
        if failed:
            return InstallationResult(
                False,
                f"Installed {len(successful)} commands, {len(failed)} failed",
                {'successful': successful, 'failed': failed}
            )
        
        return InstallationResult(
            True,
            f"Successfully installed {len(successful)} commands",
            {'installed': successful}
        )
        
    def install_command(self, command_name: str) -> InstallationResult:
        """Install a specific Claude command.
        
        Args:
            command_name: Name of the command file (e.g., 'eip.md')
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            # Check if command exists in source
            command_source = self.commands_source / command_name
            if not command_source.exists():
                return InstallationResult(
                    False,
                    f"Command '{command_name}' not found in source directory"
                )
                
            # Create required directories
            self.create_required_directories()
            ensure_directory(CLAUDE_COMMANDS_DIR)
            
            # Copy specific command file
            command_target = CLAUDE_COMMANDS_DIR / command_name
            
            # Back up existing command if present
            backup_created = False
            if command_target.exists():
                backup_path = self.backup_manager.create_backup(
                    command_target,
                    f"command_{command_name.replace('.', '_')}"
                )
                if backup_path:
                    backup_created = True
            
            # Copy command file
            shutil.copy2(command_source, command_target)
            
            details = {
                'command': command_name,
                'target_path': str(command_target)
            }
            
            if backup_created:
                details['backup_created'] = str(backup_path)
            
            return InstallationResult(
                True,
                f"Successfully installed command: {command_name}",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install command {command_name}: {str(e)}"
            )
            
    def uninstall_command(self, command_name: str) -> InstallationResult:
        """Uninstall a specific Claude command.
        
        Args:
            command_name: Name of the command file (e.g., 'eip.md')
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            command_target = CLAUDE_COMMANDS_DIR / command_name
            
            if not command_target.exists():
                return InstallationResult(
                    True,
                    f"Command '{command_name}' is not installed"
                )
            
            # Back up before removal
            backup_path = self.backup_manager.create_backup(
                command_target,
                f"command_{command_name.replace('.', '_')}_uninstall"
            )
            
            # Remove command file
            command_target.unlink()
            
            details = {
                'command': command_name,
                'backup_created': str(backup_path) if backup_path else None
            }
            
            return InstallationResult(
                True,
                f"Successfully uninstalled command: {command_name}",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall command {command_name}: {str(e)}"
            )
            
    def _install_all_commands_and_scripts(self) -> InstallationResult:
        """Install all Claude commands and add scripts to PATH (original implementation).
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            # Validate prerequisites
            prereq_result = self.validate_prerequisites()
            if not prereq_result.success:
                return prereq_result
                
            # Create required directories
            self.create_required_directories()
            
            # Back up existing installation if present
            if directory_exists(CLAUDE_COMMANDS_DIR):
                backup_path = self.backup_manager.create_backup(
                    CLAUDE_COMMANDS_DIR,
                    "claude_commands"
                )
                if backup_path:
                    details = {'backup_created': str(backup_path)}
                else:
                    details = {}
            else:
                details = {}
            
            # Copy command files
            if not self.commands_source.exists():
                return InstallationResult(
                    False,
                    f"Commands source directory not found: {self.commands_source}"
                )
                
            ensure_directory(CLAUDE_COMMANDS_DIR)
            copy_files(self.commands_source, CLAUDE_COMMANDS_DIR, patterns=["*.md"])
            
            # Copy scripts to bin directory
            if not self.scripts_source.exists():
                return InstallationResult(
                    False,
                    f"Scripts source directory not found: {self.scripts_source}"
                )
                
            ensure_directory(self.scripts_bin)
            
            # Copy Python scripts and make them executable
            script_files = list_files(self.scripts_source, "*.py")
            for script in script_files:
                dest_path = self.scripts_bin / script.name
                shutil.copy2(script, dest_path)
                make_executable(dest_path)
            
            # Add scripts directory to PATH
            if not is_in_path(self.scripts_bin):
                if not add_to_path(self.scripts_bin):
                    return InstallationResult(
                        False,
                        "Failed to add scripts directory to PATH",
                        details
                    )
                    
            # Update installation details
            status = self.check_status()
            details.update({
                'commands_installed': len(status['installed_commands']),
                'scripts_installed': len(status['available_scripts']),
                'commands_dir': status['commands_dir'],
                'scripts_dir': status['scripts_dir'],
                'shell_profile': str(get_shell_profile_path()),
                'note': f"Please restart your shell or run: source {get_shell_profile_path()}"
            })
            
            return InstallationResult(
                True,
                "Claude commands installed successfully",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Installation failed: {str(e)}"
            )
            
    def uninstall(self) -> InstallationResult:
        """Uninstall Claude commands.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            removed_items = []
            
            # Remove commands directory
            if directory_exists(CLAUDE_COMMANDS_DIR):
                # Create backup before removal
                backup_path = self.backup_manager.create_backup(
                    CLAUDE_COMMANDS_DIR,
                    "claude_commands_uninstall"
                )
                remove_directory(CLAUDE_COMMANDS_DIR)
                removed_items.append("Claude commands directory")
                
            # Remove scripts from bin directory
            if directory_exists(self.scripts_bin):
                script_files = list_files(self.scripts_bin, "*.py")
                if script_files:
                    # Back up scripts before removal
                    backup_path = self.backup_manager.create_backup(
                        self.scripts_bin,
                        "scripts_bin_uninstall"
                    )
                    for script in script_files:
                        script.unlink()
                    removed_items.append(f"{len(script_files)} scripts")
                    
            # Note: We don't remove the PATH entry automatically as it might
            # be used by other tools. User can manually remove if needed.
            
            if not removed_items:
                return InstallationResult(
                    True,
                    "No Claude commands were installed"
                )
                
            details = {
                'removed': removed_items,
                'note': f"PATH entry for {self.scripts_bin} was not removed. Remove manually if needed."
            }
            
            if 'backup_path' in locals():
                details['backup_created'] = str(backup_path)
                
            return InstallationResult(
                True,
                f"Claude commands uninstalled successfully",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Uninstallation failed: {str(e)}"
            )
            
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about Claude commands.
        
        Returns:
            Dictionary with detailed installer information
        """
        status = self.check_status()
        
        # Get list of available commands from source
        available_commands = []
        if self.commands_source.exists():
            available_commands = [f.name for f in list_files(self.commands_source, "*.md")]
            
        # Get list of available scripts from source
        available_scripts = []
        if self.scripts_source.exists():
            available_scripts = [f.name for f in list_files(self.scripts_source, "*.py")]
            
        return {
            'name': self.name,
            'description': self.description,
            'installed': status['installed'],
            'status': status,
            'paths': {
                'commands_source': str(self.commands_source),
                'scripts_source': str(self.scripts_source),
                'commands_target': str(CLAUDE_COMMANDS_DIR),
                'scripts_target': str(self.scripts_bin),
                'shell_profile': str(get_shell_profile_path())
            },
            'available': {
                'commands': available_commands,
                'scripts': available_scripts
            },
            'shell_info': {
                'detected_shell': detect_shell(),
                'scripts_in_path': status['scripts_in_path']
            }
        }
        
    def list_available_commands(self) -> List[str]:
        """List all available Claude commands.
        
        Returns:
            List of available command names
        """
        if not self.commands_source.exists():
            return []
            
        return [f.stem for f in list_files(self.commands_source, "*.md")]
        
    def validate_prerequisites(self) -> InstallationResult:
        """Validate prerequisites for Claude commands installation.
        
        Returns:
            InstallationResult indicating if prerequisites are met
        """
        # Check if source directories exist
        if not self.commands_source.exists():
            return InstallationResult(
                False,
                f"Commands source directory not found: {self.commands_source}"
            )
            
        if not self.scripts_source.exists():
            return InstallationResult(
                False,
                f"Scripts source directory not found: {self.scripts_source}"
            )
            
        # Check if we have any commands to install
        commands = list_files(self.commands_source, "*.md")
        if not commands:
            return InstallationResult(
                False,
                "No command files found in source directory"
            )
            
        return InstallationResult(True, "Prerequisites met")
        
    def create_required_directories(self) -> None:
        """Create required directories for Claude commands."""
        super().create_required_directories()
        ensure_directory(CLAUDE_DIR)
        ensure_directory(CLAUDE_COMMANDS_DIR.parent)
        ensure_directory(self.scripts_bin)