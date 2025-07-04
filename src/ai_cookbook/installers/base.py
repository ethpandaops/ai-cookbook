from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from ..utils.backup import BackupManager
from ..utils.file_operations import ensure_directory
from ..config.settings import CLAUDE_DIR


class InstallationResult:
    """Result of an installation operation.
    
    Provides detailed feedback about the success or failure of an installation,
    including any relevant details for debugging or user information.
    """
    
    def __init__(self, success: bool, message: str, details: Dict[str, Any] = None):
        """Initialize installation result.
        
        Args:
            success: Whether the operation was successful
            message: Human-readable message about the result
            details: Optional additional details about the operation
        """
        self.success = success
        self.message = message
        self.details = details or {}
        
    def __repr__(self) -> str:
        """String representation of the result."""
        return f"InstallationResult(success={self.success}, message='{self.message}')"


class BaseInstaller(ABC):
    """Base class for all installers.
    
    Provides common functionality and interface that all specific installers
    must implement. This ensures consistency across different installer types.
    """
    
    def __init__(self, name: str, description: str):
        """Initialize base installer.
        
        Args:
            name: Display name of the installer
            description: Brief description of what this installer does
        """
        self.name = name
        self.description = description
        self.backup_manager = BackupManager()
        
    @abstractmethod
    def check_status(self) -> Dict[str, Any]:
        """Check installation status.
        
        Returns:
            Dictionary containing status information. Must include at least:
            - 'installed': bool indicating if component is installed
            - Other installer-specific status details
        """
        pass
        
    @abstractmethod
    def install(self) -> InstallationResult:
        """Install the component.
        
        Returns:
            InstallationResult indicating success/failure and details
        """
        pass
        
    @abstractmethod
    def uninstall(self) -> InstallationResult:
        """Uninstall the component.
        
        Returns:
            InstallationResult indicating success/failure and details
        """
        pass
        
    @abstractmethod
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about this installer.
        
        Returns:
            Dictionary containing detailed information about the installer,
            such as available options, current configuration, file paths, etc.
        """
        pass
        
    def is_installed(self) -> bool:
        """Check if component is installed.
        
        Returns:
            True if component is installed, False otherwise
        """
        status = self.check_status()
        return status.get('installed', False)
        
    def get_status_string(self) -> str:
        """Get human-readable status string.
        
        Returns:
            Status string suitable for display in UI
        """
        return "INSTALLED" if self.is_installed() else "NOT INSTALLED"
        
    def validate_prerequisites(self) -> InstallationResult:
        """Validate prerequisites for installation.
        
        Can be overridden by subclasses to add specific prerequisite checks.
        
        Returns:
            InstallationResult indicating if prerequisites are met
        """
        # Default implementation - no prerequisites
        return InstallationResult(True, "Prerequisites met")
        
    def create_required_directories(self) -> None:
        """Create any required directories for this installer.
        
        Can be overridden by subclasses to create specific directories.
        """
        # Ensure base Claude directory exists
        ensure_directory(CLAUDE_DIR)


class InteractiveInstaller(BaseInstaller):
    """Base class for installers with interactive options.
    
    Extends BaseInstaller to support interactive menu options for installers
    that need more granular control (like the hooks installer).
    """
    
    def __init__(self, name: str, description: str):
        """Initialize interactive installer.
        
        Args:
            name: Display name of the installer
            description: Brief description of what this installer does
        """
        super().__init__(name, description)
        self._interactive_options: List[Dict[str, Any]] = []
        
    def add_interactive_option(self, name: str, description: str, 
                             action: Callable, status_checker: Callable = None) -> None:
        """Add an interactive option.
        
        Args:
            name: Display name of the option
            description: Description of what this option does
            action: Callable that performs the action
            status_checker: Optional callable that returns current status
        """
        option = {
            'name': name,
            'description': description,
            'action': action,
            'status_checker': status_checker
        }
        self._interactive_options.append(option)
        
    def get_interactive_options(self) -> List[Dict[str, Any]]:
        """Get list of interactive options.
        
        Returns:
            List of dictionaries containing option information
        """
        return self._interactive_options.copy()
        
    def clear_interactive_options(self) -> None:
        """Clear all interactive options.
        
        Useful for rebuilding options based on current state.
        """
        self._interactive_options.clear()
        
    def build_interactive_options(self) -> None:
        """Build interactive options based on current state.
        
        Should be overridden by subclasses to populate options dynamically.
        """
        # Default implementation - no options
        pass
        
    def refresh_options(self) -> None:
        """Refresh interactive options.
        
        Clears existing options and rebuilds them based on current state.
        """
        self.clear_interactive_options()
        self.build_interactive_options()