"""MCP Servers installer for PandaOps Cookbook."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..installers.base import InteractiveInstaller, InstallationResult
from ..utils.file_operations import (
    ensure_directory, copy_files, file_exists, directory_exists,
    list_files, read_json_file, write_json_file
)
from ..utils.system import run_command
from ..config.settings import CLAUDE_DIR, ORG_NAME

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class MCPServersInstaller(InteractiveInstaller):
    """Installer for MCP (Model Context Protocol) servers.
    
    Manages installation and configuration of MCP servers for Claude Code.
    Discovers servers from claude-code/mcp-servers/ directories.
    """
    
    def __init__(self) -> None:
        """Initialize MCP servers installer."""
        super().__init__(
            name="MCP Servers",
            description="Install and configure MCP servers for Claude Code"
        )
        self.mcp_servers_source = PROJECT_ROOT / "claude-code" / "mcp-servers"
        self.tools_dir = PROJECT_ROOT / "tools" / "mcp-servers"
        self.claude_config_path = Path.home() / ".claude.json"
        self.available_servers = self._discover_available_servers()
        
    def _discover_available_servers(self) -> Dict[str, Any]:
        """Discover available MCP servers from claude-code/mcp-servers.
        
        Returns:
            Dictionary of available servers with their configuration
        """
        servers = {}
        
        if not self.mcp_servers_source.exists():
            return servers
            
        for server_dir in self.mcp_servers_source.iterdir():
            if server_dir.is_dir() and (server_dir / "config.json").exists():
                try:
                    config = read_json_file(server_dir / "config.json")
                    implementation_path = PROJECT_ROOT / config.get('implementation', '')
                    
                    servers[server_dir.name] = {
                        'name': server_dir.name,
                        'config_path': server_dir / "config.json",
                        'config': config,
                        'description': config.get('description', 'No description'),
                        'implementation': implementation_path,
                        'entry_point': config.get('entry_point', 'index.js')
                    }
                except Exception as e:
                    print(f"Warning: Could not load config for {server_dir.name}: {e}")
                    
        return servers
        
    def check_status(self) -> Dict[str, Any]:
        """Check installation status of MCP servers.
        
        Returns:
            Dictionary with status information
        """
        installed_servers = {}
        
        # Check Claude Code config
        if self.claude_config_path.exists():
            try:
                config = read_json_file(self.claude_config_path)
                mcp_servers = config.get('mcpServers', {})
                
                # Check which of our servers are installed
                for server_name in self.available_servers:
                    if server_name in mcp_servers:
                        installed_servers[server_name] = {
                            'installed': True,
                            'config': mcp_servers[server_name]
                        }
                        
            except Exception as e:
                pass
                
        return {
            'installed': bool(installed_servers),
            'installed_servers': installed_servers,
            'available_servers': list(self.available_servers.keys()),
            'claude_config_exists': self.claude_config_path.exists()
        }
        
    def install(self) -> InstallationResult:
        """Install MCP servers (interactive mode message).
        
        Returns:
            InstallationResult with message directing to interactive mode
        """
        return InstallationResult(
            False,
            "MCP server installation requires interactive mode. Use the interactive menu to install specific servers.",
            {'hint': 'Select this installer from the main menu for interactive options'}
        )
        
    def uninstall(self) -> InstallationResult:
        """Uninstall all MCP servers from Claude Code.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            if not self.claude_config_path.exists():
                return InstallationResult(
                    True,
                    "No Claude Code configuration found",
                    {}
                )
                
            config = read_json_file(self.claude_config_path)
            mcp_servers = config.get('mcpServers', {})
            
            removed_servers = []
            for server_name in list(self.available_servers.keys()):
                if server_name in mcp_servers:
                    del mcp_servers[server_name]
                    removed_servers.append(server_name)
                    
            if removed_servers:
                config['mcpServers'] = mcp_servers
                write_json_file(self.claude_config_path, config)
                
                return InstallationResult(
                    True,
                    f"Successfully uninstalled {len(removed_servers)} MCP server(s)",
                    {'removed': removed_servers}
                )
            else:
                return InstallationResult(
                    True,
                    "No MCP servers were installed",
                    {}
                )
                
        except Exception as e:
            return InstallationResult(
                False,
                f"Uninstallation failed: {str(e)}"
            )
            
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about MCP servers.
        
        Returns:
            Dictionary with detailed installer information
        """
        status = self.check_status()
        
        return {
            'name': self.name,
            'description': self.description,
            'available_servers': self.available_servers,
            'installed_servers': status['installed_servers'],
            'claude_config_path': str(self.claude_config_path),
            'claude_config_exists': status['claude_config_exists']
        }
        
    def install_server(self, server_name: str, config: Dict[str, Any] = None) -> InstallationResult:
        """Install a specific MCP server.
        
        Args:
            server_name: Name of the server to install
            config: Optional configuration for the server
            
        Returns:
            InstallationResult indicating success/failure
        """
        if server_name not in self.available_servers:
            return InstallationResult(
                False,
                f"Server '{server_name}' not found in available servers"
            )
            
        try:
            server_info = self.available_servers[server_name]
            server_config_data = server_info['config']
            implementation_path = server_info['implementation']
            entry_point = server_info['entry_point']
            
            # Ensure Claude Code config directory exists
            ensure_directory(self.claude_config_path.parent)
            
            # Backup config before modification
            if self.claude_config_path.exists():
                backup_path = self.claude_config_path.with_suffix('.backup')
                shutil.copy2(self.claude_config_path, backup_path)
                claude_config = read_json_file(self.claude_config_path)
            else:
                claude_config = {'mcpServers': {}}
                
            if 'mcpServers' not in claude_config:
                claude_config['mcpServers'] = {}
                
            # Handle configuration based on config.json prompts
            if server_config_data.get('config_prompts'):
                result = self._configure_server_with_prompts(
                    server_name, server_config_data, implementation_path, entry_point, config
                )
                if not result.success:
                    return result
                claude_config['mcpServers'][server_name] = result.details['config']
            else:
                # Simple server without configuration
                server_config = {
                    'command': 'node',
                    'args': [str(implementation_path / entry_point)]
                }
                claude_config['mcpServers'][server_name] = server_config
                
            # Save updated config
            write_json_file(self.claude_config_path, claude_config)
            
            return InstallationResult(
                True,
                f"Successfully installed {server_name} MCP server",
                {'server': server_name, 'config': claude_config['mcpServers'][server_name]}
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install {server_name}: {str(e)}"
            )
            
    def _configure_server_with_prompts(self, server_name: str, server_config_data: Dict[str, Any], 
                                      implementation_path: Path, entry_point: str, 
                                      config: Dict[str, Any] = None) -> InstallationResult:
        """Configure an MCP server based on config.json prompts.
        
        Args:
            server_name: Name of the server
            server_config_data: Configuration data from config.json
            implementation_path: Path to the server implementation
            entry_point: Entry point file for the server
            config: Optional pre-provided configuration
            
        Returns:
            InstallationResult with the server configuration
        """
        try:
            config_prompts = server_config_data.get('config_prompts', {})
            env_vars = {}
            
            if not config:
                # Interactive configuration
                print(f"\n🔧 Configuring {server_name} MCP server")
                print("-" * 50)
                
                for key, prompt_config in config_prompts.items():
                    prompt_text = prompt_config.get('prompt', key)
                    default_value = prompt_config.get('default', '')
                    is_required = prompt_config.get('required', False)
                    is_secret = prompt_config.get('secret', False)
                    help_url = prompt_config.get('help_url', '')
                    description = prompt_config.get('description', '')
                    
                    if description:
                        print(f"\n{description}")
                    if help_url:
                        print(f"📝 Help: {help_url}")
                    
                    if default_value:
                        value = input(f"{prompt_text} [{default_value}]: ").strip()
                        if not value:
                            value = default_value
                    else:
                        value = input(f"{prompt_text}: ").strip()
                    
                    if is_required and not value:
                        return InstallationResult(
                            False,
                            f"{prompt_text} is required"
                        )
                    
                    # Basic validation for tokens
                    if is_secret and value:
                        if len(value) < 10:
                            return InstallationResult(
                                False,
                                f"Invalid {prompt_text}. Must be at least 10 characters long."
                            )
                        if key == 'service_token' and not (value.startswith('glsa_') or value.startswith('glc_')):
                            print("⚠️  Warning: Token doesn't start with expected prefix (glsa_ or glc_)")
                            confirm = input("Continue anyway? [y/N]: ").strip().lower()
                            if confirm != 'y':
                                return InstallationResult(
                                    False,
                                    "Token validation cancelled by user"
                                )
                    
                    env_vars[key] = value
                    
            else:
                # Use provided config
                for key in config_prompts.keys():
                    env_vars[key] = config.get(key, '')
            
            # Load datasource descriptions if available (for ethpandaops servers)
            if 'ethpandaops' in server_name:
                # Look for datasource descriptions in the server's config directory
                server_config_dir = self.mcp_servers_source / server_name
                descriptions_file = server_config_dir / "datasource-descriptions.json"
                if descriptions_file.exists():
                    try:
                        with open(descriptions_file, 'r') as f:
                            descriptions = json.load(f)
                            env_vars['datasource_descriptions'] = json.dumps(descriptions)
                            print(f"📚 Loaded {len(descriptions)} datasource descriptions")
                    except Exception as e:
                        print(f"⚠️  Could not load datasource descriptions: {e}")
                    
            # Handle binary runtime servers
            if server_config_data.get('runtime') == 'binary':
                build_cmd = server_config_data.get('build_command')
                if build_cmd:
                    print(f"\n🔨 Building {server_name}...")
                    result = run_command(build_cmd.split(), cwd=str(implementation_path))
                    if result.returncode != 0:
                        return InstallationResult(
                            False,
                            f"Failed to build {server_name}: {result.stderr}"
                        )
            else:
                # First install npm dependencies if needed
                if not (implementation_path / "node_modules").exists():
                    print(f"\n📦 Installing dependencies for {implementation_path.name}...")
                    result = run_command(['npm', 'install'], cwd=str(implementation_path))
                    if result.returncode != 0:
                        return InstallationResult(
                            False,
                            f"Failed to install npm dependencies: {result.stderr}"
                        )
                    
            # Test the configuration if it's a Grafana-based server
            if 'grafana_url' in env_vars and 'service_token' in env_vars:
                print("\n🔍 Testing connection to Grafana...")
                test_env = os.environ.copy()
                test_env['GRAFANA_URL'] = env_vars.get('grafana_url', '')
                test_env['GRAFANA_SERVICE_TOKEN'] = env_vars.get('service_token', '')
                if 'datasource_descriptions' in env_vars:
                    test_env['DATASOURCE_DESCRIPTIONS'] = env_vars['datasource_descriptions']
                
                # Create a test script to run the health check
                test_script = """
const http = require('axios').create({
  baseURL: process.env.GRAFANA_URL,
  headers: { Authorization: `Bearer ${process.env.GRAFANA_SERVICE_TOKEN}` },
  timeout: 5000
});
http.get('/api/user').then(r => {
  console.log(JSON.stringify({success: true, user: r.data.login || r.data.name}));
}).catch(e => {
  console.log(JSON.stringify({success: false, error: e.message}));
});
"""
                # Use subprocess directly for env support
                test_result = subprocess.run(
                    ['node', '-e', test_script],
                    cwd=str(implementation_path),
                    env=test_env,
                    capture_output=True,
                    text=True
                )
                
                if test_result.returncode == 0:
                    try:
                        test_data = json.loads(test_result.stdout)
                        if test_data.get('success'):
                            print(f"✅ Successfully authenticated as: {test_data.get('user', 'Unknown')}")
                        else:
                            print(f"⚠️  Authentication may have issues: {test_data.get('error', 'Unknown error')}")
                    except:
                        print("⚠️  Could not verify authentication, but continuing...")
                else:
                    print("⚠️  Could not test authentication, but continuing...")
                
            # Create the server configuration for Claude Code
            if server_config_data.get('runtime') == 'binary':
                # Use args format for consistency with Claude's expectations
                server_config = {
                    'command': str(implementation_path / entry_point),
                    'args': [],
                    'env': {}
                }
            else:
                server_config = {
                    'command': 'node',
                    'args': [str(implementation_path / entry_point)],
                    'env': {}
                }
            
            # Map config values to environment variables
            for key, value in env_vars.items():
                if key == 'grafana_url':
                    server_config['env']['GRAFANA_URL'] = value
                elif key == 'service_token':
                    server_config['env']['GRAFANA_SERVICE_TOKEN'] = value
                elif key == 'datasource_descriptions':
                    server_config['env']['DATASOURCE_DESCRIPTIONS'] = value
                else:
                    # Generic env var mapping
                    server_config['env'][key.upper()] = value
                
            return InstallationResult(
                True,
                f"{server_name} server configured",
                {'config': server_config}
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to configure {server_name} server: {str(e)}"
            )
            
    def uninstall_server(self, server_name: str) -> InstallationResult:
        """Uninstall a specific MCP server.
        
        Args:
            server_name: Name of the server to uninstall
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            if not self.claude_config_path.exists():
                return InstallationResult(
                    False,
                    "Claude Code configuration not found"
                )
                
            config = read_json_file(self.claude_config_path)
            mcp_servers = config.get('mcpServers', {})
            
            if server_name not in mcp_servers:
                return InstallationResult(
                    False,
                    f"Server '{server_name}' is not installed"
                )
                
            del mcp_servers[server_name]
            config['mcpServers'] = mcp_servers
            write_json_file(self.claude_config_path, config)
            
            return InstallationResult(
                True,
                f"Successfully uninstalled {server_name} MCP server"
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall {server_name}: {str(e)}"
            )
            
    def build_interactive_options(self) -> None:
        """Build interactive options based on available servers."""
        self.clear_interactive_options()
        
        status = self.check_status()
        
        # Add install/update options for each available server
        for server_name, server_info in self.available_servers.items():
            is_installed = server_name in status['installed_servers']
            
            if is_installed:
                # Update/reinstall option
                self.add_interactive_option(
                    f"Update {server_name}",
                    f"Reconfigure the {server_name} MCP server",
                    lambda sn=server_name: self._interactive_install_server(sn),
                    lambda sn=server_name: "INSTALLED"
                )
                
                # Uninstall option
                self.add_interactive_option(
                    f"Uninstall {server_name}",
                    f"Remove the {server_name} MCP server",
                    lambda sn=server_name: self.uninstall_server(sn),
                    lambda sn=server_name: "INSTALLED"
                )
            else:
                # Install option
                self.add_interactive_option(
                    f"Install {server_name}",
                    server_info['description'],
                    lambda sn=server_name: self._interactive_install_server(sn),
                    lambda sn=server_name: "NOT INSTALLED"
                )
                
    def _interactive_install_server(self, server_name: str) -> InstallationResult:
        """Interactive installation of a server.
        
        Args:
            server_name: Name of the server to install
            
        Returns:
            InstallationResult
        """
        # For ethpandaops-data, we'll use interactive prompts
        # For other servers, we might need different configuration
        return self.install_server(server_name)