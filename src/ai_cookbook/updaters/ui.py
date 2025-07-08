"""UI for displaying and applying updates."""

import os
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich import box
from .detector import UpdateStatus
# Removed BaseInstaller import to avoid circular dependency


class UpdateUI:
    """Handles update detection and prompting UI."""
    
    def __init__(self, console: Console):
        """Initialize update UI.
        
        Args:
            console: Rich console for output
        """
        self.console = console
    
    def _format_update_summary(self, all_updates: Dict[str, UpdateStatus]) -> Table:
        """Format update summary as a table.
        
        Args:
            all_updates: Dictionary mapping component types to their update status
            
        Returns:
            Rich table with update summary
        """
        table = Table(
            title="Available Updates",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Component", style="bold", width=20)
        table.add_column("Updated", justify="center", style="yellow")
        table.add_column("New", justify="center", style="green")
        table.add_column("Removed", justify="center", style="red")
        table.add_column("Total Changes", justify="center", style="bold")
        
        total_updated = 0
        total_new = 0
        total_deleted = 0
        
        for component_type, status in all_updates.items():
            if status.has_changes:
                updated_count = len(status.updated)
                new_count = len(status.new)
                deleted_count = len(status.deleted)
                
                total_updated += updated_count
                total_new += new_count
                total_deleted += deleted_count
                
                table.add_row(
                    component_type.title(),
                    str(updated_count) if updated_count > 0 else "-",
                    str(new_count) if new_count > 0 else "-",
                    str(deleted_count) if deleted_count > 0 else "-",
                    str(status.total_changes)
                )
        
        # Add total row
        if total_updated + total_new + total_deleted > 0:
            table.add_section()
            table.add_row(
                "TOTAL",
                str(total_updated) if total_updated > 0 else "-",
                str(total_new) if total_new > 0 else "-",
                str(total_deleted) if total_deleted > 0 else "-",
                str(total_updated + total_new + total_deleted),
                style="bold magenta"
            )
        
        return table
    
    def _format_detailed_changes(self, component_type: str, status: UpdateStatus) -> str:
        """Format detailed changes for a component type.
        
        Args:
            component_type: Type of component (e.g., 'commands')
            status: Update status for the component
            
        Returns:
            Formatted string with detailed changes
        """
        lines = [f"\n[bold]{component_type.title()}:[/bold]"]
        
        if status.updated:
            lines.append("\n  [yellow]Updated:[/yellow]")
            for file in status.updated[:10]:  # Limit to first 10
                lines.append(f"    • {file}")
            if len(status.updated) > 10:
                lines.append(f"    ... and {len(status.updated) - 10} more")
        
        if status.new:
            lines.append("\n  [green]New:[/green]")
            for file in status.new[:10]:
                lines.append(f"    • {file}")
            if len(status.new) > 10:
                lines.append(f"    ... and {len(status.new) - 10} more")
        
        if status.deleted:
            lines.append("\n  [red]Removed (will be deleted):[/red]")
            for file in status.deleted[:10]:
                lines.append(f"    • {file}")
            if len(status.deleted) > 10:
                lines.append(f"    ... and {len(status.deleted) - 10} more")
        
        return "\n".join(lines)
    
    def check_and_prompt_updates(self, installers: Dict[str, Any]) -> Optional[Dict[str, UpdateStatus]]:
        """Check for updates and prompt user to apply them.
        
        Args:
            installers: Dictionary of component installers
            
        Returns:
            Dictionary of updates to apply, or None if cancelled
        """
        # Check for updates across all installers
        all_updates = {}
        has_any_updates = False
        
        with self.console.status("Checking for updates..."):
            for name, installer in installers.items():
                if hasattr(installer, 'check_updates'):
                    status = installer.check_updates()
                    if status and status.has_changes:
                        all_updates[name] = status
                        has_any_updates = True
        
        if not has_any_updates:
            return None
        
        # Display update summary
        self.console.print()
        summary_table = self._format_update_summary(all_updates)
        self.console.print(summary_table)
        
        # Show detailed changes if not too many
        total_changes = sum(s.total_changes for s in all_updates.values())
        if total_changes <= 20:
            # Show all details
            for component_type, status in all_updates.items():
                details = self._format_detailed_changes(component_type, status)
                self.console.print(details)
        else:
            # Show summary only for large updates
            self.console.print(
                f"\n[dim]Showing summary only ({total_changes} total changes). "
                "Run with --verbose to see all details.[/dim]"
            )
        
        # Prompt for confirmation
        self.console.print()
        if Confirm.ask("Apply these updates now?", default=True):
            return all_updates
        
        return None
    
    def show_update_progress(self, component_type: str, file_name: str, action: str):
        """Show progress for an individual update.
        
        Args:
            component_type: Type of component being updated
            file_name: Name of the file being processed
            action: Action being performed ('update', 'install', 'delete')
        """
        icons = {
            'update': '🔄',
            'install': '✨',
            'delete': '🗑️'
        }
        colors = {
            'update': 'yellow',
            'install': 'green', 
            'delete': 'red'
        }
        
        icon = icons.get(action, '•')
        color = colors.get(action, 'white')
        
        self.console.print(
            f"  {icon} [{color}]{action.title()}[/{color}] {component_type}/{file_name}"
        )
    
    def show_update_complete(self, total_updated: int, total_installed: int, total_deleted: int):
        """Show completion message after updates.
        
        Args:
            total_updated: Number of files updated
            total_installed: Number of files newly installed
            total_deleted: Number of files deleted
        """
        parts = []
        if total_updated > 0:
            parts.append(f"{total_updated} updated")
        if total_installed > 0:
            parts.append(f"{total_installed} installed")
        if total_deleted > 0:
            parts.append(f"{total_deleted} deleted")
        
        if parts:
            message = f"✅ Updates complete: {', '.join(parts)}"
            self.console.print(Panel(message, style="green", box=box.ROUNDED))


def get_update_ui():
    """Factory function to get the appropriate update UI based on environment."""
    ui_preference = os.environ.get('AI_COOKBOOK_UPDATE_UI', 'tui').lower()
    
    if ui_preference == 'tui':
        try:
            from .ui_tui import TUIUpdateUI
            return TUIUpdateUI()
        except (ImportError, Exception) as e:
            # Fallback to simple UI if TUI fails
            if os.environ.get('DEBUG'):
                print(f"[DEBUG] TUI failed: {e}")
            from .ui_simple import SimpleUpdateUI
            return SimpleUpdateUI()
    elif ui_preference == 'interactive':
        try:
            from .ui_interactive import InteractiveUpdateUI
            return InteractiveUpdateUI()
        except (ImportError, Exception):
            from .ui_simple import SimpleUpdateUI
            return SimpleUpdateUI()
    else:
        from .ui_simple import SimpleUpdateUI
        return SimpleUpdateUI()