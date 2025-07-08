#!/usr/bin/env python3
"""
ai-cookbook - Interactive installer
"""

import sys
import os
import argparse

from .config.settings import ORG_DISPLAY_NAME, VERSION

def _apply_installer_operation(installer, file_name: str, operation: str) -> bool:
    """Apply an operation (install/uninstall) to a file using the appropriate installer method.
    
    Args:
        installer: The installer instance to use
        file_name: The file to operate on
        operation: Either 'install', 'update', or 'uninstall'
    
    Returns:
        bool: True if operation was successful, False otherwise
    """
    if operation in ['install', 'update']:
        if hasattr(installer, 'install_command'):
            installer.install_command(file_name)
        elif hasattr(installer, 'apply_hook_update'):
            installer.apply_hook_update(file_name)
        elif hasattr(installer, 'install_hook'):
            hook_name = file_name.replace('.sh', '')
            installer.install_hook(hook_name)
        elif hasattr(installer, 'install_language'):
            language = file_name.split('/')[0]
            installer.install_language(language)
        else:
            print(f"  [Warning] No install method for {file_name}")
            return False
    
    elif operation == 'uninstall':
        if hasattr(installer, 'uninstall_command'):
            installer.uninstall_command(file_name)
        elif hasattr(installer, 'uninstall_hook'):
            hook_name = file_name.replace('.sh', '')
            installer.uninstall_hook(hook_name)
        elif hasattr(installer, 'uninstall_language'):
            language = file_name.split('/')[0]
            installer.uninstall_language(language)
        else:
            print(f"  [Warning] No uninstall method for {file_name}")
            return False
    
    return True

def check_for_updates(skip_prompt: bool = False) -> None:
    """Check for updates and prompt to apply them.
    
    Args:
        skip_prompt: If True, skip update check entirely
    """
    if skip_prompt:
        return
        
    try:
        from .installers.commands import CommandsInstaller
        from .installers.code_standards import CodeStandardsInstaller
        from .installers.hooks import HooksInstaller
        from .installers.scripts import ScriptsInstaller
        from .updaters.detector import UpdateDetector
        
        # Initialize installers
        installers = {
            'commands': CommandsInstaller(),
            'code_standards': CodeStandardsInstaller(),
            'hooks': HooksInstaller(),
            'scripts': ScriptsInstaller()
        }
        
        # Choose UI based on environment or capability
        ui_preference = os.environ.get('AI_COOKBOOK_UPDATE_UI', 'tui').lower()
        
        if ui_preference == 'tui':
            try:
                from .updaters.ui_tui import TUIUpdateUI
                update_ui = TUIUpdateUI()
            except (ImportError, Exception) as e:
                # Fallback to simple UI if TUI fails
                if os.environ.get('DEBUG'):
                    print(f"[DEBUG] TUI failed: {e}")
                from .updaters.ui_simple import SimpleUpdateUI
                update_ui = SimpleUpdateUI()
        elif ui_preference == 'interactive':
            try:
                from .updaters.ui_interactive import InteractiveUpdateUI
                update_ui = InteractiveUpdateUI()
            except (ImportError, Exception):
                from .updaters.ui_simple import SimpleUpdateUI
                update_ui = SimpleUpdateUI()
        else:
            from .updaters.ui_simple import SimpleUpdateUI
            update_ui = SimpleUpdateUI()
        
        # Check for updates
        updates_to_apply = update_ui.check_and_prompt_updates(installers)
        
        # Check hooks sync first
        hooks_installer = installers.get('hooks')
        if hooks_installer:
            # Clean up missing projects from registry
            removed_projects = hooks_installer.project_registry.cleanup_missing_projects()
            if removed_projects:
                print("\n⚠️  Cleaned up registry for missing projects:")
                for project in removed_projects:
                    print(f"   - {project}")
            
            sync_result = hooks_installer.sync_hooks_with_files()
            if sync_result.details.get('removed_from_settings'):
                print("\n⚠️  Cleaned up hook settings for missing files:")
                for item in sync_result.details['removed_from_settings']:
                    project = item.get('project', '')
                    location = f" in {project}" if project else ""
                    print(f"   - {item['hook']} ({item['mode']}){location}: {item['reason']}")
            
            if sync_result.details.get('added_to_settings'):
                print("\n✅  Added missing hooks to settings:")
                for item in sync_result.details['added_to_settings']:
                    project = item.get('project', '')
                    location = f" in {project}" if project else ""
                    print(f"   + {item['hook']} ({item['mode']}){location}")
            
            if sync_result.details.get('orphaned_files'):
                print("\n⚠️  Found orphaned hook files (cannot be added to settings):")
                for item in sync_result.details['orphaned_files']:
                    project = item.get('project', '')
                    location = f" in {project}" if project else ""
                    print(f"   - {item['hook']} ({item['mode']}){location}: {item.get('reason', 'Unknown')}")
            
        
        # Check CLAUDE.md sync regardless of other updates
        cs_installer = installers.get('code_standards')
        if cs_installer:
            installed_langs = cs_installer._get_installed_languages()
            claude_md_langs = cs_installer._get_claude_md_languages()
            
            if set(installed_langs) != set(claude_md_langs):
                print("\n⚠️  CLAUDE.md is out of sync with installed code standards")
                print(f"   Installed: {sorted(installed_langs)}")
                print(f"   In CLAUDE.md: {sorted(claude_md_langs)}")
                
                response = input("\nSync CLAUDE.md now? [Y/n] ").strip().lower()
                if response in ('', 'y', 'yes'):
                    sync_result = cs_installer.sync_claude_md_with_installed()
                    if sync_result.success:
                        print("✅ CLAUDE.md synchronized")
                    else:
                        print(f"❌ Failed to sync: {sync_result.message}")
        
        if updates_to_apply is None:
            # User cancelled
            return
        elif not updates_to_apply:
            # No updates available
            update_ui.show_no_updates()
        else:
            # Apply updates
            total_updated = 0
            total_installed = 0
            total_deleted = 0
            
            for component_type, status in updates_to_apply.items():
                installer = installers[component_type]
                
                # Process updates
                for file_name in status.updated:
                    update_ui.show_update_progress(component_type, file_name, 'update')
                    
                    if _apply_installer_operation(installer, file_name, 'update'):
                        total_updated += 1
                
                # Process new files
                for file_name in status.new:
                    update_ui.show_update_progress(component_type, file_name, 'install')
                    
                    if _apply_installer_operation(installer, file_name, 'install'):
                        total_installed += 1
                
                # Process deletions
                for file_name in status.deleted:
                    update_ui.show_update_progress(component_type, file_name, 'delete')
                    
                    # For orphaned files, we can directly delete them
                    if 'ethpandaops/' in file_name and installer.update_detector:
                        # This is an orphaned file in ethpandaops directory
                        file_path = installer.update_detector.install_path / file_name
                        if file_path.exists():
                            # Back up before deletion
                            if hasattr(installer, 'backup_manager'):
                                installer.backup_manager.create_backup(file_path, f"orphaned_{file_name.replace('/', '_')}")
                            
                            # Delete file or directory
                            if file_path.is_dir():
                                import shutil
                                shutil.rmtree(file_path)
                            else:
                                file_path.unlink()
                            
                            # Remove metadata if it exists
                            installer.update_detector.remove_metadata(file_name)
                    else:
                        # Use installer-specific uninstall methods
                        if _apply_installer_operation(installer, file_name, 'uninstall'):
                            total_deleted += 1
                        else:
                            continue
            
            if hasattr(update_ui, 'show_update_complete'):
                update_ui.show_update_complete(total_updated, total_installed, total_deleted)
            
            # Sync CLAUDE.md if code standards were modified
            if 'code_standards' in updates_to_apply:
                print("\nSynchronizing CLAUDE.md with installed code standards...")
                cs_installer = installers['code_standards']
                sync_result = cs_installer.sync_claude_md_with_installed()
                if sync_result.success:
                    print("✓ CLAUDE.md synchronized")
                else:
                    print(f"⚠ Failed to sync CLAUDE.md: {sync_result.message}")
            
    except KeyboardInterrupt:
        # User cancelled update check
        print("\nUpdate check cancelled.")
    except Exception as e:
        # Don't fail the entire program if update check fails
        print(f"Warning: Could not check for updates: {e}")

def main() -> None:
    """Main entry point - supports interactive mode and recommended command"""
    parser = argparse.ArgumentParser(
        description=f'{ORG_DISPLAY_NAME} AI Cookbook unified installer',
        add_help=False
    )
    parser.add_argument('--version', action='store_true', help='Show version')
    parser.add_argument('--help', action='store_true', help='Show this help message')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--no-auto-update', action='store_true', help='Skip automatic update check')
    parser.add_argument('command', nargs='?', help='Command to run (recommended)')
    
    args, unknown = parser.parse_known_args()
    
    if args.version:
        print(f"ai-cookbook v{VERSION}")
        return
    
    if args.help:
        print(f"ai-cookbook v{VERSION} - {ORG_DISPLAY_NAME} AI Cookbook unified installer")
        print()
        print("Interactive installer for:")
        print("  • Claude Commands - AI-assisted development commands")
        print("  • Code Standards - Language-specific coding standards")  
        print("  • Hooks - Automated formatting and linting")
        print("  • Scripts - Add utility scripts to PATH")
        print()
        print("Usage:")
        print("  ai-cookbook              Launch interactive installer")
        print("  ai-cookbook recommended  Install recommended tools and remove non-recommended ones")
        print("  ai-cookbook --help       Show this help")
        print("  ai-cookbook --version    Show version")
        print("  ai-cookbook --yes        Skip confirmation prompts")
        print("  ai-cookbook --no-auto-update  Skip automatic update check")
        print()
        print("Interactive mode: Use arrow keys to navigate, Enter/→ to select, q/← to quit.")
        return
    
    # Check for updates before any command (unless skipped)
    if not args.no_auto_update:
        check_for_updates(skip_prompt=False)
    
    # Handle recommended command
    if args.command == 'recommended':
        try:
            from .installers.recommended import RecommendedToolsInstaller
            installer = RecommendedToolsInstaller()
            
            print("🐼 ethPandaOps AI Cookbook - Installing Recommended Tools")
            print("=" * 60)
            
            # Install recommended tools
            result = installer.install(skip_confirmation=args.yes)
            
            if result.success:
                print("\n✅ Successfully installed recommended tools!")
                
                # Show what was installed/uninstalled
                if result.details:
                    installed = result.details.get('installed', {})
                    uninstalled = result.details.get('uninstalled', {})
                    
                    # Count totals
                    total_installed = sum(len(tools) for tools in installed.values())
                    total_uninstalled = sum(len(tools) for tools in uninstalled.values())
                    
                    # Display installed tools by category
                    if installed:
                        print("\n📦 Installed:")
                        for category, tools in installed.items():
                            if tools:
                                print(f"  {category.title()}:")
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
                                print(f"  {category.title()}:")
                                for tool in tools:
                                    print(f"    ❌ {tool}")
                    
                    # Summary
                    if total_installed > 0 or total_uninstalled > 0:
                        print("\n📊 Summary:")
                        if total_installed > 0:
                            print(f"  • {total_installed} tools installed/verified")
                        if total_uninstalled > 0:
                            print(f"  • {total_uninstalled} non-recommended tools removed")
                
                print("\n🎉 Your environment is now configured with the recommended ethPandaOps tools!")
                
            else:
                print("❌ Failed to install recommended tools:")
                print(result.message)
                if result.details and 'errors' in result.details:
                    for error in result.details['errors']:
                        print(f"  • {error}")
                sys.exit(1)
                
        except ImportError as e:
            print(f"❌ Error loading recommended tools installer: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n❌ Installation cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)
        return
    
    # Handle unknown commands
    if args.command and args.command != 'recommended':
        print(f"❌ Unknown command: {args.command}")
        print("Available commands: recommended")
        print("Run 'ai-cookbook --help' for usage information.")
        sys.exit(1)
    
    # Launch interactive mode (default)
    try:
        from .tui import run_interactive
        run_interactive()
    except ImportError as e:
        print(f"❌ Error launching interactive mode: {e}")
        print("Please ensure all dependencies are installed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Installer cancelled by user.")
        sys.exit(0)

if __name__ == '__main__':
    main()