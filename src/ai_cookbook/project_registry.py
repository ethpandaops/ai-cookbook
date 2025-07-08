"""Registry for tracking projects with local ai-cookbook installations."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from .config.settings import CLAUDE_DIR, PROJECTS_FILE_NAME


class ProjectRegistry:
    """Manages registry of projects with local ai-cookbook installations."""
    
    REGISTRY_FILE = CLAUDE_DIR / PROJECTS_FILE_NAME
    
    def __init__(self) -> None:
        """Initialize project registry."""
        self.logger = logging.getLogger(__name__)
        self.projects = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load project registry from file.
        
        Returns:
            Dictionary mapping project paths to their metadata
        """
        if not self.REGISTRY_FILE.exists():
            return {}
        
        try:
            with open(self.REGISTRY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Failed to load project registry from {self.REGISTRY_FILE}: {e}")
            return {}
    
    def _save_registry(self):
        """Save project registry to file."""
        self.REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.REGISTRY_FILE, 'w') as f:
            json.dump(self.projects, f, indent=2)
    
    def register_project(self, project_path: Path, component_types: List[str]):
        """Register a project with local installations.
        
        Args:
            project_path: Path to the project directory
            component_types: List of component types installed locally (e.g., ['hooks', 'commands'])
        """
        project_str = str(project_path.resolve())
        
        if project_str not in self.projects:
            self.projects[project_str] = {
                'components': [],
                'last_updated': None
            }
        
        # Update component types
        existing = set(self.projects[project_str]['components'])
        existing.update(component_types)
        self.projects[project_str]['components'] = sorted(list(existing))
        
        # Update timestamp
        import time
        self.projects[project_str]['last_updated'] = time.time()
        
        self._save_registry()
    
    def unregister_project(self, project_path: Path, component_types: List[str] = None):
        """Unregister a project or specific components.
        
        Args:
            project_path: Path to the project directory
            component_types: Specific components to unregister, or None to remove project entirely
        """
        project_str = str(project_path.resolve())
        
        if project_str not in self.projects:
            return
        
        if component_types is None:
            # Remove entire project
            del self.projects[project_str]
        else:
            # Remove specific components
            existing = set(self.projects[project_str]['components'])
            for comp in component_types:
                existing.discard(comp)
            
            if existing:
                self.projects[project_str]['components'] = sorted(list(existing))
            else:
                # No components left, remove project
                del self.projects[project_str]
        
        self._save_registry()
    
    def get_projects_with_component(self, component_type: str) -> List[Path]:
        """Get all projects that have a specific component type installed.
        
        Args:
            component_type: Type of component (e.g., 'hooks', 'commands')
            
        Returns:
            List of project paths
        """
        projects = []
        for project_path, info in self.projects.items():
            if component_type in info.get('components', []):
                path = Path(project_path)
                if path.exists():
                    projects.append(path)
        
        return projects
    
    def cleanup_missing_projects(self) -> List[str]:
        """Remove projects that no longer exist from registry.
        
        Returns:
            List of removed project paths
        """
        removed = []
        for project_path in list(self.projects.keys()):
            if not Path(project_path).exists():
                del self.projects[project_path]
                removed.append(project_path)
        
        if removed:
            self._save_registry()
        
        return removed