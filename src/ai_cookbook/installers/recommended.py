"""Recommended tools installer for ai-cookbook."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Set

from ..installers.base import InteractiveInstaller, InstallationResult
from ..installers.commands import CommandsInstaller
from ..installers.code_standards import CodeStandardsInstaller
from ..installers.hooks import HooksInstaller
from ..installers.agents import AgentsInstaller
from ..installers.mcp_servers import MCPServersInstaller
from ..installers.scripts import ScriptsInstaller
from ..utils.file_operations import file_exists
from ..config.settings import ORG_NAME, ORG_DISPLAY_NAME

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class RecommendedToolsInstaller(InteractiveInstaller):
    """Installer for recommended tools configuration.
    
    Manages installation of the exact set of tools recommended by the team.
    Safely uninstalls {ORG_DISPLAY_NAME} tools not in the recommended set.
    """
    
    def __init__(self) -> None:
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
            'agents': AgentsInstaller(),
            'mcp_servers': MCPServersInstaller(),
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
                    'agents': config.get('agents', []),
                    'mcp_servers': config.get('mcp_servers', []),
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
                elif installer_name == 'mcp_servers':
                    # For MCP servers, get installed server names
                    installed = set(installer_status.get('installed_servers', {}).keys())
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
            
            if not self._confirm_installation(skip_confirmation):
                return InstallationResult(False, "Installation cancelled by user")
            
            results = self._initialize_results()
            
            self._install_recommended_tools(config, results)
            self._remove_non_recommended_tools_with_results(config, results)
            
            self._display_results(results)
            
            return self._create_installation_result(results)
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install recommended tools: {str(e)}"
            )
    
    def _confirm_installation(self, skip_confirmation: bool) -> bool:
        """Confirm installation with user unless skip_confirmation is True.
        
        Args:
            skip_confirmation: Whether to skip user confirmation
            
        Returns:
            True if installation should proceed, False otherwise
        """
        if skip_confirmation:
            return True
            
        print(f"This will install recommended tools and remove non-recommended {ORG_DISPLAY_NAME} tools.")
        print(f"Only {ORG_DISPLAY_NAME}-managed tools will be removed - other tools are safe.")
        response = input("Continue? (y/N): ").lower().strip()
        return response == 'y'
    
    def _initialize_results(self) -> Dict[str, Any]:
        """Initialize results dictionary for tracking installation progress.
        
        Returns:
            Dictionary with installed, uninstalled, and errors keys
        """
        return {
            'installed': {},
            'uninstalled': {},
            'errors': []
        }
    
    def _install_recommended_tools(self, config: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Install all recommended tools based on configuration.
        
        Args:
            config: Configuration dictionary with recommended tools
            results: Results dictionary to update with installation outcomes
        """
        print(f"\n🐼 Installing recommended {ORG_DISPLAY_NAME} tools...")
        print("=" * 60)
        
        for installer_name, recommended_tools in config.items():
            if installer_name not in self.installers:
                continue
                
            installer = self.installers[installer_name]
            
            # Handle scripts installer specially (installs all at once)
            if installer_name == 'scripts':
                self._install_scripts(installer, installer_name, results)
                continue
            
            # Install each recommended tool for other installers
            installer_status = installer.check_status()
            
            for tool_name in recommended_tools:
                self._install_single_tool(
                    installer, installer_name, tool_name, 
                    installer_status, results
                )
    
    def _install_scripts(self, installer, installer_name: str, results: Dict[str, Any]) -> None:
        """Install scripts using the scripts installer.
        
        Args:
            installer: Scripts installer instance
            installer_name: Name of the installer ('scripts')
            results: Results dictionary to update
        """
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
    
    def _install_single_tool(self, installer, installer_name: str, tool_name: str, 
                           installer_status: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Install a single tool using the appropriate installer method.
        
        Args:
            installer: Installer instance to use
            installer_name: Name of the installer type
            tool_name: Name of the tool to install
            installer_status: Current status of the installer
            results: Results dictionary to update
        """
        try:
            # Check if tool is already installed
            if self._is_tool_installed(installer_name, tool_name, installer_status):
                if installer_name not in results['installed']:
                    results['installed'][installer_name] = []
                results['installed'][installer_name].append(f"{tool_name} (already installed)")
                print(f"  ⏩ {tool_name} ({installer_name}) - already installed")
                return
            
            print(f"  📦 Installing {tool_name} ({installer_name})...")
            
            # Install the tool using appropriate method
            result = self._execute_install(installer, installer_name, tool_name)
            
            if result and result.success:
                if installer_name not in results['installed']:
                    results['installed'][installer_name] = []
                results['installed'][installer_name].append(tool_name)
                print(f"     ✅ Successfully installed {tool_name}")
            else:
                error_msg = result.message if result else "Unknown error"
                results['errors'].append(f"Failed to install {tool_name} ({installer_name}): {error_msg}")
                print(f"     ❌ Failed to install {tool_name}: {error_msg}")
                
        except Exception as e:
            results['errors'].append(f"Error installing {tool_name} ({installer_name}): {str(e)}")
    
    def _is_tool_installed(self, installer_name: str, tool_name: str, 
                          installer_status: Dict[str, Any]) -> bool:
        """Check if a tool is already installed.
        
        Args:
            installer_name: Name of the installer type
            tool_name: Name of the tool
            installer_status: Current status from the installer
            
        Returns:
            True if tool is already installed, False otherwise
        """
        if installer_name == 'hooks':
            installed_global = set(installer_status.get('global_hooks', []))
            installed_local = set(installer_status.get('local_hooks', []))
            return tool_name in (installed_global | installed_local)
        elif installer_name == 'agents':
            installed = set(installer_status.get('installed_agents', []))
            return tool_name in installed
        elif installer_name == 'mcp_servers':
            installed = set(installer_status.get('installed_servers', {}).keys())
            return tool_name in installed
        else:
            installed = set(installer_status.get('installed_items', []))
            return tool_name in installed
    
    def _execute_install(self, installer, installer_name: str, tool_name: str) -> InstallationResult:
        """Execute the appropriate install method for the tool.
        
        Args:
            installer: Installer instance
            installer_name: Name of the installer type
            tool_name: Name of the tool to install
            
        Returns:
            InstallationResult from the installer
        """
        if installer_name == 'hooks':
            # Use global mode by default
            installer.set_mode('global')
            return installer.install_hook(tool_name)
        elif installer_name == 'commands':
            return installer.install_command(tool_name)
        elif installer_name == 'code_standards':
            return installer.install_language(tool_name)
        elif installer_name == 'agents':
            return installer.install_agent(tool_name)
        elif installer_name == 'mcp_servers':
            return installer.install_server(tool_name)
        else:
            return None
    
    def _remove_non_recommended_tools_with_results(self, config: Dict[str, Any], 
                                                  results: Dict[str, Any]) -> None:
        """Remove non-recommended tools and update results.
        
        Args:
            config: Configuration with recommended tools
            results: Results dictionary to update
        """
        uninstall_results = self._remove_non_recommended_tools(config)
        results['uninstalled'] = uninstall_results.get('uninstalled', {})
        results['errors'].extend(uninstall_results.get('errors', []))
    
    def _display_results(self, results: Dict[str, Any]) -> None:
        """Display installation results to the user.
        
        Args:
            results: Results dictionary with installed, uninstalled, and errors
        """
        print("\n✅ Successfully installed recommended tools!")
        
        # Show what was installed/uninstalled
        installed = results.get('installed', {})
        uninstalled = results.get('uninstalled', {})
        
        # Display installed tools by category
        if installed:
            print("\n📦 Installed:")
            for category, tools in installed.items():
                if tools:
                    print(f"  {category.replace('_', ' ').title()}:")
                    for tool in tools:
                        if "(already installed)" not in tool:
                            print(f"    ✅ {tool}")
                        else:
                            print(f"    ⏩ {tool}")
        
        # Display uninstalled tools by category
        if uninstalled:
            print("\n🗑️  Removed (non-recommended):")
            for category, tools in uninstalled.items():
                if tools:
                    print(f"  {category.replace('_', ' ').title()}:")
                    for tool in tools:
                        print(f"    ❌ {tool}")
        
        # Display errors if any
        if results.get('errors'):
            print("\n⚠️  Errors encountered:")
            for error in results['errors']:
                print(f"  • {error}")
        
        # Summary
        total_installed = sum(len(tools) for tools in results['installed'].values())
        total_uninstalled = sum(len(tools) for tools in results['uninstalled'].values())
        total_errors = len(results['errors'])
        
        if total_installed > 0 or total_uninstalled > 0:
            print("\n📊 Summary:")
            if total_installed > 0:
                print(f"  • {total_installed} tools installed/verified")
            if total_uninstalled > 0:
                print(f"  • {total_uninstalled} non-recommended tools removed")
            if total_errors > 0:
                print(f"  • {total_errors} errors encountered")
        
        print(f"\n🎉 Your environment is now configured with the recommended {ORG_DISPLAY_NAME} tools!")
        print("\nPress any key to continue...")
    
    def _create_installation_result(self, results: Dict[str, Any]) -> InstallationResult:
        """Create final installation result based on results.
        
        Args:
            results: Results dictionary with errors and installation details
            
        Returns:
            InstallationResult with appropriate success status and message
        """
        total_errors = len(results.get('errors', []))
        
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
        """Remove {ORG_DISPLAY_NAME} tools that are not in the recommended set.
        
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
        org_markers = [ORG_NAME, 'ai-cookbook', 'pandaops-cookbook']
        protected_patterns = ['user-custom', 'project-specific', 'local-override']
        
        print("\n🔍 Checking for non-recommended tools to remove...")
        
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
                    if self._is_ethpandaops_tool(hook_name, org_markers, protected_patterns):
                        try:
                            print(f"  🗑️  Removing {hook_name} (global hook)...")
                            installer.set_mode('global')
                            result = installer.uninstall_hook(hook_name)
                            if result.success:
                                if installer_name not in results['uninstalled']:
                                    results['uninstalled'][installer_name] = []
                                results['uninstalled'][installer_name].append(f"{hook_name} (global)")
                                print(f"     ✅ Removed {hook_name}")
                            else:
                                print(f"     ❌ Failed to remove {hook_name}: {result.message}")
                        except Exception as e:
                            results['errors'].append(f"Error removing {hook_name} (global): {str(e)}")
                            print(f"     ❌ Error removing {hook_name}: {str(e)}")
                
                # Remove non-recommended hooks from local
                for hook_name in installed_local - recommended:
                    if self._is_ethpandaops_tool(hook_name, org_markers, protected_patterns):
                        try:
                            print(f"  🗑️  Removing {hook_name} (local hook)...")
                            installer.set_mode('local')
                            result = installer.uninstall_hook(hook_name)
                            if result.success:
                                if installer_name not in results['uninstalled']:
                                    results['uninstalled'][installer_name] = []
                                results['uninstalled'][installer_name].append(f"{hook_name} (local)")
                                print(f"     ✅ Removed {hook_name}")
                            else:
                                print(f"     ❌ Failed to remove {hook_name}: {result.message}")
                        except Exception as e:
                            results['errors'].append(f"Error removing {hook_name} (local): {str(e)}")
                            print(f"     ❌ Error removing {hook_name}: {str(e)}")
            else:
                # For other installers
                installed = set(installer_status.get('installed_items', []))
                
                # Remove non-recommended tools
                for tool_name in installed - recommended:
                    if self._is_ethpandaops_tool(tool_name, org_markers, protected_patterns):
                        try:
                            if installer_name == 'commands':
                                print(f"  🗑️  Removing {tool_name} (command)...")
                                result = installer.uninstall_command(tool_name)
                                if result.success:
                                    if installer_name not in results['uninstalled']:
                                        results['uninstalled'][installer_name] = []
                                    results['uninstalled'][installer_name].append(tool_name)
                                    print(f"     ✅ Removed {tool_name}")
                                else:
                                    print(f"     ❌ Failed to remove {tool_name}: {result.message}")
                            elif installer_name == 'code_standards':
                                print(f"  🗑️  Removing {tool_name} (code standard)...")
                                result = installer.uninstall_language(tool_name)
                                if result.success:
                                    if installer_name not in results['uninstalled']:
                                        results['uninstalled'][installer_name] = []
                                    results['uninstalled'][installer_name].append(tool_name)
                                    print(f"     ✅ Removed {tool_name}")
                                else:
                                    print(f"     ❌ Failed to remove {tool_name}: {result.message}")
                            elif installer_name == 'agents':
                                print(f"  🗑️  Removing {tool_name} (agent)...")
                                result = installer.uninstall_agent(tool_name)
                                if result.success:
                                    if installer_name not in results['uninstalled']:
                                        results['uninstalled'][installer_name] = []
                                    results['uninstalled'][installer_name].append(tool_name)
                                    print(f"     ✅ Removed {tool_name}")
                                else:
                                    print(f"     ❌ Failed to remove {tool_name}: {result.message}")
                            elif installer_name == 'mcp_servers':
                                print(f"  🗑️  Removing {tool_name} (MCP server)...")
                                result = installer.uninstall_server(tool_name)
                                if result.success:
                                    if installer_name not in results['uninstalled']:
                                        results['uninstalled'][installer_name] = []
                                    results['uninstalled'][installer_name].append(tool_name)
                                    print(f"     ✅ Removed {tool_name}")
                                else:
                                    print(f"     ❌ Failed to remove {tool_name}: {result.message}")
                            elif installer_name == 'scripts':
                                # Scripts are managed as a single unit, skip individual removal
                                # Only remove if scripts are not in the recommended list at all
                                if not recommended:
                                    print(f"  🗑️  Removing all scripts...")
                                    result = installer.uninstall()
                                    if result.success:
                                        if installer_name not in results['uninstalled']:
                                            results['uninstalled'][installer_name] = []
                                        results['uninstalled'][installer_name].append('all scripts')
                                        print(f"     ✅ Removed all scripts")
                                    else:
                                        print(f"     ❌ Failed to remove scripts: {result.message}")
                                continue
                        except Exception as e:
                            results['errors'].append(f"Error removing {tool_name} ({installer_name}): {str(e)}")
                            print(f"     ❌ Error removing {tool_name}: {str(e)}")
        
        return results
        
    def _is_ethpandaops_tool(self, tool_name: str, org_markers: List[str], protected_patterns: List[str]) -> bool:
        f"""Check if a tool is managed by {ORG_DISPLAY_NAME} and safe to remove.
        
        Args:
            tool_name: Name of the tool to check
            org_markers: Patterns that identify {ORG_DISPLAY_NAME} tools
            protected_patterns: Patterns that identify protected tools
            
        Returns:
            True if tool can be safely removed, False otherwise
        """
        # Check if tool is protected
        for pattern in protected_patterns:
            if pattern.lower() in tool_name.lower():
                return False
                
        # Check if tool is managed by organization
        for marker in org_markers:
            if marker.lower() in tool_name.lower():
                return True
                
        # Default to safe removal for known ethPandaOps tools
        # This is a conservative approach - only remove tools we're confident about
        known_org_tools = {
            # Commands (with .md extension)
            'init-project-ai-docs.md', 'prime-context.md', 'init-component-ai-docs.md',
            'parallel-repository-tasks.md', 'create-implementation-plan.md',
            'create-implementation-plan-v2.md', 'create-implementation-plan-v3.md',
            'review-implementation-plan.md', 'create-feedback-loop.md',
            'create-presentation.md', 'prepare-one-shot.md',
            # Code standards (without extension)
            'go', 'python', 'rust', 'tailwindcss',
            # Hooks (without extension)
            'ast-grep', 'eslint', 'gofmt', 'golangci-lint', 'typescript',
            # Scripts
            'init-ai-docs.py', 'all'
        }
        
        return tool_name in known_org_tools
        
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
            
