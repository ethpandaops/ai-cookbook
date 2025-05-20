#!/usr/bin/env python3

"""
EthPandaOps AI Documentation Initialization Script

This script recursively initializes AI documentation for a project by:
1. Running init-project-ai-docs at the project root
2. Finding all directories with code and running init-component-ai-docs for each
"""

import argparse
import os
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import List, Optional


class TaskStats:
    """Track statistics for a single task."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = time.time()
        self.end_time = None
        self.cost_usd = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.duration_ms = 0
        self.success = False
        
    def complete(self, cost: float = 0.0, input_tokens: int = 0, output_tokens: int = 0, duration_ms: int = 0):
        """Mark task as complete with stats."""
        self.end_time = time.time()
        self.cost_usd = cost
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms
        self.success = True
        
    @property
    def duration_seconds(self) -> float:
        """Get task duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class ProgressSpinner:
    """A progress spinner with timer and recent message display for command execution."""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_index = 0
        self.start_time = time.time()
        self.running = False
        self.thread = None
        self.recent_messages = []
        self.lock = threading.Lock()
        self.stats = None  # Will be set by caller
    
    def start(self):
        """Start the spinner in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def add_message(self, message: str):
        """Add a message to the recent messages list."""
        with self.lock:
            self.recent_messages.append(message)
            # Keep only last 5 messages
            if len(self.recent_messages) > 5:
                self.recent_messages = self.recent_messages[-5:]
    
    def stop(self):
        """Stop the spinner and show completion."""
        self.running = False
        if self.thread:
            self.thread.join()
        
        elapsed = time.time() - self.start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        
        # Calculate how many lines to clear (progress line + max 5 message lines + waiting line)
        lines_to_clear = 2  # At minimum there's the progress line and one message/waiting line
        with self.lock:
            if self.recent_messages:
                lines_to_clear = 1 + len(self.recent_messages[-5:])  # progress + actual messages
        
        # Clear the previous spinner output
        for _ in range(lines_to_clear):
            print("\033[1A\033[K", end="")
        
        # Show completion with stats if available
        if self.stats:
            print(f"📦 Completed: {self.component_name:<30} ✅ {mins:02d}:{secs:02d} | ${self.stats.cost_usd:.4f} | {self.stats.input_tokens + self.stats.output_tokens:,} tokens")
        else:
            print(f"📦 Completed: {self.component_name:<40} ✅ {mins:02d}:{secs:02d}")
        
        # Show final messages if any
        with self.lock:
            if self.recent_messages:
                for i, msg in enumerate(self.recent_messages[-3:]):  # Show last 3 messages
                    truncated = msg[:70] + "..." if len(msg) > 70 else msg
                    prefix = "   └─" if i == len(self.recent_messages[-3:]) - 1 else "   ├─"
                    print(f"{prefix} {truncated}")
        
        # Restore cursor
        print("\033[?25h", end="", flush=True)
    
    def _spin(self):
        """Internal spinning animation with message display."""
        # Hide cursor
        print("\033[?25l", end="", flush=True)
        lines_printed = 0
        
        while self.running:
            # Clear previous lines if any
            if lines_printed > 0:
                for _ in range(lines_printed):
                    print("\033[1A\033[K", end="")
            
            elapsed = time.time() - self.start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            
            spinner_char = self.spinner_chars[self.spinner_index]
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            
            # Get recent messages for display
            with self.lock:
                display_messages = self.recent_messages[-5:] if self.recent_messages else []
            
            # Print main progress line
            print(f"📦 Processing: {self.component_name:<40} {spinner_char} {mins:02d}:{secs:02d}")
            lines_printed = 1
            
            # Show recent messages (last 5)
            if display_messages:
                for i, msg in enumerate(display_messages):
                    truncated = msg[:60] + "..." if len(msg) > 60 else msg
                    print(f"   {'└─' if i == len(display_messages) - 1 else '├─'} {truncated}")
                    lines_printed += 1
            else:
                print("   ⏳ Waiting for response...")
                lines_printed += 1
            
            time.sleep(0.3)


class DocumentationInitializer:
    """Main class for initializing AI documentation."""
    
    def __init__(self, project_root: str = ".", dry_run: bool = False, verbose: bool = False):
        self.project_root = Path(project_root).resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        self.component_dirs: List[Path] = []
        self.task_stats: List[TaskStats] = []
        
        # Code file extensions to look for
        self.code_extensions = {
            "*.go", "*.ts", "*.js", "*.py", "*.rs", 
            "*.java", "*.cpp", "*.c", "*.h"
        }
        
        # Directories to skip
        self.skip_patterns = {
            ".git", ".svn", ".hg", "node_modules", "vendor", 
            "build", "dist", "target", "static", "__pycache__"
        }
    
    def log(self, message: str):
        """Log message if verbose or dry run mode."""
        if self.verbose or self.dry_run:
            print(message)
    
    def execute_command(self, cmd: List[str], component_name: Optional[str] = None) -> bool:
        """Execute a command with optional progress spinner and streaming output."""
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
            return True
        
        self.log(f"Executing: {' '.join(cmd)}")
        
        if component_name:
            # Create task stats for tracking
            task_stats = TaskStats(component_name)
            self.task_stats.append(task_stats)
            
            # Run with progress spinner and streaming output
            spinner = ProgressSpinner(component_name)
            spinner.stats = task_stats  # Link stats to spinner
            spinner.start()
            
            try:
                # Start process for streaming
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                import json
                
                # Read output line by line
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    
                    if output:
                        line = output.strip()
                        
                        # Try to parse as JSON for streaming format
                        try:
                            json_obj = json.loads(line)
                            
                            # Handle different message types
                            if isinstance(json_obj, dict):
                                # Handle assistant messages with nested structure
                                if json_obj.get('type') == 'assistant' and 'message' in json_obj:
                                    message = json_obj['message']
                                    
                                    # Extract token usage if available
                                    if 'usage' in message:
                                        usage = message['usage']
                                        input_tokens = usage.get('input_tokens', 0)
                                        output_tokens = usage.get('output_tokens', 0)
                                        # Update task stats with token info
                                        task_stats.input_tokens += input_tokens
                                        task_stats.output_tokens += output_tokens
                                    
                                    if 'content' in message and isinstance(message['content'], list):
                                        for item in message['content']:
                                            if isinstance(item, dict):
                                                if item.get('type') == 'text':
                                                    text = item.get('text', '')
                                                    if text:
                                                        spinner.add_message(text)
                                                elif item.get('type') == 'tool_use':
                                                    tool_name = item.get('name', 'unknown')
                                                    spinner.add_message(f"🔧 Using tool: {tool_name}")
                                
                                # Handle user messages (tool results)
                                elif json_obj.get('type') == 'user' and 'message' in json_obj:
                                    message = json_obj['message']
                                    if 'content' in message and isinstance(message['content'], list):
                                        for item in message['content']:
                                            if isinstance(item, dict) and item.get('type') == 'tool_result':
                                                content = item.get('content', '')
                                                if content and len(content) < 100:  # Only show short tool results
                                                    spinner.add_message(f"✅ {content[:50]}...")
                                
                                # Handle system messages with stats
                                elif json_obj.get('type') == 'system':
                                    subtype = json_obj.get('subtype', '')
                                    if subtype == 'init':
                                        spinner.add_message("🚀 Initializing Claude session...")
                                    elif 'cost_usd' in json_obj:
                                        # Extract stats from final system message
                                        cost = json_obj.get('cost_usd', 0)
                                        duration_ms = json_obj.get('duration_ms', 0)
                                        # Note: Token info isn't in the system message, would need to parse from usage
                                        task_stats.complete(cost=cost, duration_ms=duration_ms)
                                        spinner.add_message(f"💰 Completed (${cost:.4f})")
                                        
                        except json.JSONDecodeError:
                            # Not JSON, could be regular text output or partial JSON
                            if line and self.verbose:
                                spinner.add_message(f"📝 {line}")
                
                spinner.stop()
                
                # Get final result
                return_code = process.poll()
                stderr_output = process.stderr.read()
                
                if return_code != 0:
                    print(f"❌ Command failed with exit status {return_code}")
                    if stderr_output:
                        print(f"Error: {stderr_output}")
                    return False
                
                # Mark as successful if not already marked by stats
                if not task_stats.success:
                    task_stats.complete()
                    
                return True
                
            except Exception as e:
                spinner.stop()
                print(f"❌ Command failed with exception: {e}")
                return False
        else:
            # Run without spinner
            try:
                result = subprocess.run(cmd, text=True)
                return result.returncode == 0
            except Exception as e:
                print(f"❌ Command failed with exception: {e}")
                return False
    
    def check_claude_installed(self) -> bool:
        """Check if claude command is available."""
        try:
            subprocess.run(["claude", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: claude could not be found -- have you installed Claude Code? (https://docs.anthropic.com/en/docs/claude-code)")
            return False
    
    def validate_project_root(self) -> bool:
        """Validate that project root exists."""
        if not self.project_root.exists():
            print(f"Error: Project directory does not exist: {self.project_root}")
            return False
        
        if not self.project_root.is_dir():
            print(f"Error: Project path is not a directory: {self.project_root}")
            return False
        
        return True
    
    def should_skip_directory(self, dir_path: Path) -> bool:
        """Check if directory should be skipped."""
        # Skip if any part of path contains skip patterns
        for part in dir_path.parts:
            if part.startswith('.') and part != '.':
                return True
            if part in self.skip_patterns:
                return True
        
        return False
    
    def has_code_files(self, dir_path: Path) -> bool:
        """Check if directory contains code files."""
        try:
            for pattern in self.code_extensions:
                if list(dir_path.glob(pattern)):
                    return True
            return False
        except PermissionError:
            return False
    
    def has_files(self, dir_path: Path) -> bool:
        """Check if directory contains any files (not just subdirectories)."""
        try:
            for item in dir_path.iterdir():
                if item.is_file():
                    return True
            return False
        except PermissionError:
            return False
    
    def find_component_directories(self):
        """Find all directories that contain code files."""
        self.component_dirs = []
        
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # Skip the project root itself
            if root_path == self.project_root:
                continue
            
            # Skip directories that should be ignored
            if self.should_skip_directory(root_path):
                continue
            
            # Skip directories with no files
            if not self.has_files(root_path):
                continue
            
            # Check if directory contains code files
            if self.has_code_files(root_path):
                self.component_dirs.append(root_path)
        
        # Sort directories for consistent processing
        self.component_dirs.sort()
    
    def show_plan(self):
        """Display the documentation plan."""
        print()
        print("📋 Documentation Plan")
        print("==================")
        print()
        print("🎯 Project Root:")
        print("   ├── CLAUDE.md")
        print("   ├── .cursor/")
        print("   │   └── rules/")
        print("   │       ├── project_architecture.mdc")
        print("   │       ├── code_standards.mdc")
        print("   │       └── development_workflow.mdc")
        print("   ├── llms/ -> .cursor (symlink)")
        print("   └── .roo/ -> .cursor (symlink)")
        print("   └── ai_docs/ -> .cursor (symlink)")
        print()
        
        if not self.component_dirs:
            print("⚠️  No component directories found")
        else:
            print(f"📦 Components ({len(self.component_dirs)} directories):")
            
            for i, component_dir in enumerate(self.component_dirs):
                rel_path = component_dir.relative_to(self.project_root)
                
                if i == len(self.component_dirs) - 1:
                    print(f"   └── {rel_path}/")
                    print("       └── CLAUDE.md")
                else:
                    print(f"   ├── {rel_path}/")
                    print("   │   └── CLAUDE.md")
        
        print()
        print("📊 Summary:")
        print("   • Will create 1 project root with .cursor/rules/ structure")
        print(f"   • Will create CLAUDE.md in {len(self.component_dirs)} component directories")
        print("   • Each component CLAUDE.md references project root rules, and will create an equivalent rule in .cursor/rules/")
        print()
    
    def confirm_execution(self) -> bool:
        """Ask user for confirmation to proceed."""
        if self.dry_run:
            return True
        
        try:
            response = input("🤔 Proceed with this plan? [y/N]: ").strip().lower()
            if response in ('y', 'yes'):
                print("✅ Starting documentation generation...")
                return True
            else:
                print("❌ Cancelled by user")
                return False
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return False
    
    def execute_claude_command(self, command: str, params: str, component_name: str) -> bool:
        """Execute a claude command with parameters."""
        cmd = [
            "claude", "-p", "--dangerously-skip-permissions",
            "--verbose", "--output-format", "stream-json",
            f"/{command}", params
        ]
        print(f"Executing: {' '.join(cmd)}")
        return self.execute_command(cmd, component_name)
    
    def show_summary(self):
        """Show a summary of all completed tasks with stats."""
        if not self.task_stats:
            return
            
        print("\n" + "="*80)
        print("📊 EXECUTION SUMMARY")
        print("="*80)
        
        total_cost = 0.0
        total_tokens = 0
        total_duration = 0.0
        successful_tasks = 0
        
        for i, stats in enumerate(self.task_stats):
            if stats.success:
                successful_tasks += 1
                total_cost += stats.cost_usd
                total_tokens += stats.input_tokens + stats.output_tokens
                total_duration += stats.duration_seconds
                
                # Format task info
                mins = int(stats.duration_seconds // 60)
                secs = int(stats.duration_seconds % 60)
                tokens = stats.input_tokens + stats.output_tokens
                
                status = "✅" if stats.success else "❌"
                print(f"{i+1:2d}. {status} {stats.name:<30} | {mins:02d}:{secs:02d} | ${stats.cost_usd:>8.4f} | {tokens:>6,} tokens")
        
        print("-" * 80)
        
        # Overall totals
        total_mins = int(total_duration // 60)
        total_secs = int(total_duration % 60)
        
        print(f"📈 TOTALS:")
        print(f"   ✅ Successful tasks: {successful_tasks}/{len(self.task_stats)}")
        print(f"   ⏱️  Total time: {total_mins:02d}:{total_secs:02d}")
        print(f"   💰 Total cost: ${total_cost:.4f}")
        print(f"   🔤 Total tokens: {total_tokens:,}")
        
        if total_tokens > 0:
            avg_cost_per_token = total_cost / total_tokens * 1000  # Cost per 1K tokens
            print(f"   📊 Avg cost/1K tokens: ${avg_cost_per_token:.4f}")
        
        print("="*80)
    
    def run(self) -> bool:
        """Run the full documentation initialization process."""
        print("🐼 ethPandaOps AI Documentation Initialization")
        print("==============================================")
        print(f"Project directory: {self.project_root}")
        print()
        
        # Validate prerequisites
        if not self.check_claude_installed():
            return False
        
        if not self.validate_project_root():
            return False
        
        # Planning phase
        print("📋 Planning documentation structure...")
        print()
        print("🔍 Scanning project structure...")
        
        self.find_component_directories()
        self.show_plan()
        
        # Confirmation
        if not self.confirm_execution():
            return False
        
        print()
        
        # Execute project root initialization
        print("📋 Initializing project-level documentation...")
        success = self.execute_claude_command(
            "init-project-ai-docs", 
            f"project-root={self.project_root}",
            "Project Root"
        )
        
        if not success:
            return False
        
        print()
        
        # Execute component initialization
        if self.component_dirs:
            print("📦 Processing components...")
            
            for component_dir in self.component_dirs:
                rel_path = component_dir.relative_to(self.project_root)
                
                success = self.execute_claude_command(
                    "init-component-ai-docs",
                    f"project-root={self.project_root},component-dir={component_dir}",
                    str(rel_path)
                )
                
                if not success:
                    return False
        
        # Final summary
        print()
        if self.dry_run:
            print("🔍 Dry run completed. Use without --dry-run to execute.")
        else:
            print("✅ AI documentation initialization completed!")
            print()
            print("📋 Summary:")
            print(f"   • Project root processed: {self.project_root}")
            print(f"   • Components processed: {len(self.component_dirs)}")
            print()
            print("🚀 Next steps:")
            print("   • Review generated CLAUDE.md files")
            print("   • Review generated .cursor/rules/*.mdc files")
            print("   • Customize the documentation as needed")
            
            # Show detailed stats summary
            self.show_summary()
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize AI documentation for a project and its components.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize from current directory (simplest usage)
  %(prog)s

  # Initialize specific project directory  
  %(prog)s /path/to/project

  # Dry run to see what would happen
  %(prog)s --dry-run
        """
    )
    
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="Project directory to process (default: current directory)"
    )
    
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true", 
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Initialize and run
    initializer = DocumentationInitializer(
        project_root=args.project_root,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    success = initializer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()