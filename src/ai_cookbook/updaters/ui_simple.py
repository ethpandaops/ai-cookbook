"""Simple text-based UI for displaying and applying updates."""

import os
from typing import Dict, List, Optional, Any
from .detector import UpdateStatus
# Removed BaseInstaller import to avoid circular dependency


class SimpleUpdateUI:
    """Handles update detection and prompting UI without rich dependency."""
    
    def _format_update_summary(self, all_updates: Dict[str, UpdateStatus]) -> str:
        """Format update summary as text.
        
        Args:
            all_updates: Dictionary mapping component types to their update status
            
        Returns:
            Formatted string with update summary
        """
        lines = ["", "Available Updates:", "=" * 60]
        
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
                
                line = f"{component_type.title():20} "
                parts = []
                if updated_count > 0:
                    parts.append(f"{updated_count} updated")
                if new_count > 0:
                    parts.append(f"{new_count} new")
                if deleted_count > 0:
                    parts.append(f"{deleted_count} removed")
                line += ", ".join(parts)
                lines.append(line)
        
        lines.append("-" * 60)
        lines.append(f"{'TOTAL':20} {total_updated} updated, {total_new} new, {total_deleted} removed")
        lines.append("")
        
        return "\n".join(lines)
    
    def _format_detailed_changes(self, component_type: str, status: UpdateStatus) -> str:
        """Format detailed changes for a component type.
        
        Args:
            component_type: Type of component (e.g., 'commands')
            status: Update status for the component
            
        Returns:
            Formatted string with detailed changes
        """
        lines = [f"\n{component_type.title()}:"]
        
        if status.updated:
            lines.append("\n  Updated:")
            for file in status.updated[:10]:  # Limit to first 10
                lines.append(f"    • {file}")
            if len(status.updated) > 10:
                lines.append(f"    ... and {len(status.updated) - 10} more")
        
        if status.new:
            lines.append("\n  New:")
            for file in status.new[:10]:
                lines.append(f"    • {file}")
            if len(status.new) > 10:
                lines.append(f"    ... and {len(status.new) - 10} more")
        
        if status.deleted:
            lines.append("\n  Removed (will be deleted):")
            for file in status.deleted[:10]:
                # Check if it's an orphaned file (in ethpandaops dir)
                if 'ethpandaops/' in file:
                    # Check if it's likely a directory (code standards)
                    if '/' not in file or file.count('/') == 0:
                        lines.append(f"    • {file}/ (orphaned directory)")
                    else:
                        lines.append(f"    • {file} (orphaned)")
                else:
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
        
        print("Checking for updates...")
        for name, installer in installers.items():
            if hasattr(installer, 'check_updates'):
                status = installer.check_updates()
                if status and status.has_changes:
                    all_updates[name] = status
                    has_any_updates = True
        
        if not has_any_updates:
            # Return empty dict to indicate no updates (different from None which means cancelled)
            return {}
        
        # Display update summary
        summary = self._format_update_summary(all_updates)
        print(summary)
        
        # Show detailed changes if not too many
        total_changes = sum(s.total_changes for s in all_updates.values())
        if total_changes <= 20:
            # Show all details
            for component_type, status in all_updates.items():
                details = self._format_detailed_changes(component_type, status)
                print(details)
        else:
            # Show summary only for large updates
            print(f"\nShowing summary only ({total_changes} total changes).")
        
        # Prompt for confirmation
        print()
        
        # Add debug hint if needed
        if os.environ.get('DEBUG', '').lower() not in ('1', 'true', 'yes'):
            print("(Tip: Run with DEBUG=1 for detailed information)")
        
        response = input("Apply these updates now? [Y/n] ").strip().lower()
        if response in ('', 'y', 'yes'):
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
            'update': '↻',
            'install': '+',
            'delete': '-'
        }
        
        icon = icons.get(action, '•')
        print(f"  {icon} {action.title()} {component_type}/{file_name}")
    
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
            print(f"\n{message}\n")
    
    def show_no_updates(self):
        """Show message when no updates are available."""
        print("✅ All components are up to date!")