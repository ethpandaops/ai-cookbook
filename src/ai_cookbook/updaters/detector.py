"""Update detection for installed ai-cookbook components."""

import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config.settings import META_FILE_NAME


@dataclass
class ComponentMetadata:
    """Metadata for an installed component."""
    source: str  # 'ethpandaops' or 'user'
    source_path: Optional[str]  # Relative path in repo
    source_hash: Optional[str]  # Hash of source file
    source_mtime: Optional[float]  # Source file modification time
    installed_at: float  # Installation timestamp
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class UpdateStatus:
    """Status of updates for a component category."""
    updated: List[str]  # Files that have updates
    new: List[str]  # New files to install
    deleted: List[str]  # Files to delete (removed from repo)
    unchanged: List[str]  # Files that are up to date
    
    @property
    def has_changes(self) -> bool:
        """Check if any changes are available."""
        return bool(self.updated or self.new or self.deleted)
    
    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return len(self.updated) + len(self.new) + len(self.deleted)


class UpdateDetector:
    """Detects updates for installed ai-cookbook components."""
    
    METADATA_FILE = META_FILE_NAME
    CHUNK_SIZE = 65536  # 64KB chunks for hashing
    
    def __init__(self, source_path: Path, install_path: Path, debug: bool = False):
        """Initialize update detector.
        
        Args:
            source_path: Path to source files in repo
            install_path: Path to installed files
            debug: Enable debug output
        """
        self.source_path = source_path
        self.install_path = install_path
        self.metadata_path = install_path / self.METADATA_FILE
        self.metadata = self._load_metadata()
        self._debug = debug or os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
    
    def _load_metadata(self) -> Dict[str, ComponentMetadata]:
        """Load metadata from file."""
        if not self.metadata_path.exists():
            return {}
        
        try:
            with open(self.metadata_path, 'r') as f:
                data = json.load(f)
                return {
                    name: ComponentMetadata(**meta) 
                    for name, meta in data.items()
                }
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _save_metadata(self):
        """Save metadata to file."""
        data = {
            name: meta.to_dict() 
            for name, meta in self.metadata.items()
        }
        
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _compute_file_hash(self, path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            while chunk := f.read(self.CHUNK_SIZE):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _get_file_info(self, path: Path) -> Tuple[float, int]:
        """Get file modification time and size."""
        stat = path.stat()
        return stat.st_mtime, stat.st_size
    
    def _needs_update(self, source_file: Path, installed_file: Path, 
                     metadata: Optional[ComponentMetadata]) -> bool:
        """Check if an installed file needs updating.
        
        Args:
            source_file: Path to source file in repo
            installed_file: Path to installed file
            metadata: Metadata for the installed file
            
        Returns:
            True if file needs update
        """
        if not installed_file.exists():
            return True
        
        # Quick check: different sizes mean definitely changed
        source_size = source_file.stat().st_size
        installed_size = installed_file.stat().st_size
        if source_size != installed_size:
            return True
        
        # If we have metadata, check if source hasn't changed
        source_mtime = source_file.stat().st_mtime
        if metadata and source_mtime == metadata.source_mtime:
            # Source hasn't changed since last check
            installed_hash = self._compute_file_hash(installed_file)
            return installed_hash != metadata.source_hash
        
        # Otherwise, compute both hashes
        source_hash = self._compute_file_hash(source_file)
        installed_hash = self._compute_file_hash(installed_file)
        return source_hash != installed_hash
    
    def reconcile_metadata(self):
        """Sync metadata with the actual filesystem.

        - Remove stale entries: metadata exists but installed file doesn't
        - Create missing entries: installed file exists with a matching source but no metadata
        """
        changed = False

        # Remove stale entries (metadata points to files that don't exist on disk)
        stale_keys = []
        for name, meta in self.metadata.items():
            if meta.source != 'ethpandaops':
                continue
            installed_file = self.install_path / name
            if not installed_file.exists():
                stale_keys.append(name)
                if self._debug:
                    print(f"[DEBUG] reconcile: removing stale metadata for '{name}' (file missing)")

        for key in stale_keys:
            del self.metadata[key]
            changed = True

        # Create missing entries (installed files with matching source but no metadata)
        if self.source_path.exists() and self.install_path.exists():
            # Build map of source files keyed by their relative path from source_path
            source_files = {}
            for file in self.source_path.rglob('*'):
                if file.is_file() and file.name != self.METADATA_FILE:
                    rel_path = str(file.relative_to(self.source_path))
                    source_files[rel_path] = file

            # Scan installed ethpandaops files
            dirs_to_scan = []
            if 'ethpandaops' in str(self.install_path):
                dirs_to_scan.append(self.install_path)
            else:
                ethpandaops_dir = self.install_path / 'ethpandaops'
                if ethpandaops_dir.exists():
                    dirs_to_scan.append(ethpandaops_dir)

            for scan_dir in dirs_to_scan:
                for file_path in scan_dir.rglob('*'):
                    if not file_path.is_file() or file_path.name == self.METADATA_FILE:
                        continue
                    if file_path.suffix == '.bak':
                        continue

                    rel_to_install = str(file_path.relative_to(self.install_path))
                    if rel_to_install in self.metadata:
                        continue

                    # Try to find a matching source file
                    # For hooks: installed as "gofmt.sh", source is "gofmt/hook.sh"
                    # For code-standards: installed as "go/CLAUDE.md", source is "go/CLAUDE.md"
                    matching_source_path = None
                    matching_source_file = None

                    # Direct match (code-standards style)
                    if rel_to_install in source_files:
                        matching_source_path = rel_to_install
                        matching_source_file = source_files[rel_to_install]
                    else:
                        # Hook-style match: "hookname.sh" -> "hookname/hook.sh"
                        stem = file_path.stem  # e.g. "gofmt"
                        hook_source_key = f"{stem}/hook.sh"
                        if hook_source_key in source_files:
                            matching_source_path = hook_source_key
                            matching_source_file = source_files[hook_source_key]

                    if matching_source_file:
                        source_hash = self._compute_file_hash(matching_source_file)
                        source_mtime = matching_source_file.stat().st_mtime
                        self.metadata[rel_to_install] = ComponentMetadata(
                            source='ethpandaops',
                            source_path=matching_source_path,
                            source_hash=source_hash,
                            source_mtime=source_mtime,
                            installed_at=file_path.stat().st_mtime
                        )
                        changed = True
                        if self._debug:
                            print(f"[DEBUG] reconcile: created metadata for '{rel_to_install}' "
                                  f"(source: {matching_source_path})")

        if changed:
            self._save_metadata()

    def check_updates(self, installed_only: bool = True, check_orphaned: bool = True) -> UpdateStatus:
        """Check for available updates.
        
        Args:
            installed_only: Only check files that are already installed
            check_orphaned: Check for orphaned ethpandaops files without metadata
            
        Returns:
            UpdateStatus with lists of changed files
        """
        # Reconcile metadata with filesystem before checking
        self.reconcile_metadata()

        updated = []
        new = []
        deleted = []
        unchanged = []

        # Get all source files
        source_files = {}
        if self.source_path.exists():
            for file in self.source_path.rglob('*'):
                if file.is_file() and file.name != self.METADATA_FILE:
                    rel_path = file.relative_to(self.source_path)
                    source_files[str(rel_path)] = file
        
        if self._debug:
            print(f"\n[DEBUG] UpdateDetector checking updates:")
            print(f"  - Source path: {self.source_path}")
            print(f"  - Install path: {self.install_path}")
            print(f"  - Source files found: {len(source_files)}")
            print(f"  - Metadata entries: {len(self.metadata)}")
            if len(source_files) < 20:  # Only show files if not too many
                print(f"  - Source files: {list(source_files.keys())}")
        
        # Check installed files
        checked_files = set()
        for name, meta in self.metadata.items():
            if meta.source != 'ethpandaops':
                # Skip user-created files
                continue
            
            if self._debug and name == "create-implementation-plan-v3.md":
                print(f"\n[DEBUG] Checking specific file '{name}':")
                print(f"  - Metadata source_path: {meta.source_path}")
                print(f"  - Looking for key: {meta.source_path}")
                print(f"  - Key exists in source_files: {meta.source_path in source_files if meta.source_path else 'No source_path'}")
            
            checked_files.add(name)
            installed_file = self.install_path / name
            
            if meta.source_path and meta.source_path in source_files:
                # File still exists in repo
                source_file = source_files[meta.source_path]
                if self._needs_update(source_file, installed_file, meta):
                    updated.append(name)
                else:
                    unchanged.append(name)
            else:
                # File removed from repo
                if installed_file.exists():
                    deleted.append(name)
                    # Debug: show why file is marked for deletion
                    if hasattr(self, '_debug') and self._debug:
                        print(f"[DEBUG] Marking '{name}' for deletion:")
                        print(f"  - Source path: {meta.source_path}")
                        print(f"  - Expected at: {self.source_path.parent.parent / meta.source_path}")
                        print(f"  - Source files checked: {len(source_files)}")
                        if meta.source_path:
                            print(f"  - Path in source_files: {meta.source_path in source_files}")
        
        # Check for new files (if not installed_only)
        if not installed_only:
            for rel_path, source_file in source_files.items():
                if str(rel_path) not in checked_files:
                    installed_file = self.install_path / rel_path
                    if not installed_file.exists():
                        new.append(str(rel_path))
        
        # Check for orphaned files if requested
        if check_orphaned:
            orphaned = self._find_orphaned_files(source_files, checked_files)
            deleted.extend(orphaned)
            
            if self._debug:
                print(f"\n[DEBUG] Found {len(orphaned)} orphaned files to add to deleted list")
                if orphaned:
                    for file in orphaned[:5]:
                        print(f"  - {file}")
                    if len(orphaned) > 5:
                        print(f"  ... and {len(orphaned) - 5} more")
                print(f"[DEBUG] Total deleted after adding orphaned: {len(deleted)}")
        
        return UpdateStatus(
            updated=sorted(updated),
            new=sorted(new),
            deleted=sorted(deleted),
            unchanged=sorted(unchanged)
        )
    
    def update_metadata(self, file_name: str, source_file: Path):
        """Update metadata for a file after installation.
        
        Args:
            file_name: Name of the installed file
            source_file: Path to source file in repo
        """
        source_mtime, _ = self._get_file_info(source_file)
        source_hash = self._compute_file_hash(source_file)
        
        # Store relative path from source directory (not repo root)
        # This ensures consistency with how we build source_files dict
        try:
            relative_path = source_file.relative_to(self.source_path)
        except ValueError:
            # If file is not under source_path, use the filename
            relative_path = Path(file_name)
        
        self.metadata[file_name] = ComponentMetadata(
            source='ethpandaops',
            source_path=str(relative_path),
            source_hash=source_hash,
            source_mtime=source_mtime,
            installed_at=time.time()
        )
        
        self._save_metadata()
    
    def remove_metadata(self, file_name: str):
        """Remove metadata for a deleted file.
        
        Args:
            file_name: Name of the file to remove
        """
        if file_name in self.metadata:
            del self.metadata[file_name]
            self._save_metadata()
    
    def _find_orphaned_files(self, source_files: Dict[str, Path], checked_files: set) -> List[str]:
        """Find orphaned ethpandaops files without metadata.
        
        Args:
            source_files: Dictionary of source files from repo
            checked_files: Set of files already checked via metadata
            
        Returns:
            List of orphaned file names to delete
        """
        orphaned = []
        
        # Determine if we're checking an ethpandaops directory
        # Check if install_path contains 'ethpandaops' in its path
        dirs_to_check = []
        
        if 'ethpandaops' in str(self.install_path):
            # This is an ethpandaops directory
            dirs_to_check.append(self.install_path)
        else:
            # Check for ethpandaops subdirectory
            ethpandaops_dir = self.install_path / 'ethpandaops'
            if ethpandaops_dir.exists() and ethpandaops_dir.is_dir():
                dirs_to_check.append(ethpandaops_dir)
        
        if self._debug:
            print(f"\n[DEBUG] _find_orphaned_files called")
            print(f"  - Dirs to check: {[str(d) for d in dirs_to_check]}")
            print(f"  - Already checked files: {checked_files}")
            
        for check_dir in dirs_to_check:
            if self._debug:
                print(f"\n[DEBUG] Scanning directory: {check_dir}")
                
            # Scan all files and directories
            for file_path in check_dir.rglob('*'):
                # For code standards, check directories too
                if file_path.is_dir() and check_dir.name == 'code-standards':
                    # Check if any files in this directory have metadata
                    dir_name = file_path.relative_to(self.install_path)
                    has_metadata = False
                    for key in self.metadata:
                        if key.startswith(str(dir_name) + '/'):
                            has_metadata = True
                            break
                    
                    if not has_metadata and file_path.name not in ['.', '..']:
                        # No files in this directory have metadata - it's orphaned
                        orphaned.append(str(dir_name))
                        
                        if self._debug:
                            print(f"\n[DEBUG] Orphaned directory found: {dir_name}")
                            print(f"  - Full path: {file_path}")
                            print(f"  - Reason: No metadata for any files in directory")
                
                if file_path.is_file() and file_path.name != self.METADATA_FILE:
                    # Get relative path from install directory
                    rel_path = file_path.relative_to(self.install_path)
                    file_name = str(rel_path)
                    
                    # Skip if already checked via metadata
                    if file_name in checked_files:
                        continue
                    
                    # Skip backup files
                    if file_path.suffix == '.bak':
                        continue
                    
                    # If it's in ethpandaops dir and has no metadata, it's orphaned
                    # We don't need to check if it exists in source - no metadata = remove it
                    orphaned.append(file_name)
                    
                    if self._debug:
                        print(f"\n[DEBUG] Orphaned file found: {file_name}")
                        print(f"  - Full path: {file_path}")
                        print(f"  - Reason: No metadata in ethpandaops directory")
        
        if self._debug:
            print(f"\n[DEBUG] _find_orphaned_files returning {len(orphaned)} items: {orphaned[:3]}...")
            
        return orphaned