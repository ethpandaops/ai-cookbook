"""Path handling utilities."""

import os
from pathlib import Path
from typing import Optional, List


def expand_path(path: str) -> Path:
    """Expand user home directory and environment variables in path.
    
    Args:
        path: Path string that may contain ~ or environment variables
        
    Returns:
        Expanded Path object
    """
    # Expand ~ to user home directory
    expanded = os.path.expanduser(path)
    
    # Expand environment variables
    expanded = os.path.expandvars(expanded)
    
    return Path(expanded).resolve()


def relative_to_home(path: Path) -> str:
    """Get path relative to home directory if possible.
    
    Args:
        path: Absolute path
        
    Returns:
        Path string relative to home (with ~/) or absolute path if not under home
    """
    home = Path.home()
    try:
        relative = path.relative_to(home)
        return f"~/{relative}"
    except ValueError:
        # Path is not under home directory
        return str(path)


def find_repo_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the root of the git repository.
    
    Args:
        start_path: Starting directory (defaults to current directory)
        
    Returns:
        Path to repository root, or None if not in a git repository
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()
        
    current = start_path
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
        
    return None


def ensure_absolute(path: Path, base: Optional[Path] = None) -> Path:
    """Ensure path is absolute.
    
    Args:
        path: Path that may be relative
        base: Base directory for relative paths (defaults to current directory)
        
    Returns:
        Absolute path
    """
    if path.is_absolute():
        return path
        
    if base is None:
        base = Path.cwd()
        
    return (base / path).resolve()


def is_subdirectory(path: Path, parent: Path) -> bool:
    """Check if path is a subdirectory of parent.
    
    Args:
        path: Path to check
        parent: Parent directory
        
    Returns:
        True if path is under parent directory
    """
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def find_file_upwards(filename: str, start_path: Optional[Path] = None) -> Optional[Path]:
    """Search for a file in current directory and parent directories.
    
    Args:
        filename: Name of file to find
        start_path: Starting directory (defaults to current directory)
        
    Returns:
        Path to file if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()
        
    current = start_path
    while current != current.parent:
        file_path = current / filename
        if file_path.exists():
            return file_path
        current = current.parent
        
    return None


def safe_join(base: Path, *parts: str) -> Path:
    """Safely join path components preventing directory traversal.
    
    Args:
        base: Base directory
        *parts: Path components to join
        
    Returns:
        Joined path
        
    Raises:
        ValueError: If resulting path would be outside base directory
    """
    base = base.resolve()
    joined = base
    
    for part in parts:
        # Remove any leading slashes or dots that could cause traversal
        clean_part = part.lstrip('/.').strip()
        if not clean_part:
            continue
            
        # Check for directory traversal attempts
        if '..' in Path(clean_part).parts:
            raise ValueError(f"Directory traversal attempt detected: {part}")
            
        joined = joined / clean_part
        
    # Ensure final path is under base directory
    resolved = joined.resolve()
    if not is_subdirectory(resolved, base):
        raise ValueError(f"Path {resolved} is outside base directory {base}")
        
    return resolved


def get_common_parent(paths: List[Path]) -> Optional[Path]:
    """Get common parent directory of multiple paths.
    
    Args:
        paths: List of paths
        
    Returns:
        Common parent directory, or None if paths list is empty
    """
    if not paths:
        return None
        
    if len(paths) == 1:
        return paths[0].parent if paths[0].is_file() else paths[0]
        
    # Convert all to absolute paths
    abs_paths = [p.resolve() for p in paths]
    
    # Find common parts
    common_parts = []
    for parts in zip(*[p.parts for p in abs_paths]):
        if len(set(parts)) == 1:
            common_parts.append(parts[0])
        else:
            break
            
    if not common_parts:
        return None
        
    # Handle Windows drive letters
    if os.name == 'nt' and len(common_parts) == 1:
        return Path(common_parts[0] + os.sep)
    else:
        return Path(*common_parts)


def normalize_path(path: Path) -> Path:
    """Normalize path by resolving symlinks and removing redundant components.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized path
    """
    return path.resolve()


def split_extension(path: Path) -> tuple[Path, str]:
    """Split path into base and extension.
    
    Args:
        path: File path
        
    Returns:
        Tuple of (path without extension, extension with dot)
    """
    return (path.with_suffix(''), path.suffix)