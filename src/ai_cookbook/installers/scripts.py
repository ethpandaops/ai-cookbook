"""Scripts installer for PandaOps Cookbook."""

from pathlib import Path
from typing import Dict, Any, List

from ..installers.base import BaseInstaller, InstallationResult
from ..utils.system import add_to_path, is_in_path, get_shell_profile_path
from ..utils.file_operations import file_exists, list_files

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class ScriptsInstaller(BaseInstaller):
    """Installer for adding project scripts to PATH.
    
    Manages installation of scripts directory to system PATH,
    making all project scripts globally accessible.
    """
    
    def __init__(self):
        """Initialize scripts installer."""
        super().__init__(
            name="Scripts",
            description="Add project scripts to system PATH"
        )
        self.scripts_dir = PROJECT_ROOT / "scripts"
        
    def check_status(self) -> Dict[str, Any]:
        """Check if scripts directory is in PATH.
        
        Returns:
            Dictionary with status information:
            - installed: Whether scripts directory is in PATH
            - scripts_dir: Path to scripts directory
            - available_scripts: List of available script files
            - shell_profile: Path to shell profile file
            - in_path: Whether scripts directory is in current PATH
        """
        in_path = is_in_path(self.scripts_dir)
        available_scripts = self._get_available_scripts()
        
        return {
            'installed': in_path,
            'scripts_dir': str(self.scripts_dir),
            'available_scripts': available_scripts,
            'shell_profile': str(get_shell_profile_path()),
            'in_path': in_path
        }
        
    def install(self) -> InstallationResult:
        """Add scripts directory to PATH.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            # Check if already in PATH
            if is_in_path(self.scripts_dir):
                return InstallationResult(
                    True,
                    "Scripts directory is already in PATH",
                    {'scripts_dir': str(self.scripts_dir)}
                )
                
            # Check if scripts directory exists
            if not self.scripts_dir.exists():
                return InstallationResult(
                    False,
                    f"Scripts directory not found: {self.scripts_dir}",
                    {'scripts_dir': str(self.scripts_dir)}
                )
                
            # Add to PATH
            success = add_to_path(self.scripts_dir)
            
            if success:
                available_scripts = self._get_available_scripts()
                shell_profile = get_shell_profile_path()
                
                return InstallationResult(
                    True,
                    f"Successfully added scripts directory to PATH. Restart your shell or run 'source {shell_profile}' to apply changes.",
                    {
                        'scripts_dir': str(self.scripts_dir),
                        'shell_profile': str(shell_profile),
                        'available_scripts': available_scripts,
                        'note': 'You may need to restart your shell for changes to take effect'
                    }
                )
            else:
                return InstallationResult(
                    False,
                    "Failed to add scripts directory to PATH",
                    {'scripts_dir': str(self.scripts_dir)}
                )
                
        except Exception as e:
            return InstallationResult(
                False,
                f"Installation failed: {str(e)}",
                {'error': str(e)}
            )
            
    def uninstall(self) -> InstallationResult:
        """Remove scripts directory from PATH (manual operation).
        
        Returns:
            InstallationResult with instructions for manual removal
        """
        shell_profile = get_shell_profile_path()
        
        message = f"""
Scripts PATH removal requires manual editing of your shell profile.

To remove the scripts directory from PATH:
1. Open your shell profile: {shell_profile}
2. Find and remove the line containing: export PATH="{self.scripts_dir}:$PATH"
3. Save the file and restart your shell

The line to remove will look like:
# Added by ai-cookbook
export PATH="{self.scripts_dir}:$PATH"
        """.strip()
        
        return InstallationResult(
            False,
            "Manual removal required",
            {
                'instructions': message,
                'shell_profile': str(shell_profile),
                'scripts_dir': str(self.scripts_dir)
            }
        )
        
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about scripts installer.
        
        Returns:
            Dictionary with detailed installer information
        """
        status = self.check_status()
        
        # Get script details
        script_details = []
        for script_name in status['available_scripts']:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                script_info = {
                    'name': script_name,
                    'path': str(script_path),
                    'executable': script_path.is_file() and script_path.stat().st_mode & 0o111 != 0,
                    'size': script_path.stat().st_size if script_path.is_file() else 0
                }
                
                # Try to get script description from first line comment
                try:
                    with open(script_path, 'r') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('#') and not first_line.startswith('#!'):
                            script_info['description'] = first_line.lstrip('#').strip()
                except Exception:
                    pass
                    
                script_details.append(script_info)
                
        return {
            'name': self.name,
            'description': self.description,
            'installed': status['installed'],
            'status': status,
            'paths': {
                'scripts_dir': str(self.scripts_dir),
                'shell_profile': status['shell_profile']
            },
            'scripts': script_details,
            'installation_note': 'Adding scripts to PATH allows you to run them from anywhere in your terminal'
        }
        
    def _get_available_scripts(self) -> List[str]:
        """Get list of available script files.
        
        Returns:
            List of script file names
        """
        scripts = []
        
        if self.scripts_dir.exists():
            # Get all Python and shell scripts
            for pattern in ['*.py', '*.sh', '*.bash', '*.zsh', '*.fish']:
                scripts.extend([f.name for f in self.scripts_dir.glob(pattern)])
                
            # Also check for files with no extension but with shebang
            for file_path in self.scripts_dir.iterdir():
                if file_path.is_file() and file_path.suffix == '':
                    try:
                        with open(file_path, 'r') as f:
                            first_line = f.readline()
                            if first_line.startswith('#!'):
                                scripts.append(file_path.name)
                    except Exception:
                        pass
                        
        return sorted(list(set(scripts)))  # Remove duplicates and sort