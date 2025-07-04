"""File and directory operations utilities."""

import shutil
import json
import os
from pathlib import Path
from typing import List, Optional, Any, Dict
import fnmatch


def ensure_directory(path: Path) -> None:
    """Create directory if it doesn't exist, including parent directories.
    
    Args:
        path: Directory path to create
    """
    path.mkdir(parents=True, exist_ok=True)


def copy_files(source: Path, dest: Path, patterns: Optional[List[str]] = None) -> None:
    """Copy files matching patterns from source to destination.
    
    Args:
        source: Source directory path
        dest: Destination directory path
        patterns: List of glob patterns to match (e.g. ['*.py', '*.md'])
                 If None, copies all files
    """
    if not source.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source}")
        
    # Ensure destination exists
    ensure_directory(dest)
    
    # If source is a file, copy it directly
    if source.is_file():
        shutil.copy2(source, dest)
        return
        
    # Copy matching files
    if patterns is None:
        # Copy entire directory tree
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
    else:
        # Copy only files matching patterns
        for item in source.iterdir():
            if item.is_file():
                # Check if file matches any pattern
                for pattern in patterns:
                    if fnmatch.fnmatch(item.name, pattern):
                        shutil.copy2(item, dest / item.name)
                        break
            elif item.is_dir():
                # Recursively copy subdirectories
                dest_subdir = dest / item.name
                copy_files(item, dest_subdir, patterns)


def read_json_file(path: Path) -> Dict[str, Any]:
    """Read and parse JSON file.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
        
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json_file(path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """Write data to JSON file.
    
    Args:
        path: Path to JSON file
        data: Data to write
        indent: Number of spaces for indentation
    """
    # Ensure parent directory exists
    ensure_directory(path.parent)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def remove_directory(path: Path) -> None:
    """Remove directory and all its contents.
    
    Args:
        path: Directory path to remove
    """
    if path.exists() and path.is_dir():
        shutil.rmtree(path)


def file_exists(path: Path) -> bool:
    """Check if file exists.
    
    Args:
        path: File path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return path.exists() and path.is_file()


def directory_exists(path: Path) -> bool:
    """Check if directory exists.
    
    Args:
        path: Directory path to check
        
    Returns:
        True if directory exists, False otherwise
    """
    return path.exists() and path.is_dir()


def list_files(directory: Path, pattern: str = '*') -> List[Path]:
    """List files in directory matching pattern.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        
    Returns:
        List of file paths
    """
    if not directory.exists() or not directory.is_dir():
        return []
        
    return list(directory.glob(pattern))


def get_file_size(path: Path) -> int:
    """Get file size in bytes.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    if path.exists() and path.is_file():
        return path.stat().st_size
    return 0


def make_executable(path: Path) -> None:
    """Make file executable (Unix-like systems only).
    
    Args:
        path: File path to make executable
    """
    if path.exists() and path.is_file():
        # Add execute permissions for owner
        current_mode = path.stat().st_mode
        path.chmod(current_mode | 0o100)


def read_text_file(path: Path, encoding: str = 'utf-8') -> str:
    """Read text file contents.
    
    Args:
        path: File path
        encoding: Text encoding
        
    Returns:
        File contents as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
        
    with open(path, 'r', encoding=encoding) as f:
        return f.read()


def write_text_file(path: Path, content: str, encoding: str = 'utf-8') -> None:
    """Write text to file.
    
    Args:
        path: File path
        content: Content to write
        encoding: Text encoding
    """
    # Ensure parent directory exists
    ensure_directory(path.parent)
    
    with open(path, 'w', encoding=encoding) as f:
        f.write(content)


def append_to_file(path: Path, content: str, encoding: str = 'utf-8') -> None:
    """Append text to file.
    
    Args:
        path: File path
        content: Content to append
        encoding: Text encoding
    """
    # Ensure parent directory exists
    ensure_directory(path.parent)
    
    with open(path, 'a', encoding=encoding) as f:
        f.write(content)