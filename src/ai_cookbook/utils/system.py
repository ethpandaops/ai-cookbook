"""System detection and shell integration utilities."""

import os
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def detect_shell() -> str:
    """Detect user's shell (bash, zsh, fish, etc.).
    
    Returns:
        Shell name (e.g., 'bash', 'zsh', 'fish', 'sh')
    """
    # First try SHELL environment variable
    shell_env = os.environ.get('SHELL', '')
    if shell_env:
        shell_name = Path(shell_env).name
        return shell_name
        
    # Fallback to checking common shell locations
    if Path('/bin/zsh').exists():
        return 'zsh'
    elif Path('/bin/bash').exists():
        return 'bash'
    elif Path('/usr/bin/fish').exists():
        return 'fish'
    else:
        return 'sh'  # Default to sh


def get_shell_profile_path() -> Path:
    """Get path to shell profile file based on detected shell.
    
    Returns:
        Path to shell profile file (e.g., ~/.bashrc, ~/.zshrc)
    """
    shell = detect_shell()
    home = Path.home()
    
    # Map shells to their profile files
    profile_map = {
        'zsh': home / '.zshrc',
        'bash': home / '.bashrc',  # Note: on macOS, might need .bash_profile
        'fish': home / '.config' / 'fish' / 'config.fish',
        'sh': home / '.profile',
    }
    
    # Special handling for bash on macOS
    if shell == 'bash' and platform.system() == 'Darwin':
        # On macOS, Terminal.app uses .bash_profile for login shells
        bash_profile = home / '.bash_profile'
        if bash_profile.exists():
            return bash_profile
            
    return profile_map.get(shell, home / '.profile')


def add_to_path(directory: Path) -> bool:
    """Add directory to PATH in shell profile.
    
    Args:
        directory: Directory to add to PATH
        
    Returns:
        True if successfully added, False otherwise
    """
    try:
        directory = directory.resolve()
        profile_path = get_shell_profile_path()
        
        # Check if already in PATH
        if is_in_path(directory):
            return True
            
        # Read current profile content
        if profile_path.exists():
            content = profile_path.read_text()
        else:
            content = ''
            
        # Check if already in profile file
        dir_str = str(directory)
        if dir_str in content:
            return True
            
        # Prepare PATH export line based on shell
        shell = detect_shell()
        if shell == 'fish':
            # Fish shell syntax
            export_line = f'\n# Added by ai-cookbook\nset -gx PATH "{dir_str}" $PATH\n'
        else:
            # Bash/Zsh/Sh syntax
            export_line = f'\n# Added by ai-cookbook\nexport PATH="{dir_str}:$PATH"\n'
            
        # Append to profile
        with open(profile_path, 'a') as f:
            f.write(export_line)
            
        return True
        
    except Exception as e:
        # Log error or handle as appropriate
        return False


def is_in_path(directory: Path) -> bool:
    """Check if directory is in PATH.
    
    Args:
        directory: Directory to check
        
    Returns:
        True if directory is in PATH, False otherwise
    """
    directory = directory.resolve()
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    
    for path_dir in path_dirs:
        try:
            if Path(path_dir).resolve() == directory:
                return True
        except Exception:
            # Skip invalid paths
            continue
            
    return False


def run_command(command: List[str], cwd: Optional[Path] = None, 
                capture_output: bool = True, check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command and return result.
    
    Args:
        command: Command and arguments as list
        cwd: Working directory for command
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit code
        
    Returns:
        CompletedProcess instance with command result
        
    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=capture_output,
        text=True,
        check=check
    )


def command_exists(command: str) -> bool:
    """Check if a command exists in the system PATH.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command exists, False otherwise
    """
    return shutil.which(command) is not None


def get_system_info() -> Dict[str, Any]:
    """Get system information.
    
    Returns:
        Dictionary with system information
    """
    return {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'python_version': platform.python_version(),
        'shell': detect_shell(),
        'home_directory': str(Path.home()),
        'current_directory': str(Path.cwd()),
    }


def is_root() -> bool:
    """Check if running as root/administrator.
    
    Returns:
        True if running with elevated privileges
    """
    if platform.system() == 'Windows':
        try:
            # Windows: check if running as administrator
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # Unix-like: check if UID is 0
        return os.getuid() == 0


def get_environment_variable(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable value.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value or default
    """
    return os.environ.get(name, default)


def set_environment_variable(name: str, value: str) -> None:
    """Set environment variable for current process.
    
    Args:
        name: Environment variable name
        value: Value to set
    """
    os.environ[name] = value


def which(command: str) -> Optional[Path]:
    """Find full path to a command.
    
    Args:
        command: Command name
        
    Returns:
        Full path to command, or None if not found
    """
    result = shutil.which(command)
    return Path(result) if result else None


def get_user_name() -> str:
    """Get current user name.
    
    Returns:
        User name
    """
    return os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))


def create_symlink(source: Path, target: Path) -> bool:
    """Create symbolic link.
    
    Args:
        source: Source path (what the link points to)
        target: Target path (the link itself)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        target.symlink_to(source)
        return True
    except Exception:
        return False