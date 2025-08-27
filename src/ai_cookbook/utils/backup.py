from pathlib import Path
from datetime import datetime, timedelta
import shutil
import json
from typing import Optional, List


class BackupManager:
    """Manages backup and restore operations for files."""
    
    def __init__(self, backup_dir: Path = None):
        """Initialize the backup manager with a backup directory.
        
        Args:
            backup_dir: Directory to store backups. Defaults to ~/.claude/backups
        """
        self.backup_dir = backup_dir or Path.home() / ".claude" / "backups"
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self, file_path: Path, prefix: str = "backup") -> Path:
        """Create timestamped backup of file or directory.
        
        Args:
            file_path: Path to file or directory to backup
            prefix: Prefix for backup filename
            
        Returns:
            Path to created backup file or directory
            
        Raises:
            FileNotFoundError: If source file or directory doesn't exist
            PermissionError: If unable to read source or write backup
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")
            
        # Create timestamp for backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Build backup filename: prefix_timestamp_originalname
        backup_name = f"{prefix}_{timestamp}_{file_path.name}"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Copy file or directory to backup location
            if file_path.is_dir():
                # For directories, use copytree
                shutil.copytree(file_path, backup_path)
            else:
                # For files, use copy2
                shutil.copy2(file_path, backup_path)
            return backup_path
        except PermissionError as e:
            raise PermissionError(f"Unable to create backup: {e}")
            
    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore file from backup.
        
        Args:
            backup_path: Path to backup file
            target_path: Path where to restore the file
            
        Returns:
            True if restore successful, False otherwise
            
        Raises:
            FileNotFoundError: If backup file doesn't exist
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
        try:
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy backup to target location
            if backup_path.is_dir():
                # For directories, remove existing target and use copytree
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(backup_path, target_path)
            else:
                # For files, use copy2
                shutil.copy2(backup_path, target_path)
            return True
        except Exception:
            return False
            
    def list_backups(self, prefix: str = None) -> List[Path]:
        """List available backups.
        
        Args:
            prefix: Optional prefix to filter backups
            
        Returns:
            List of backup file paths, sorted by modification time (newest first)
        """
        if not self.backup_dir.exists():
            return []
            
        # Get all backup files
        if prefix:
            pattern = f"{prefix}_*"
            backup_files = list(self.backup_dir.glob(pattern))
        else:
            backup_files = [f for f in self.backup_dir.iterdir() if f.is_file()]
            
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        return backup_files
        
    def cleanup_old_backups(self, max_age_days: int = 30) -> None:
        """Remove backups older than max_age_days.
        
        Args:
            max_age_days: Maximum age in days to keep backups
        """
        if not self.backup_dir.exists():
            return
            
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        # Check each backup file
        for backup_file in self.backup_dir.iterdir():
            if not backup_file.is_file():
                continue
                
            # Get file modification time
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            # Remove if older than cutoff
            if file_mtime < cutoff_date:
                try:
                    backup_file.unlink()
                except Exception:
                    # Continue cleanup even if one file fails
                    pass
                    
    def backup_json_section(self, file_path: Path, section_key: str) -> Path:
        """Backup specific section of JSON file.
        
        Args:
            file_path: Path to JSON file
            section_key: Key of section to backup
            
        Returns:
            Path to backup file containing only the specified section
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
            KeyError: If section_key doesn't exist in JSON
        """
        if not file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
            
        # Read and parse JSON file
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in {file_path}: {e.msg}", e.doc, e.pos)
            
        # Extract section
        if section_key not in data:
            raise KeyError(f"Section '{section_key}' not found in JSON file")
            
        section_data = data[section_key]
        
        # Create backup filename with section name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"json_section_{section_key}_{timestamp}_{file_path.name}"
        backup_path = self.backup_dir / backup_name
        
        # Write section to backup file
        with open(backup_path, 'w') as f:
            json.dump({section_key: section_data}, f, indent=2)
            
        return backup_path