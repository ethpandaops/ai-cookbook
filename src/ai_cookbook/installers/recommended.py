"""Recommended tools installer for ai-cookbook."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Set

from ..installers.base import InteractiveInstaller, InstallationResult
from ..installers.commands import CommandsInstaller
from ..installers.code_standards import CodeStandardsInstaller
from ..installers.hooks import HooksInstaller
from ..installers.scripts import ScriptsInstaller
from ..utils.file_operations import file_exists

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class RecommendedToolsInstaller(InteractiveInstaller):
    """Installer for recommended tools configuration.
    
    Manages installation of the exact set of tools recommended by the team.
    Safely uninstalls ethPandaOps tools not in the recommended set.
    """
    
    def __init__(self):
        """Initialize recommended tools installer."""
        super().__init__(
            name="Recommended Tools",
            description="Install team's recommended tools and remove non-recommended ones"
        )
        self.config_path = PROJECT_ROOT / "recommended-tools.yaml"
        self.config = None
        self.installers = {
            'commands': CommandsInstaller(),
            'code_standards': CodeStandardsInstaller(),
            'hooks': HooksInstaller(),
            'scripts': ScriptsInstaller()
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load recommended tools configuration from YAML file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if self.config is None:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                
        return self.config
        
    def check_status(self) -> Dict[str, Any]:
        """Check status of recommended tools installation.
        
        Returns:
            Dictionary with status information
        """
        try:
            config = self._load_config()
            
            status = {
                'config_loaded': True,
                'recommended_tools': {
                    'commands': config.get('commands', []),
                    'code_standards': config.get('code_standards', []),
                    'hooks': config.get('hooks', []),
                    'scripts': config.get('scripts', [])
                },
                'installed_tools': {},
                'missing_tools': {},
                'extra_tools': {},
                'compliance_score': 0.0
            }
            
            # Check each installer type
            for installer_name, installer in self.installers.items():
                installer_status = installer.check_status()
                recommended = set(config.get(installer_name, []))
                
                if installer_name == 'hooks':
                    # For hooks, check both global and local
                    installed_global = set(installer_status.get('global_hooks', []))
                    installed_local = set(installer_status.get('local_hooks', []))
                    installed = installed_global | installed_local
                elif installer_name == 'scripts':
                    # For scripts, check if scripts are in PATH
                    if installer_status.get('installed', False):
                        installed = set(['all'])
                    else:
                        installed = set()
                else:
                    installed = set(installer_status.get('installed_items', []))
                
                status['installed_tools'][installer_name] = list(installed)
                status['missing_tools'][installer_name] = list(recommended - installed)
                status['extra_tools'][installer_name] = list(installed - recommended)
                
                
            return status
            
        except Exception as e:
            return {
                'config_loaded': False,
                'error': str(e),
                'compliance_score': 0.0
            }
            
    def install(self, skip_confirmation: bool = False) -> InstallationResult:
        """Install recommended tools and remove non-recommended ones.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            config = self._load_config()
            
            # Check if confirmation is required
            if not skip_confirmation:
                print("This will install recommended tools and remove non-recommended ethPandaOps tools.")
                print("Only ethPandaOps-managed tools will be removed - other tools are safe.")
                response = input("Continue? (y/N): ").lower().strip()
                if response != 'y':
                    return InstallationResult(False, "Installation cancelled by user")
            
            results = {
                'installed': {},
                'uninstalled': {},
                'errors': []
            }
            
            # Install missing recommended tools
            for installer_name, recommended_tools in config.items():
                    
                if installer_name not in self.installers:
                    continue
                    
                installer = self.installers[installer_name]
                
                # Handle scripts installer specially (installs all at once)
                if installer_name == 'scripts':
                    try:
                        result = installer.install()
                        if result.success:
                            if installer_name not in results['installed']:
                                results['installed'][installer_name] = []
                            results['installed'][installer_name].append('all scripts')
                        else:
                            results['errors'].append(f"Failed to install scripts: {result.message}")
                    except Exception as e:
                        results['errors'].append(f"Error installing scripts: {str(e)}")
                    continue
                
                # Install each recommended tool for other installers
                installer_status = installer.check_status()
                
                for tool_name in recommended_tools:
                    try:
                        # Check if tool is already installed
                        if installer_name == 'hooks':
                            installed_global = set(installer_status.get('global_hooks', []))
                            installed_local = set(installer_status.get('local_hooks', []))
                            already_installed = tool_name in (installed_global | installed_local)
                        else:
                            installed = set(installer_status.get('installed_items', []))
                            already_installed = tool_name in installed
                        
                        if already_installed:
                            # Skip if already installed
                            if installer_name not in results['installed']:
                                results['installed'][installer_name] = []
                            results['installed'][installer_name].append(f"{tool_name} (already installed)")
                            continue
                        
                        if installer_name == 'hooks':
                            # Use global mode by default
                            installer.set_mode('global')
                            result = installer.install_hook(tool_name)
                        elif installer_name == 'commands':
                            result = installer.install_command(tool_name)
                        elif installer_name == 'code_standards':
                            result = installer.install_language(tool_name)
                        else:
                            continue
                            
                        if result.success:
                            if installer_name not in results['installed']:
                                results['installed'][installer_name] = []
                            results['installed'][installer_name].append(tool_name)
                        else:
                            results['errors'].append(f"Failed to install {tool_name} ({installer_name}): {result.message}")
                            
                    except Exception as e:
                        results['errors'].append(f"Error installing {tool_name} ({installer_name}): {str(e)}")
            
            # Remove non-recommended ethPandaOps tools
            uninstall_results = self._remove_non_recommended_tools(config)
            results['uninstalled'] = uninstall_results.get('uninstalled', {})
            results['errors'].extend(uninstall_results.get('errors', []))
            
            # Calculate success
            total_installed = sum(len(tools) for tools in results['installed'].values())
            total_uninstalled = sum(len(tools) for tools in results['uninstalled'].values())
            total_errors = len(results['errors'])
            
            if total_errors > 0:
                return InstallationResult(
                    False,
                    f"Completed with {total_errors} errors.",
                    results
                )
            
            return InstallationResult(
                True,
                f"Successfully installed recommended tools!",
                results
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install recommended tools: {str(e)}"
            )
            
    def uninstall(self) -> InstallationResult:
        """Uninstall all recommended tools.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            config = self._load_config()
            
            results = {
                'uninstalled': {},
                'errors': []
            }
            
            # Uninstall all recommended tools
            for installer_name, recommended_tools in config.items():
                    
                if installer_name not in self.installers:
                    continue
                    
                installer = self.installers[installer_name]
                
                # Uninstall each recommended tool
                for tool_name in recommended_tools:
                    try:
                        if installer_name == 'hooks':
                            # Try both global and local modes
                            for mode in ['global', 'local']:
                                installer.set_mode(mode)
                                result = installer.uninstall_hook(tool_name)
                                if result.success:
                                    if installer_name not in results['uninstalled']:
                                        results['uninstalled'][installer_name] = []
                                    results['uninstalled'][installer_name].append(f"{tool_name} ({mode})")
                        elif installer_name == 'commands':
                            result = installer.uninstall_command(tool_name)
                        elif installer_name == 'code_standards':
                            result = installer.uninstall_language(tool_name)
                        elif installer_name == 'scripts':
                            # Scripts installer uninstalls all scripts at once
                            result = installer.uninstall()
                        else:
                            continue
                            
                        if result.success and installer_name != 'hooks':
                            if installer_name not in results['uninstalled']:
                                results['uninstalled'][installer_name] = []
                            results['uninstalled'][installer_name].append(tool_name)
                        elif not result.success:
                            results['errors'].append(f"Failed to uninstall {tool_name} ({installer_name}): {result.message}")
                            
                    except Exception as e:
                        results['errors'].append(f"Error uninstalling {tool_name} ({installer_name}): {str(e)}")
            
            total_uninstalled = sum(len(tools) for tools in results['uninstalled'].values())
            total_errors = len(results['errors'])
            
            if total_errors > 0:
                return InstallationResult(
                    False,
                    f"Completed with {total_errors} errors. Uninstalled {total_uninstalled} tools.",
                    results
                )
            
            return InstallationResult(
                True,
                f"Successfully uninstalled {total_uninstalled} recommended tools.",
                results
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall recommended tools: {str(e)}"
            )
            
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about recommended tools.
        
        Returns:
            Dictionary with detailed installer information
        """
        try:
            config = self._load_config()
            status = self.check_status()
            
            return {
                'name': self.name,
                'description': self.description,
                'config_path': str(self.config_path),
                'config_loaded': status.get('config_loaded', False),
                'compliance_score': status.get('compliance_score', 0.0),
                'recommended_tools': status.get('recommended_tools', {}),
                'installed_tools': status.get('installed_tools', {}),
                'missing_tools': status.get('missing_tools', {}),
                'extra_tools': status.get('extra_tools', {}),
                'error': status.get('error')
            }
            
        except Exception as e:
            return {
                'name': self.name,
                'description': self.description,
                'error': str(e),
                'config_loaded': False
            }
            
    def _remove_non_recommended_tools(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove ethPandaOps tools that are not in the recommended set.
        
        Args:
            config: Loaded configuration dictionary
            
        Returns:
            Dictionary with uninstallation results
        """
        results = {
            'uninstalled': {},
            'errors': []
        }
        
        # Default safety settings
        ethpandaops_markers = ['ethpandaops', 'ai-cookbook', 'pandaops-cookbook']
        protected_patterns = ['user-custom', 'project-specific', 'local-override']
        
        # Check each installer type
        for installer_name, installer in self.installers.items():
            recommended = set(config.get(installer_name, []))
            installer_status = installer.check_status()
            
            if installer_name == 'hooks':
                # For hooks, check both global and local
                installed_global = set(installer_status.get('global_hooks', []))
                installed_local = set(installer_status.get('local_hooks', []))
                
                # Remove non-recommended hooks from global
                for hook_name in installed_global - recommended:
                    if self._is_ethpandaops_tool(hook_name, ethpandaops_markers, protected_patterns):
                        try:
                            installer.set_mode('global')
                            result = installer.uninstall_hook(hook_name)
                            if result.success:
                                if installer_name not in results['uninstalled']:
                                    results['uninstalled'][installer_name] = []
                                results['uninstalled'][installer_name].append(f"{hook_name} (global)")
                        except Exception as e:
                            results['errors'].append(f"Error removing {hook_name} (global): {str(e)}")
                
                # Remove non-recommended hooks from local
                for hook_name in installed_local - recommended:
                    if self._is_ethpandaops_tool(hook_name, ethpandaops_markers, protected_patterns):
                        try:
                            installer.set_mode('local')
                            result = installer.uninstall_hook(hook_name)
                            if result.success:
                                if installer_name not in results['uninstalled']:
                                    results['uninstalled'][installer_name] = []
                                results['uninstalled'][installer_name].append(f"{hook_name} (local)")
                        except Exception as e:
                            results['errors'].append(f"Error removing {hook_name} (local): {str(e)}")
            else:
                # For other installers
                installed = set(installer_status.get('installed_items', []))
                
                # Remove non-recommended tools
                for tool_name in installed - recommended:
                    if self._is_ethpandaops_tool(tool_name, ethpandaops_markers, protected_patterns):
                        try:
                            if installer_name == 'commands':
                                result = installer.uninstall_command(tool_name)
                                if result.success:
                                    if installer_name not in results['uninstalled']:
                                        results['uninstalled'][installer_name] = []
                                    results['uninstalled'][installer_name].append(tool_name)
                            elif installer_name == 'code_standards':
                                result = installer.uninstall_language(tool_name)
                                if result.success:
                                    if installer_name not in results['uninstalled']:
                                        results['uninstalled'][installer_name] = []
                                    results['uninstalled'][installer_name].append(tool_name)
                            elif installer_name == 'scripts':
                                # Scripts are managed as a single unit, skip individual removal
                                # Only remove if scripts are not in the recommended list at all
                                if not recommended:
                                    result = installer.uninstall()
                                    if result.success:
                                        if installer_name not in results['uninstalled']:
                                            results['uninstalled'][installer_name] = []
                                        results['uninstalled'][installer_name].append('all scripts')
                                continue
                        except Exception as e:
                            results['errors'].append(f"Error removing {tool_name} ({installer_name}): {str(e)}")
        
        return results
        
    def _is_ethpandaops_tool(self, tool_name: str, ethpandaops_markers: List[str], protected_patterns: List[str]) -> bool:
        """Check if a tool is managed by ethPandaOps and safe to remove.
        
        Args:
            tool_name: Name of the tool to check
            ethpandaops_markers: Patterns that identify ethPandaOps tools
            protected_patterns: Patterns that identify protected tools
            
        Returns:
            True if tool can be safely removed, False otherwise
        """
        # Check if tool is protected
        for pattern in protected_patterns:
            if pattern.lower() in tool_name.lower():
                return False
                
        # Check if tool is managed by ethPandaOps
        for marker in ethpandaops_markers:
            if marker.lower() in tool_name.lower():
                return True
                
        # Default to safe removal for known ethPandaOps tools
        # This is a conservative approach - only remove tools we're confident about
        known_ethpandaops_tools = {
            # Commands (with .md extension)
            'init-project-ai-docs.md', 'prime-context.md', 'init-component-ai-docs.md',
            'parallel-repository-tasks.md', 'create-implementation-plan.md', 
            'create-implementation-plan-v2.md', 'create-implementation-plan-v3.md',
            'review-implementation-plan.md', 'eip.md', 'create-feedback-loop.md',
            'create-presentation.md', 'prepare-one-shot.md',
            # Code standards (without extension)
            'go', 'python', 'rust', 'tailwindcss',
            # Hooks (without extension)
            'eslint', 'gofmt', 'golangci-lint', 'typescript',
            # Scripts
            'init-ai-docs.py', 'all'
        }
        
        return tool_name in known_ethpandaops_tools
        
    def build_interactive_options(self) -> None:
        """Build interactive options for recommended tools."""
        self.clear_interactive_options()
        
        status = self.check_status()
        
        if not status.get('config_loaded'):
            self.add_interactive_option(
                "Configuration Error",
                f"Cannot load recommended tools configuration: {status.get('error', 'Unknown error')}",
                lambda: None
            )
            return
        
        compliance = status.get('compliance_score', 0.0)
        missing = status.get('missing_tools', {})
        extra = status.get('extra_tools', {})
        
        total_missing = sum(len(tools) for tools in missing.values())
        total_extra = sum(len(tools) for tools in extra.values())
        
        
        # Install recommended tools option
        self.add_interactive_option(
            "✅ Install Recommended Tools",
            "Install team's recommended configuration",
            lambda: self.install(skip_confirmation=True)
        )
            
