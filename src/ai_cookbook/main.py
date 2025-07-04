#!/usr/bin/env python3
"""
ai-cookbook - Interactive installer
"""

import sys
import argparse

def main():
    """Main entry point - supports interactive mode and recommended command"""
    parser = argparse.ArgumentParser(
        description='ethPandaOps AI Cookbook unified installer',
        add_help=False
    )
    parser.add_argument('--version', action='store_true', help='Show version')
    parser.add_argument('--help', action='store_true', help='Show this help message')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('command', nargs='?', help='Command to run (recommended)')
    
    args, unknown = parser.parse_known_args()
    
    if args.version:
        print("ai-cookbook v1.0.0")
        return
    
    if args.help:
        print("ai-cookbook v1.0.0 - ethPandaOps AI Cookbook unified installer")
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
        print()
        print("Interactive mode: Use arrow keys to navigate, Enter to select, 'q' to quit.")
        return
    
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
                print("✅ Successfully installed recommended tools!")
                
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