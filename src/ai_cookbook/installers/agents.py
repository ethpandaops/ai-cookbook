"""Claude agents installer for PandaOps Cookbook."""

from pathlib import Path
from typing import Dict, Any, List
import shutil

from ..installers.base import BaseInstaller, InstallationResult
from ..utils.file_operations import (
    ensure_directory, copy_files, directory_exists, 
    list_files, remove_directory
)
from ..utils.system import run_command
from ..config.settings import CLAUDE_DIR

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Define paths for agents
CLAUDE_AGENTS_DIR = CLAUDE_DIR / "agents" / "ethpandaops"


class AgentsInstaller(BaseInstaller):
    """Installer for Claude agents integration."""
    
    def __init__(self) -> None:
        """Initialize agents installer."""
        super().__init__(
            name="Claude Agents",
            description="Install Claude Code agents for specialized AI assistance"
        )
        self.agents_source = PROJECT_ROOT / "claude-code" / "agents"
        
        # Initialize update detector
        self.initialize_update_detector(self.agents_source, CLAUDE_AGENTS_DIR)
        
    def check_status(self) -> Dict[str, Any]:
        """Check installation status of Claude agents.
        
        Returns:
            Dictionary with status information:
            - installed: Whether any agents are installed
            - installed_agents: List of installed agent names
            - available_agents: List of available agents from source
        """
        agents_installed = CLAUDE_AGENTS_DIR.exists() and \
                          len(list(CLAUDE_AGENTS_DIR.glob("*/agent.md"))) > 0
        
        installed_agents = []
        if agents_installed:
            # List agent directories that contain agent.md
            for agent_dir in CLAUDE_AGENTS_DIR.iterdir():
                if agent_dir.is_dir() and (agent_dir / "agent.md").exists():
                    installed_agents.append(agent_dir.name)
        
        # Get available agents from source
        available_agents = []
        if directory_exists(self.agents_source):
            for agent_dir in self.agents_source.iterdir():
                if agent_dir.is_dir() and (agent_dir / "agent.md").exists():
                    available_agents.append(agent_dir.name)
        
        return {
            'installed': agents_installed,
            'installed_agents': installed_agents,
            'installed_items': installed_agents,  # For compatibility with recommended installer
            'available_agents': available_agents,
            'agents_dir': str(CLAUDE_AGENTS_DIR)
        }
        
    def install(self) -> InstallationResult:
        """Install all available agents.
        
        Returns:
            InstallationResult indicating success/failure
        """
        status = self.check_status()
        available_agents = status.get('available_agents', [])
        installed_agents = status.get('installed_agents', [])
        
        results = []
        for agent in available_agents:
            if agent not in installed_agents:
                result = self.install_agent(agent)
                results.append((agent, result))
        
        successful = [agent for agent, result in results if result.success]
        failed = [agent for agent, result in results if not result.success]
        
        if not results:
            return InstallationResult(
                True,
                "All agents are already installed"
            )
        
        if failed:
            return InstallationResult(
                False,
                f"Installed {len(successful)} agents, {len(failed)} failed",
                {'successful': successful, 'failed': failed}
            )
        
        return InstallationResult(
            True,
            f"Successfully installed {len(successful)} agents",
            {'installed': successful}
        )
        
    def install_agent(self, agent_name: str) -> InstallationResult:
        """Install a specific Claude agent.
        
        Args:
            agent_name: Name of the agent directory (e.g., 'hello')
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            # Check if agent exists in source
            agent_source_dir = self.agents_source / agent_name
            agent_file = agent_source_dir / "agent.md"
            
            if not agent_source_dir.exists() or not agent_file.exists():
                return InstallationResult(
                    False,
                    f"Agent '{agent_name}' not found in source directory"
                )
            
            # Check dependencies if deps.sh exists
            deps_result = self._check_agent_dependencies(agent_name)
            if not deps_result['success']:
                return InstallationResult(
                    False,
                    f"Dependencies not met for agent '{agent_name}'\n{deps_result.get('output', '')}",
                    deps_result
                )
            
            # Create required directories
            self.create_required_directories()
            ensure_directory(CLAUDE_AGENTS_DIR)
            agent_target_dir = CLAUDE_AGENTS_DIR / agent_name
            ensure_directory(agent_target_dir)
            
            # Back up existing agent if present
            backup_created = False
            agent_target_file = agent_target_dir / "agent.md"
            if agent_target_file.exists():
                backup_path = self.backup_manager.create_backup(
                    agent_target_file,
                    f"agent_{agent_name}"
                )
                if backup_path:
                    backup_created = True
            
            # Copy agent file
            shutil.copy2(agent_file, agent_target_file)
            
            # Update metadata
            if self.update_detector:
                self.update_detector.update_metadata(agent_name, agent_file)
            
            details = {
                'agent': agent_name,
                'target_path': str(agent_target_file)
            }
            
            if backup_created:
                details['backup_created'] = str(backup_path)
            
            return InstallationResult(
                True,
                f"Successfully installed agent: {agent_name}",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install agent {agent_name}: {str(e)}"
            )
            
    def uninstall_agent(self, agent_name: str) -> InstallationResult:
        """Uninstall a specific Claude agent.
        
        Args:
            agent_name: Name of the agent directory (e.g., 'hello')
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            agent_target_dir = CLAUDE_AGENTS_DIR / agent_name
            
            if not agent_target_dir.exists():
                return InstallationResult(
                    True,
                    f"Agent '{agent_name}' is not installed"
                )
            
            # Remove agent directory
            shutil.rmtree(agent_target_dir)
            
            # Remove metadata
            if self.update_detector:
                self.update_detector.remove_metadata(agent_name)
            
            details = {
                'agent': agent_name
            }
            
            return InstallationResult(
                True,
                f"Successfully uninstalled agent: {agent_name}",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall agent {agent_name}: {str(e)}"
            )
            
    def uninstall(self) -> InstallationResult:
        """Uninstall all Claude agents.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            if not directory_exists(CLAUDE_AGENTS_DIR):
                return InstallationResult(
                    True,
                    "No Claude agents were installed"
                )
            
            # Get list of installed agents
            status = self.check_status()
            installed_agents = status.get('installed_agents', [])
            
            if not installed_agents:
                return InstallationResult(
                    True,
                    "No Claude agents were installed"
                )
            
            # Remove agents directory
            remove_directory(CLAUDE_AGENTS_DIR)
            
            details = {
                'removed': installed_agents
            }
            
            return InstallationResult(
                True,
                f"Successfully uninstalled {len(installed_agents)} agents",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Uninstallation failed: {str(e)}"
            )
            
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about Claude agents.
        
        Returns:
            Dictionary with detailed installer information
        """
        status = self.check_status()
        
        # Get details about each available agent
        available_agents_details = {}
        if self.agents_source.exists():
            for agent_dir in self.agents_source.iterdir():
                if agent_dir.is_dir():
                    agent_file = agent_dir / "agent.md"
                    if agent_file.exists():
                        # Read agent metadata from frontmatter
                        try:
                            with open(agent_file, 'r') as f:
                                content = f.read()
                                if content.startswith('---'):
                                    # Extract frontmatter
                                    end_idx = content.find('---', 3)
                                    if end_idx > 0:
                                        frontmatter = content[3:end_idx].strip()
                                        # Simple parsing of key fields
                                        agent_info = {'name': agent_dir.name}
                                        for line in frontmatter.split('\n'):
                                            if ':' in line:
                                                key, value = line.split(':', 1)
                                                agent_info[key.strip()] = value.strip()
                                        available_agents_details[agent_dir.name] = agent_info
                        except Exception:
                            available_agents_details[agent_dir.name] = {'name': agent_dir.name}
        
        return {
            'name': self.name,
            'description': self.description,
            'installed': status['installed'],
            'status': status,
            'paths': {
                'agents_source': str(self.agents_source),
                'agents_target': str(CLAUDE_AGENTS_DIR)
            },
            'available_agents': available_agents_details
        }
        
    def list_available_agents(self) -> List[str]:
        """List all available Claude agents.
        
        Returns:
            List of available agent names
        """
        if not self.agents_source.exists():
            return []
        
        agents = []
        for agent_dir in self.agents_source.iterdir():
            if agent_dir.is_dir() and (agent_dir / "agent.md").exists():
                agents.append(agent_dir.name)
        
        return agents
        
    def validate_prerequisites(self) -> InstallationResult:
        """Validate prerequisites for Claude agents installation.
        
        Returns:
            InstallationResult indicating if prerequisites are met
        """
        # Check if source directory exists
        if not self.agents_source.exists():
            return InstallationResult(
                False,
                f"Agents source directory not found: {self.agents_source}"
            )
        
        # Check if we have any agents to install
        agents = self.list_available_agents()
        if not agents:
            return InstallationResult(
                False,
                "No agent directories found in source directory"
            )
        
        return InstallationResult(True, "Prerequisites met")
        
    def create_required_directories(self) -> None:
        """Create required directories for Claude agents."""
        super().create_required_directories()
        ensure_directory(CLAUDE_DIR)
        ensure_directory(CLAUDE_DIR / "agents")
        ensure_directory(CLAUDE_AGENTS_DIR)
        
    def _check_agent_dependencies(self, agent_name: str) -> Dict[str, Any]:
        """Check if agent dependencies are met.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary with success status and details
        """
        deps_script = self.agents_source / agent_name / "deps.sh"
        if deps_script.exists():
            try:
                result = run_command(["bash", str(deps_script)], check=False)
                return {
                    'success': result.returncode == 0,
                    'output': (result.stdout or '') + (result.stderr or ''),
                    'return_code': result.returncode
                }
            except Exception as e:
                return {
                    'success': False,
                    'output': f'Error running dependencies check: {str(e)}',
                    'return_code': -1
                }
        return {'success': True, 'output': 'No dependencies to check'}