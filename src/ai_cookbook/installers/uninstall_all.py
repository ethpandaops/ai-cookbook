"""Complete uninstaller for all ai-cookbook components."""

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..installers.base import InteractiveInstaller, InstallationResult
from ..installers.commands import CommandsInstaller
from ..installers.code_standards import CodeStandardsInstaller
from ..installers.hooks import HooksInstaller
from ..installers.agents import AgentsInstaller
from ..installers.scripts import ScriptsInstaller
from ..installers.mcp_servers import MCPServersInstaller
from ..utils.file_operations import file_exists, directory_exists
from ..config.settings import CLAUDE_DIR, ORG_NAME, ORG_DISPLAY_NAME
from ..project_registry import ProjectRegistry


class UninstallAllInstaller(InteractiveInstaller):
    f"""Complete uninstaller for all {ORG_DISPLAY_NAME} AI Cookbook components.
    
    Removes:
    - All code standards and CLAUDE.md entries
    - All commands from ~/.claude/commands/{ORG_NAME}
    - All hooks from ~/.claude/hooks/{ORG_NAME}
    - All agents from ~/.claude/agents/{ORG_NAME}
    - All MCP servers from ~/.claude.json
    - All local project hooks and settings
    - Scripts from PATH
    - Project registry entries
    """
    
    def __init__(self) -> None:
        """Initialize complete uninstaller."""
        super().__init__(
            name="Uninstall Everything",
            description=f"Remove all {ORG_DISPLAY_NAME} AI Cookbook components"
        )
        self.installers = {
            'commands': CommandsInstaller(),
            'code_standards': CodeStandardsInstaller(),
            'hooks': HooksInstaller(),
            'agents': AgentsInstaller(),
            'mcp_servers': MCPServersInstaller(),
            'scripts': ScriptsInstaller()
        }
        self.project_registry = ProjectRegistry()
        
    def check_status(self) -> Dict[str, Any]:
        """Check what is currently installed.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'components_installed': {},
            'local_projects': [],
            'total_items': 0
        }
        
        # Check each component
        for name, installer in self.installers.items():
            installer_status = installer.check_status()
            
            if name == 'hooks':
                global_hooks = installer_status.get('global_hooks', [])
                local_hooks = installer_status.get('local_hooks', [])
                if global_hooks or local_hooks:
                    status['components_installed'][name] = {
                        'global': global_hooks,
                        'local': local_hooks
                    }
                    status['total_items'] += len(global_hooks) + len(local_hooks)
            elif name == 'scripts':
                if installer_status.get('installed', False):
                    status['components_installed'][name] = ['scripts in PATH']
                    status['total_items'] += 1
            elif name == 'agents':
                installed = installer_status.get('installed_agents', [])
                if installed:
                    status['components_installed'][name] = installed
                    status['total_items'] += len(installed)
            elif name == 'mcp_servers':
                installed = list(installer_status.get('installed_servers', {}).keys())
                if installed:
                    status['components_installed'][name] = installed
                    status['total_items'] += len(installed)
            else:
                installed = installer_status.get('installed_items', [])
                if installed:
                    status['components_installed'][name] = installed
                    status['total_items'] += len(installed)
        
        # Check local projects
        projects = list(self.project_registry.projects.keys())
        existing_projects = [p for p in projects if Path(p).exists()]
        if existing_projects:
            status['local_projects'] = existing_projects
            status['total_items'] += len(existing_projects)
        
        return status
        
    def install(self, skip_confirmation: bool = False) -> InstallationResult:
        """Not applicable for uninstaller."""
        return InstallationResult(
            False,
            "This is an uninstaller - use uninstall() instead"
        )
        
    def uninstall(self, skip_confirmation: bool = False) -> InstallationResult:
        f"""Uninstall all {ORG_DISPLAY_NAME} AI Cookbook components.
        
        Args:
            skip_confirmation: Skip confirmation prompt
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            status = self.check_status()
            
            if status['total_items'] == 0:
                return InstallationResult(
                    True,
                    f"No {ORG_DISPLAY_NAME} AI Cookbook components found to uninstall"
                )
            
            self._show_uninstall_preview(status)
            
            if not self._confirm_uninstall(skip_confirmation):
                return InstallationResult(False, "Uninstallation cancelled by user")
            
            print("\n🔧 Uninstalling all components...")
            print("=" * 60)
            
            results = self._initialize_uninstall_results()
            
            # Execute uninstallation steps
            self._uninstall_code_standards(results)
            self._uninstall_commands(results)
            self._uninstall_hooks(results)
            self._uninstall_agents(results)
            self._uninstall_mcp_servers(results)
            self._clean_local_projects(results)
            self._uninstall_scripts(results)
            self._remove_ai_cookbook_binary(results)
            self._cleanup_directories(results)
            
            self._display_uninstall_summary(results)
            
            return self._create_uninstall_result(results)
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall: {str(e)}"
            )
    
    def _show_uninstall_preview(self, status: Dict[str, Any]) -> None:
        """Display what will be removed during uninstallation.
        
        Args:
            status: Status dictionary from check_status()
        """
        print(f"\n🗑️  The following {ORG_DISPLAY_NAME} AI Cookbook components will be removed:")
        print("=" * 60)
        
        for component, items in status['components_installed'].items():
            print(f"\n{component.replace('_', ' ').title()}:")
            if component == 'hooks':
                if items['global']:
                    print("  Global hooks:")
                    for hook in items['global']:
                        print(f"    • {hook}")
                if items['local']:
                    print("  Local hooks:")
                    for hook in items['local']:
                        print(f"    • {hook}")
            else:
                for item in items:
                    print(f"  • {item}")
        
        if status['local_projects']:
            print(f"\nLocal Projects:")
            for project in status['local_projects']:
                print(f"  • {project}")
        
        print("\nThis will also clean up:")
        print("  • ~/.claude/ethpandaops/ directory")
        print("  • ~/.claude/CLAUDE.md ethPandaOps entries")
        print("  • ~/.claude/settings.json hook entries")
        print("  • Local project .claude/settings.local.json files")
        print("  • Project registry (~/.claude/.ai-cookbook-projects.json)")
        print("  • ai-cookbook binary from PATH")
        print("  • Scripts PATH entries from shell profile")
    
    def _confirm_uninstall(self, skip_confirmation: bool) -> bool:
        """Confirm uninstallation with user unless skip_confirmation is True.
        
        Args:
            skip_confirmation: Whether to skip user confirmation
            
        Returns:
            True if uninstallation should proceed, False otherwise
        """
        if skip_confirmation:
            return True
            
        print(f"\n⚠️  This action cannot be undone!")
        response = input("Are you sure you want to uninstall everything? (y/N): ").lower().strip()
        return response == 'y'
    
    def _initialize_uninstall_results(self) -> Dict[str, Any]:
        """Initialize results dictionary for tracking uninstallation progress.
        
        Returns:
            Dictionary with uninstalled, cleaned_up, and errors keys
        """
        return {
            'uninstalled': {},
            'cleaned_up': [],
            'errors': []
        }
    
    def _uninstall_code_standards(self, results: Dict[str, Any]) -> None:
        """Uninstall all code standards.
        
        Args:
            results: Results dictionary to update
        """
        print("\n📝 Removing code standards...")
        cs_installer = self.installers['code_standards']
        cs_status = cs_installer.check_status()
        
        for language in cs_status.get('installed_languages', []):
            print(f"  • Removing {language}...")
            result = cs_installer.uninstall_language(language)
            if result.success:
                if 'code_standards' not in results['uninstalled']:
                    results['uninstalled']['code_standards'] = []
                results['uninstalled']['code_standards'].append(language)
            else:
                results['errors'].append(f"Failed to remove {language}: {result.message}")
        
        # This should have cleaned up CLAUDE.md automatically
        print("  ✓ CLAUDE.md entries cleaned")
    
    def _uninstall_commands(self, results: Dict[str, Any]) -> None:
        """Uninstall all commands.
        
        Args:
            results: Results dictionary to update
        """
        print("\n💻 Removing commands...")
        cmd_installer = self.installers['commands']
        cmd_status = cmd_installer.check_status()
        
        for command in cmd_status.get('installed_commands', []):
            print(f"  • Removing {command}...")
            result = cmd_installer.uninstall_command(command)
            if result.success:
                if 'commands' not in results['uninstalled']:
                    results['uninstalled']['commands'] = []
                results['uninstalled']['commands'].append(command)
            else:
                results['errors'].append(f"Failed to remove {command}: {result.message}")
    
    def _uninstall_hooks(self, results: Dict[str, Any]) -> None:
        """Uninstall all hooks (global and local).
        
        Args:
            results: Results dictionary to update
        """
        print("\n🪝 Removing hooks...")
        hooks_installer = self.installers['hooks']
        hooks_status = hooks_installer.check_status()
        
        # Remove global hooks
        for hook in hooks_status.get('global_hooks', []):
            print(f"  • Removing {hook} (global)...")
            hooks_installer.set_mode('global')
            result = hooks_installer.uninstall_hook(hook)
            if result.success:
                if 'hooks' not in results['uninstalled']:
                    results['uninstalled']['hooks'] = []
                results['uninstalled']['hooks'].append(f"{hook} (global)")
            else:
                results['errors'].append(f"Failed to remove {hook} (global): {result.message}")
        
        # Remove local hooks
        for hook in hooks_status.get('local_hooks', []):
            print(f"  • Removing {hook} (local)...")
            hooks_installer.set_mode('local')
            result = hooks_installer.uninstall_hook(hook)
            if result.success:
                if 'hooks' not in results['uninstalled']:
                    results['uninstalled']['hooks'] = []
                results['uninstalled']['hooks'].append(f"{hook} (local)")
            else:
                results['errors'].append(f"Failed to remove {hook} (local): {result.message}")
    
    def _uninstall_agents(self, results: Dict[str, Any]) -> None:
        """Uninstall all agents.
        
        Args:
            results: Results dictionary to update
        """
        print("\n🤖 Removing agents...")
        agents_installer = self.installers['agents']
        agents_status = agents_installer.check_status()
        
        for agent in agents_status.get('installed_agents', []):
            print(f"  • Removing {agent}...")
            result = agents_installer.uninstall_agent(agent)
            if result.success:
                if 'agents' not in results['uninstalled']:
                    results['uninstalled']['agents'] = []
                results['uninstalled']['agents'].append(agent)
            else:
                results['errors'].append(f"Failed to remove {agent}: {result.message}")
    
    def _uninstall_mcp_servers(self, results: Dict[str, Any]) -> None:
        """Uninstall all MCP servers.
        
        Args:
            results: Results dictionary to update
        """
        print("\n🔌 Removing MCP servers...")
        mcp_installer = self.installers['mcp_servers']
        result = mcp_installer.uninstall()
        if result.success:
            if result.details and 'removed' in result.details:
                if 'mcp_servers' not in results['uninstalled']:
                    results['uninstalled']['mcp_servers'] = []
                results['uninstalled']['mcp_servers'].extend(result.details['removed'])
        else:
            results['errors'].append(f"Failed to remove MCP servers: {result.message}")
    
    def _clean_local_projects(self, results: Dict[str, Any]) -> None:
        """Clean up local project hooks and registry entries.
        
        Args:
            results: Results dictionary to update
        """
        print("\n📁 Cleaning up local projects...")
        projects = list(self.project_registry.projects.keys())
        
        for project_path in projects:
            print(f"  • Cleaning {project_path}...")
            try:
                # Remove hooks from project's local settings
                self._clean_project_settings(project_path, results)
                
                # Remove from registry
                self.project_registry.unregister_project(Path(project_path))
                results['cleaned_up'].append(f"Project: {project_path}")
                
            except Exception as e:
                results['errors'].append(f"Error cleaning project {project_path}: {str(e)}")
    
    def _clean_project_settings(self, project_path: str, results: Dict[str, Any]) -> None:
        """Clean hooks from a project's local settings file.
        
        Args:
            project_path: Path to the project
            results: Results dictionary to update for errors
        """
        project_settings_file = Path(project_path) / '.claude' / 'settings.local.json'
        if project_settings_file.exists():
            try:
                import json
                with open(project_settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Remove hooks section
                if 'hooks' in settings:
                    del settings['hooks']
                    with open(project_settings_file, 'w') as f:
                        json.dump(settings, f, indent=2)
                        
            except Exception as e:
                results['errors'].append(f"Failed to clean hooks from {project_path}: {str(e)}")
    
    def _uninstall_scripts(self, results: Dict[str, Any]) -> None:
        """Uninstall scripts from PATH.
        
        Args:
            results: Results dictionary to update
        """
        scripts_installer = self.installers['scripts']
        scripts_status = scripts_installer.check_status()
        
        if scripts_status.get('installed', False):
            print("\n📜 Removing scripts from PATH...")
            result = scripts_installer.uninstall(auto_remove=True)
            if result.success:
                print(f"  ✓ {result.message}")
                if result.details and 'note' in result.details:
                    print(f"  ℹ️  {result.details['note']}")
                results['uninstalled']['scripts'] = ['removed from PATH']
            else:
                results['errors'].append(f"Failed to remove scripts: {result.message}")
    
    def _remove_ai_cookbook_binary(self, results: Dict[str, Any]) -> None:
        """Remove the ai-cookbook binary from system.
        
        Args:
            results: Results dictionary to update
        """
        print("\n🗑️  Removing ai-cookbook binary...")
        try:
            # Find ai-cookbook binary location
            result = subprocess.run(['which', 'ai-cookbook'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                ai_cookbook_path = Path(result.stdout.strip())
                if ai_cookbook_path.exists():
                    ai_cookbook_path.unlink()
                    print(f"  ✓ Removed {ai_cookbook_path}")
                    results['cleaned_up'].append(f"Binary: {ai_cookbook_path}")
                else:
                    print("  ℹ️  ai-cookbook binary not found")
            else:
                print("  ℹ️  ai-cookbook binary not found in PATH")
        except Exception as e:
            results['errors'].append(f"Failed to remove ai-cookbook binary: {str(e)}")
            print(f"  ⚠️  Failed to remove binary: {str(e)}")
    
    def _cleanup_directories(self, results: Dict[str, Any]) -> None:
        """Clean up all ethPandaOps directories.
        
        Args:
            results: Results dictionary to update
        """
        print("\n🧹 Cleaning up directories...")
        
        directories_to_remove = [
            (CLAUDE_DIR / ORG_NAME, f"Directory: ~/.claude/{ORG_NAME}"),
            (CLAUDE_DIR / 'commands' / ORG_NAME, f"Directory: ~/.claude/commands/{ORG_NAME}"),
            (CLAUDE_DIR / 'hooks' / ORG_NAME, f"Directory: ~/.claude/hooks/{ORG_NAME}")
        ]
        
        for directory, description in directories_to_remove:
            if directory.exists():
                try:
                    shutil.rmtree(directory)
                    results['cleaned_up'].append(description)
                    print(f"  ✓ Removed {directory}")
                except Exception as e:
                    results['errors'].append(f"Failed to remove {directory}: {str(e)}")
        
        # Clean up project registry file
        if self.project_registry.REGISTRY_FILE.exists():
            try:
                self.project_registry.REGISTRY_FILE.unlink()
                results['cleaned_up'].append("Project registry file")
                print(f"  ✓ Removed project registry")
            except Exception as e:
                results['errors'].append(f"Failed to remove project registry: {str(e)}")
    
    def _display_uninstall_summary(self, results: Dict[str, Any]) -> None:
        """Display uninstallation summary.
        
        Args:
            results: Results dictionary with uninstallation details
        """
        total_uninstalled = sum(len(items) for items in results['uninstalled'].values())
        total_cleaned = len(results['cleaned_up'])
        total_errors = len(results['errors'])
        
        print("\n" + "=" * 60)
        print("📊 Uninstallation Summary:")
        print(f"  • {total_uninstalled} components uninstalled")
        print(f"  • {total_cleaned} items cleaned up")
        if total_errors > 0:
            print(f"  • {total_errors} errors encountered")
        
        if results['errors']:
            print("\n⚠️  Errors:")
            for error in results['errors']:
                print(f"  • {error}")
    
    def _create_uninstall_result(self, results: Dict[str, Any]) -> InstallationResult:
        """Create final uninstallation result based on results.
        
        Args:
            results: Results dictionary with errors and uninstallation details
            
        Returns:
            InstallationResult with appropriate success status and message
        """
        total_errors = len(results.get('errors', []))
        
        if total_errors > 0:
            return InstallationResult(
                False,
                f"Uninstallation completed with {total_errors} errors",
                results
            )
        else:
            print("\n✅ All ethPandaOps AI Cookbook components have been removed!")
            return InstallationResult(
                True,
                "Successfully uninstalled all components",
                results
            )
            
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about what will be uninstalled.
        
        Returns:
            Dictionary with detailed uninstaller information
        """
        status = self.check_status()
        
        return {
            'name': self.name,
            'description': self.description,
            'components_installed': status['components_installed'],
            'local_projects': status['local_projects'],
            'total_items': status['total_items'],
            'directories_to_remove': [
                '~/.claude/ethpandaops/',
                '~/.claude/commands/ethpandaops/',
                '~/.claude/hooks/ethpandaops/'
            ],
            'files_to_clean': [
                '~/.claude/CLAUDE.md (ethPandaOps entries)',
                '~/.claude/settings.json (hook entries)',
                '~/.claude/.ai-cookbook-projects.json',
                'Local project .claude/settings.local.json files'
            ]
        }
        
    def build_interactive_options(self) -> None:
        """Build interactive options for uninstaller."""
        self.clear_interactive_options()
        
        status = self.check_status()
        
        if status['total_items'] > 0:
            self.add_interactive_option(
                "🗑️  Uninstall Everything",
                f"Remove all {status['total_items']} ethPandaOps components",
                lambda: self.uninstall(skip_confirmation=True)
            )
        else:
            self.add_interactive_option(
                "✓ Nothing to Uninstall",
                "No ethPandaOps components are installed",
                lambda: None
            )