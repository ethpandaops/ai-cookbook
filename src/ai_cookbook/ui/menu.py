"""Interactive menu system for PandaOps Cookbook."""

from typing import List, Dict, Callable, Optional, Any
from .terminal import TerminalController


class MenuOption:
    """Single menu option with status and action."""
    
    def __init__(self, name: str, description: str, action: Callable, 
                 status_checker: Callable[[], str] = None):
        """Initialize a menu option.
        
        Args:
            name: Display name for the option
            description: Detailed description of what this option does
            action: Function to call when option is selected
            status_checker: Optional function that returns current status string
        """
        self.name = name
        self.description = description
        self.action = action
        self.status_checker = status_checker
        
    def get_status(self) -> str:
        """Get current status of this option.
        
        Returns:
            Status string from status_checker, or empty string if none
        """
        if self.status_checker:
            try:
                return self.status_checker()
            except Exception:
                return "ERROR"
        return ""
        
    def execute(self) -> Any:
        """Execute the option's action.
        
        Returns:
            Result from the action function
        """
        return self.action()


class InteractiveMenu:
    """Interactive menu with keyboard navigation."""
    
    def __init__(self, title: str, options: List[MenuOption], 
                 terminal: TerminalController):
        """Initialize interactive menu.
        
        Args:
            title: Menu title to display
            options: List of menu options
            terminal: Terminal controller for UI operations
        """
        self.title = title
        self.options = options
        self.terminal = terminal
        self.selected_index = 0
        self.show_details = False
        self.running = False
        
    def render(self) -> None:
        """Render the menu to the terminal."""
        self.terminal.clear_screen()
        
        # Get terminal dimensions
        rows, cols = self.terminal.get_terminal_size()
        
        # Render title
        self.terminal.move_cursor(1, 1)
        title_line = f"═══ {self.title} ═══"
        padding = (cols - len(title_line)) // 2
        self.terminal.write(" " * padding + title_line)
        
        # Render options
        start_row = 3
        for i, option in enumerate(self.options):
            row = start_row + i * 2  # Add spacing between options
            self.terminal.move_cursor(row, 3)
            
            # Selection indicator
            if i == self.selected_index:
                self.terminal.write("▶ ")
            else:
                self.terminal.write("  ")
                
            # Option name
            self.terminal.write(option.name)
            
            # Status (if available)
            status = option.get_status()
            if status:
                # Right-align status
                status_with_brackets = f"[{status}]"
                status_col = cols - len(status_with_brackets) - 5
                self.terminal.move_cursor(row, status_col)
                self.terminal.write(status_with_brackets)
                
            # Show description if details mode is on
            if self.show_details and i == self.selected_index:
                desc_row = row + 1
                self.terminal.move_cursor(desc_row, 5)
                # Truncate description if too long
                max_desc_len = cols - 10
                desc = option.description
                if len(desc) > max_desc_len:
                    desc = desc[:max_desc_len-3] + "..."
                self.terminal.write(f"└─ {desc}")
        
        # Render help text at bottom
        help_row = rows - 2
        self.terminal.move_cursor(help_row, 3)
        help_text = "↑↓: Navigate | Enter: Select | Tab: Toggle details | q: Quit"
        if len(help_text) < cols - 6:
            self.terminal.write(help_text)
        
    def handle_input(self) -> Optional[str]:
        """Handle keyboard input.
        
        Returns:
            Action to take ('select', 'quit') or None to continue
        """
        key = self.terminal.get_key()
        
        if key == 'UP':
            self.move_selection(-1)
        elif key == 'DOWN':
            self.move_selection(1)
        elif key == 'ENTER':
            return 'select'
        elif key == 'TAB':
            self.toggle_details()
        elif key.lower() == 'q':
            return 'quit'
        elif key == 'CTRL+C':
            return 'quit'
            
        return None
        
    def run(self) -> None:
        """Run the interactive menu loop."""
        self.running = True
        
        try:
            self.terminal.setup_terminal()
            
            while self.running:
                self.render()
                
                action = self.handle_input()
                
                if action == 'select':
                    # Execute selected option
                    selected_option = self.get_selected_option()
                    if selected_option:
                        # Restore terminal before executing action
                        self.terminal.restore_terminal()
                        
                        try:
                            selected_option.execute()
                        except Exception as e:
                            # Show error and wait for keypress
                            self.terminal.writeln(f"\nError: {str(e)}")
                            self.terminal.writeln("\nPress any key to continue...")
                            self.terminal.getch()
                        
                        # Re-setup terminal after action
                        self.terminal.setup_terminal()
                        
                elif action == 'quit':
                    self.running = False
                    
        finally:
            self.terminal.restore_terminal()
            self.terminal.show_cursor()
            
    def get_selected_option(self) -> MenuOption:
        """Get currently selected option.
        
        Returns:
            Selected MenuOption or None if index out of range
        """
        if 0 <= self.selected_index < len(self.options):
            return self.options[self.selected_index]
        return None
        
    def move_selection(self, direction: int) -> None:
        """Move selection up or down.
        
        Args:
            direction: -1 for up, 1 for down
        """
        if not self.options:
            return
            
        new_index = self.selected_index + direction
        
        # Wrap around
        if new_index < 0:
            new_index = len(self.options) - 1
        elif new_index >= len(self.options):
            new_index = 0
            
        self.selected_index = new_index
        
    def toggle_details(self) -> None:
        """Toggle details view on/off."""
        self.show_details = not self.show_details


class SubMenu(InteractiveMenu):
    """Submenu for specific installation types."""
    
    def __init__(self, title: str, installer_module, terminal: TerminalController):
        """Initialize submenu for an installer.
        
        Args:
            title: Submenu title
            installer_module: Installer instance with methods to build options
            terminal: Terminal controller for UI operations
        """
        self.installer = installer_module
        options = self._build_options()
        super().__init__(title, options, terminal)
        
    def _build_options(self) -> List[MenuOption]:
        """Build options specific to this installer.
        
        Returns:
            List of MenuOption instances for this installer
        """
        options = []
        
        # Check if installer has interactive options
        if hasattr(self.installer, 'get_interactive_options'):
            # Build options from interactive installer
            for opt_info in self.installer.get_interactive_options():
                option = MenuOption(
                    name=opt_info['name'],
                    description=opt_info['description'],
                    action=opt_info['action'],
                    status_checker=opt_info.get('status_checker')
                )
                options.append(option)
        else:
            # Build standard install/uninstall options
            if self.installer.is_installed():
                # Uninstall option
                option = MenuOption(
                    name="Uninstall",
                    description=f"Remove {self.installer.name}",
                    action=self._uninstall,
                    status_checker=lambda: "INSTALLED"
                )
            else:
                # Install option
                option = MenuOption(
                    name="Install",
                    description=f"Install {self.installer.name}",
                    action=self._install,
                    status_checker=lambda: "NOT INSTALLED"
                )
            options.append(option)
            
            # Add info option
            info_option = MenuOption(
                name="Show Details",
                description="Display detailed information",
                action=self._show_details
            )
            options.append(info_option)
            
        # Add back option
        back_option = MenuOption(
            name="← Back",
            description="Return to main menu",
            action=self._go_back
        )
        options.append(back_option)
        
        return options
        
    def _install(self) -> None:
        """Install the component."""
        self.terminal.writeln(f"\nInstalling {self.installer.name}...\n")
        
        result = self.installer.install()
        
        if result.success:
            self.terminal.writeln(f"\n✓ {result.message}")
        else:
            self.terminal.writeln(f"\n✗ {result.message}")
            
        self.terminal.writeln("\nPress any key to continue...")
        self.terminal.getch()
        
        # Rebuild options after installation
        self.options = self._build_options()
        
    def _uninstall(self) -> None:
        """Uninstall the component."""
        self.terminal.writeln(f"\nUninstalling {self.installer.name}...\n")
        
        result = self.installer.uninstall()
        
        if result.success:
            self.terminal.writeln(f"\n✓ {result.message}")
        else:
            self.terminal.writeln(f"\n✗ {result.message}")
            
        self.terminal.writeln("\nPress any key to continue...")
        self.terminal.getch()
        
        # Rebuild options after uninstallation
        self.options = self._build_options()
        
    def _show_details(self) -> None:
        """Show detailed information about the installer."""
        self.terminal.clear_screen()
        self.terminal.writeln(f"\n{self.installer.name} Details\n")
        self.terminal.writeln("=" * 40)
        
        details = self.installer.get_details()
        
        # Display details in a formatted way
        for key, value in details.items():
            if isinstance(value, list):
                self.terminal.writeln(f"\n{key}:")
                for item in value:
                    self.terminal.writeln(f"  - {item}")
            elif isinstance(value, dict):
                self.terminal.writeln(f"\n{key}:")
                for k, v in value.items():
                    self.terminal.writeln(f"  {k}: {v}")
            else:
                self.terminal.writeln(f"{key}: {value}")
                
        self.terminal.writeln("\nPress any key to continue...")
        self.terminal.getch()
        
    def _go_back(self) -> None:
        """Exit this submenu."""
        self.running = False