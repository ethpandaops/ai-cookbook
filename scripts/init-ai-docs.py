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
from concurrent.futures import ThreadPoolExecutor, as_completed
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
            
            time.sleep(0.5)  # Slower refresh rate to reduce flicker


class DocumentationInitializer:
    """Main class for initializing AI documentation."""
    
    def __init__(self, project_root: str = ".", dry_run: bool = False, verbose: bool = False, max_workers: int = 10):
        self.project_root = Path(project_root).resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        self.max_workers = max_workers
        self.component_dirs: List[Path] = []
        self.component_dirs_by_depth: dict[int, List[Path]] = {}
        self.component_line_counts: dict[Path, int] = {}
        self.task_stats: List[TaskStats] = []
        
        # Code file extensions to look for
        self.code_extensions = {
            "*.go", "*.ts", "*.js", "*.py", "*.rs", 
            "*.java", "*.cpp", "*.c", "*.h", "*.md", "*.sh", "*.star"
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
    
    def execute_command(self, cmd: List[str], component_name: Optional[str] = None, working_dir: Optional[Path] = None) -> bool:
        """Execute a command with optional progress spinner and streaming output."""
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
            if working_dir:
                print(f"[DRY RUN] Working directory: {working_dir}")
            return True
        
        self.log(f"Executing: {' '.join(cmd)}")
        if working_dir:
            self.log(f"Working directory: {working_dir}")
        
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
                    universal_newlines=True,
                    cwd=working_dir
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
                                                    text = item.get('text', '').strip()
                                                    # Only add non-empty text messages from Claude
                                                    if text and len(text) > 10:  # Skip very short messages
                                                        # Truncate long messages for display
                                                        display_text = text[:100] + "..." if len(text) > 100 else text
                                                        spinner.add_message(display_text)
                                                elif item.get('type') == 'tool_use':
                                                    tool_name = item.get('name', 'unknown')
                                                    spinner.add_message(f"🔧 Using tool: {tool_name}")
                                
                                # Handle user messages (tool results) - skip these to reduce spam
                                elif json_obj.get('type') == 'user' and 'message' in json_obj:
                                    # Skip user messages (tool results) to reduce console spam
                                    pass
                                
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
                            # Skip non-JSON output to reduce spam unless in verbose mode
                            pass
                
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
                result = subprocess.run(cmd, text=True, cwd=working_dir)
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
    
    def count_lines_in_directory(self, dir_path: Path) -> int:
        """Count total lines of code in all matching files in a directory."""
        total_lines = 0
        try:
            for pattern in self.code_extensions:
                for file_path in dir_path.glob(pattern):
                    if file_path.is_file():
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = sum(1 for line in f if line.strip())  # Count non-empty lines
                                total_lines += lines
                        except Exception:
                            # Skip files that can't be read
                            pass
            return total_lines
        except PermissionError:
            return 0
    
    def process_directory(self, root_path: Path) -> Optional[tuple[Path, int]]:
        """Process a single directory and return path and line count if it contains code."""
        # Skip the project root itself
        if root_path == self.project_root:
            return None
        
        # Skip directories that should be ignored
        if self.should_skip_directory(root_path):
            return None
        
        # Skip directories with no files
        if not self.has_files(root_path):
            return None
        
        # Check if directory contains code files
        if self.has_code_files(root_path):
            # Count lines of code in this directory
            line_count = self.count_lines_in_directory(root_path)
            if line_count > 0:  # Only include directories with actual code
                return (root_path, line_count)
        
        return None

    def find_component_directories(self):
        """Find all directories that contain code files, organized by depth level."""
        all_component_dirs = []
        
        # Collect all directories to process
        dirs_to_process = []
        for root, _, _ in os.walk(self.project_root):
            root_path = Path(root)
            if not self.should_skip_directory(root_path):
                dirs_to_process.append(root_path)
        
        total_dirs = len(dirs_to_process)
        print(f"🔍 Scanning {total_dirs} directories for code files (using {self.max_workers} threads)...")
        
        dirs_processed = 0
        start_time = time.time()
        
        # Process directories in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_dir = {executor.submit(self.process_directory, dir_path): dir_path 
                           for dir_path in dirs_to_process}
            
            # Process completed tasks
            for future in as_completed(future_to_dir):
                dirs_processed += 1
                
                # Show progress every 10 directories or at completion
                if dirs_processed % 10 == 0 or dirs_processed == total_dirs:
                    elapsed = time.time() - start_time
                    rate = dirs_processed / elapsed if elapsed > 0 else 0
                    eta = (total_dirs - dirs_processed) / rate if rate > 0 else 0
                    print(f"   Progress: {dirs_processed}/{total_dirs} ({dirs_processed/total_dirs*100:.1f}%) | "
                          f"Rate: {rate:.1f} dirs/sec | ETA: {eta:.1f}s", end='\r')
                
                try:
                    result = future.result()
                    if result:
                        dir_path, line_count = result
                        all_component_dirs.append(dir_path)
                        self.component_line_counts[dir_path] = line_count
                except Exception as e:
                    dir_path = future_to_dir[future]
                    self.log(f"Error processing {dir_path}: {e}")
        
        # Clear progress line
        print(" " * 100, end='\r')
        
        elapsed = time.time() - start_time
        print(f"✅ Scanned {total_dirs} directories in {elapsed:.1f}s ({total_dirs/elapsed:.1f} dirs/sec)")
        
        # Group directories by depth level (number of path parts from project root)
        self.component_dirs_by_depth = {}
        for component_dir in all_component_dirs:
            rel_path = component_dir.relative_to(self.project_root)
            depth = len(rel_path.parts)
            
            if depth not in self.component_dirs_by_depth:
                self.component_dirs_by_depth[depth] = []
            self.component_dirs_by_depth[depth].append(component_dir)
        
        # Sort directories within each depth level for consistent processing
        for depth in self.component_dirs_by_depth:
            self.component_dirs_by_depth[depth].sort()
        
        # Also maintain flat list for backward compatibility
        self.component_dirs = []
        for depth in sorted(self.component_dirs_by_depth.keys()):
            self.component_dirs.extend(self.component_dirs_by_depth[depth])
    
    def create_directory_strategies(self) -> dict:
        """Create documentation strategies based on directory analysis."""
        all_dirs = [str(d.relative_to(self.project_root)) for d in self.component_dirs]
        
        # Calculate statistics
        line_counts = list(self.component_line_counts.values())
        if line_counts:
            avg_lines = sum(line_counts) / len(line_counts)
            sorted_counts = sorted(line_counts, reverse=True)
            percentile_75 = sorted_counts[int(len(sorted_counts) * 0.25)] if len(sorted_counts) >= 4 else avg_lines
            percentile_50 = sorted_counts[int(len(sorted_counts) * 0.5)] if len(sorted_counts) >= 2 else avg_lines
        else:
            avg_lines = percentile_75 = percentile_50 = 0
        
        # Score and categorize directories
        dir_info = []
        for d in self.component_dirs:
            rel_path = d.relative_to(self.project_root)
            lines = self.component_line_counts.get(d, 0)
            
            # Calculate importance score
            score = 0
            reasons = []
            
            # Size factor
            if lines > percentile_75:
                score += 30
                reasons.append("large codebase")
            elif lines > percentile_50:
                score += 20
                reasons.append("substantial code")
            elif lines > avg_lines:
                score += 10
                reasons.append("above average size")
            
            # Depth factor (prefer shallower directories)
            depth = len(rel_path.parts)
            if depth == 1:
                score += 25
                reasons.append("top-level")
            elif depth == 2:
                score += 15
                reasons.append("second-level")
            elif depth == 3:
                score += 5
            
            # Name importance
            path_str = str(rel_path).lower()
            important_keywords = {
                'src': 20, 'lib': 20, 'core': 25, 'api': 20,
                'service': 15, 'model': 15, 'controller': 15,
                'handler': 15, 'manager': 15, 'util': 5, 'utils': 5,
                'helper': 5, 'common': 10, 'shared': 10,
                'main': 20, 'app': 20, 'server': 20, 'client': 20
            }
            
            for keyword, points in important_keywords.items():
                if keyword in path_str.split('/'):
                    score += points
                    reasons.append(f"'{keyword}' component")
                    break
            
            # Negative patterns
            if any(word in path_str for word in ['test', 'tests', 'mock', 'example', 'demo', 'sample']):
                score *= 0.5
                reasons = [r for r in reasons if r != "test/example code"]
                reasons.append("test/example code")
            
            dir_info.append({
                'path': str(rel_path),
                'lines': lines,
                'score': score,
                'depth': depth,
                'reasons': reasons
            })
        
        # Sort by score
        dir_info.sort(key=lambda x: x['score'], reverse=True)
        
        # Create strategies
        minimal_threshold = 50  # High score threshold
        smart_threshold = 25    # Medium score threshold
        
        minimal_dirs = [d['path'] for d in dir_info if d['score'] >= minimal_threshold]
        smart_dirs = [d['path'] for d in dir_info if d['score'] >= smart_threshold]
        
        # Ensure we have at least some directories in minimal/smart
        if len(minimal_dirs) < 5 and len(dir_info) >= 5:
            minimal_dirs = [d['path'] for d in dir_info[:5]]
        if len(smart_dirs) < 10 and len(dir_info) >= 10:
            smart_dirs = [d['path'] for d in dir_info[:10]]
        
        # Build reasoning
        minimal_reasons = []
        smart_reasons = []
        
        if minimal_dirs:
            top_dirs = dir_info[:len(minimal_dirs)]
            common_reasons = {}
            for d in top_dirs:
                for r in d['reasons']:
                    common_reasons[r] = common_reasons.get(r, 0) + 1
            top_reasons = sorted(common_reasons.items(), key=lambda x: x[1], reverse=True)[:3]
            minimal_reasons = [r[0] for r in top_reasons]
        
        if smart_dirs:
            top_dirs = dir_info[:len(smart_dirs)]
            common_reasons = {}
            for d in top_dirs:
                for r in d['reasons']:
                    common_reasons[r] = common_reasons.get(r, 0) + 1
            top_reasons = sorted(common_reasons.items(), key=lambda x: x[1], reverse=True)[:3]
            smart_reasons = [r[0] for r in top_reasons]
        
        return {
            "minimal": {
                "directories": minimal_dirs,
                "reasoning": f"Focus on {', '.join(minimal_reasons[:2])} directories",
                "count": len(minimal_dirs),
                "details": [d for d in dir_info if d['path'] in minimal_dirs]
            },
            "smart": {
                "directories": smart_dirs,
                "reasoning": f"Cover {', '.join(smart_reasons[:2])} with good architecture coverage",
                "count": len(smart_dirs),
                "details": [d for d in dir_info if d['path'] in smart_dirs]
            },
            "full": {
                "directories": all_dirs,
                "reasoning": "Document every directory containing code",
                "count": len(all_dirs),
                "details": dir_info
            }
        }
    
    
    def select_strategy(self, strategies: dict) -> str:
        """Present strategies to user and get their selection."""
        print("\n📊 Documentation Strategy Options")
        print("=================================\n")
        
        # Show each strategy
        for strategy_name in ['minimal', 'smart', 'full']:
            strategy = strategies.get(strategy_name, {})
            count = strategy.get('count', 0)
            reasoning = strategy.get('reasoning', '')
            
            print(f"📌 {strategy_name.upper()} Strategy ({count} directories)")
            print(f"   {reasoning}")
            
            if strategy_name != 'full' and 'directories' in strategy and 'details' in strategy:
                print("   Top directories:")
                for detail in strategy['details'][:10]:
                    reasons_str = ", ".join(detail['reasons'][:2])
                    print(f"     - {detail['path']} ({detail['lines']:,} lines, score: {detail['score']}, {reasons_str})")
                if len(strategy['directories']) > 10:
                    print(f"     ... and {len(strategy['directories']) - 10} more")
            print()
        
        # Get user choice
        while True:
            try:
                choice = input("🤔 Select strategy [minimal/smart/full/manual] (default: smart): ").strip().lower()
                if not choice:
                    choice = 'smart'
                if choice in ['minimal', 'smart', 'full']:
                    print(f"✅ Selected {choice.upper()} strategy")
                    return choice
                elif choice == 'manual':
                    print("✅ Selected MANUAL strategy - you'll choose directories interactively")
                    return choice
                else:
                    print("❌ Invalid choice. Please enter 'minimal', 'smart', 'full', or 'manual'")
            except KeyboardInterrupt:
                print("\n❌ Cancelled by user")
                sys.exit(1)
    
    def select_directories_manually(self) -> List[str]:
        """Let user manually select directories to document."""
        print("\n📂 Manual Directory Selection")
        print("============================")
        print("Review each directory and decide whether to document it.")
        print("Type 'y' to include, 'n' to skip, 'q' to finish selection\n")
        
        selected = []
        dir_info = []
        
        # Prepare directory info sorted by score
        for d in self.component_dirs:
            rel_path = d.relative_to(self.project_root)
            lines = self.component_line_counts.get(d, 0)
            dir_info.append({
                'path': d,
                'rel_path': str(rel_path),
                'lines': lines
            })
        
        # Sort by lines (descending) for better review order
        dir_info.sort(key=lambda x: x['lines'], reverse=True)
        
        for i, info in enumerate(dir_info):
            print(f"\n[{i+1}/{len(dir_info)}] {info['rel_path']} ({info['lines']:,} lines)")
            
            while True:
                choice = input("   Include? [y/n/q]: ").strip().lower()
                if choice == 'y':
                    selected.append(info['rel_path'])
                    print("   ✅ Added to documentation")
                    break
                elif choice == 'n':
                    print("   ⏭️  Skipped")
                    break
                elif choice == 'q':
                    print("\n✅ Manual selection complete")
                    return selected
                else:
                    print("   ❌ Please enter 'y', 'n', or 'q'")
        
        print(f"\n✅ Manual selection complete: {len(selected)} directories selected")
        return selected

    def apply_strategy(self, strategy_name: str, strategies: dict):
        """Apply the selected strategy to filter component directories."""
        if strategy_name == 'full':
            # Keep all directories
            return
        elif strategy_name == 'manual':
            # Manual selection
            selected_paths = self.select_directories_manually()
            selected_dirs = set()
            for path_str in selected_paths:
                dir_path = self.project_root / path_str
                if dir_path in self.component_dirs:
                    selected_dirs.add(dir_path)
        else:
            # Use predefined strategy
            strategy = strategies.get(strategy_name, {})
            selected_dirs = set()
            for dir_str in strategy.get('directories', []):
                dir_path = self.project_root / dir_str
                if dir_path in self.component_dirs:
                    selected_dirs.add(dir_path)
        
        # Update component directories
        self.component_dirs = sorted(list(selected_dirs))
        
        # Rebuild depth grouping
        self.component_dirs_by_depth = {}
        for component_dir in self.component_dirs:
            rel_path = component_dir.relative_to(self.project_root)
            depth = len(rel_path.parts)
            
            if depth not in self.component_dirs_by_depth:
                self.component_dirs_by_depth[depth] = []
            self.component_dirs_by_depth[depth].append(component_dir)
        
        # Sort directories within each depth level
        for depth in self.component_dirs_by_depth:
            self.component_dirs_by_depth[depth].sort()

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
            print(f"📦 Components ({len(self.component_dirs)} directories - processed by depth):")
            print()
            
            for depth in sorted(self.component_dirs_by_depth.keys()):
                depth_dirs = self.component_dirs_by_depth[depth]
                print(f"   📂 Depth {depth} ({len(depth_dirs)} directories):")
                
                for i, component_dir in enumerate(depth_dirs):
                    rel_path = component_dir.relative_to(self.project_root)
                    lines = self.component_line_counts.get(component_dir, 0)
                    
                    prefix = "   └──" if i == len(depth_dirs) - 1 else "   ├──"
                    print(f"   {prefix} {rel_path}/ ({lines:,} lines)")
                    print(f"       └── CLAUDE.md + CURSOR.mdc")
                print()
        
        print()
        print("📊 Summary:")
        print("   • Will create 1 project root with .cursor/rules/ structure")
        print(f"   • Will create CLAUDE.md + CURSOR.mdc in {len(self.component_dirs)} component directories")
        print("   • Components will be processed by depth level (deepest first)")
        print("   • Each CURSOR.mdc includes glob patterns for auto-attachment")
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
    
    def setup_cursor_structure(self) -> bool:
        """Create .cursor directory structure and symbolic links."""
        if self.dry_run:
            print("[DRY RUN] Would create .cursor directory structure and symlinks")
            return True
        
        cursor_dir = self.project_root / ".cursor"
        rules_dir = cursor_dir / "rules"
        
        try:
            # Create .cursor/rules directory
            print("📁 Creating .cursor directory structure...")
            cursor_dir.mkdir(exist_ok=True)
            rules_dir.mkdir(exist_ok=True)
            
            # Create basic rule template files if they don't exist
            rule_templates = {
                "project_architecture.mdc": """# Project Architecture

This file contains project-specific architecture guidelines and patterns.

## Overview
- Project structure and organization
- Module dependencies and relationships
- Key architectural decisions

## Guidelines
- Follow established patterns in the codebase
- Maintain consistency with existing architecture
- Document significant architectural changes

_This file will be auto-generated and customized by Claude AI._
""",
                "code_standards.mdc": """# Code Standards

This file defines coding standards and conventions for this project.

## Code Style
- Follow language-specific best practices
- Maintain consistency with existing code
- Use meaningful names for variables and functions

## Documentation
- Document public APIs and interfaces
- Include examples where helpful
- Keep documentation up to date

_This file will be auto-generated and customized by Claude AI._
""",
                "development_workflow.mdc": """# Development Workflow

This file outlines the development workflow and processes for this project.

## Workflow
- Feature branch development
- Code review requirements
- Testing standards

## Tools and Processes
- Build and deployment procedures
- Quality assurance practices
- Change management

_This file will be auto-generated and customized by Claude AI._
"""
            }
            
            for filename, content in rule_templates.items():
                rule_file = rules_dir / filename
                if not rule_file.exists():
                    print(f"   📝 Creating rule template: {filename}")
                    rule_file.write_text(content)
                else:
                    print(f"   📝 Rule file already exists: {filename}")
            
            # Create symbolic links
            symlinks = [
                ("llms", ".cursor"),
                (".roo", ".cursor"), 
                ("ai_docs", ".cursor")
            ]
            
            for link_name, target in symlinks:
                link_path = self.project_root / link_name
                
                # Remove existing link/file if it exists
                if link_path.exists() or link_path.is_symlink():
                    if link_path.is_symlink():
                        print(f"   🔗 Removing existing symlink: {link_name}")
                        link_path.unlink()
                    elif link_path.is_dir():
                        print(f"   ⚠️  Directory {link_name} already exists, skipping symlink creation")
                        continue
                    else:
                        print(f"   ⚠️  File {link_name} already exists, skipping symlink creation")
                        continue
                
                # Create the symbolic link
                print(f"   🔗 Creating symlink: {link_name} -> {target}")
                link_path.symlink_to(target)
            
            print("   ✅ Directory structure and symlinks created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create directory structure: {e}")
            return False
    
    def execute_claude_command(self, command: str, component_name: str, working_dir: Optional[Path] = None) -> bool:
        """Execute a claude command with parameters, optionally from a specific working directory."""
        cmd = [
            "claude", "-p", "--dangerously-skip-permissions",
            "--verbose", "--output-format", "stream-json",
            f"/{command}"
        ]
        print(f"Executing: {' '.join(cmd)}")
        if working_dir:
            print(f"Working directory: {working_dir}")
        return self.execute_command(cmd, component_name, working_dir)
    
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
        print(f"   🧵 Max workers used: {self.max_workers}")
        
        if total_tokens > 0:
            avg_cost_per_token = total_cost / total_tokens * 1000  # Cost per 1K tokens
            print(f"   📊 Avg cost/1K tokens: ${avg_cost_per_token:.4f}")
        
        if successful_tasks > 0 and total_duration > 0:
            avg_time_per_task = total_duration / successful_tasks
            print(f"   ⚡ Avg time per task: {avg_time_per_task:.1f}s")
        
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
        
        self.find_component_directories()
        
        # Strategy selection
        print()
        total_lines = sum(self.component_line_counts.values())
        print(f"📊 Found {len(self.component_dirs)} directories with {total_lines:,} total lines of code.")
        print("Let's choose a documentation strategy.")
        print()
        
        # Create and select strategy
        print("📊 Analyzing project structure...")
        strategies = self.create_directory_strategies()
        selected_strategy = self.select_strategy(strategies)
        self.apply_strategy(selected_strategy, strategies)
        print()
        
        self.show_plan()
        
        # Confirmation
        if not self.confirm_execution():
            return False
        
        print()
        
        # Setup .cursor directory structure and symlinks first
        if not self.setup_cursor_structure():
            return False
        
        print()
        
        # Execute component initialization depth by depth
        if self.component_dirs:
            print(f"📦 Processing components by depth (deepest first) using {self.max_workers} threads...")
            print()
            
            total_dirs = len(self.component_dirs)
            processed_dirs = 0
            failed_dirs = []
            
            for depth in sorted(self.component_dirs_by_depth.keys(), reverse=True):
                depth_dirs = self.component_dirs_by_depth[depth]
                print(f"🔄 Processing depth {depth} ({len(depth_dirs)} directories)...")
                
                # Process directories at this depth in parallel
                start_time = time.time()
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Create tasks for each directory
                    future_to_dir = {}
                    for component_dir in depth_dirs:
                        rel_path = component_dir.relative_to(self.project_root)
                        rel_project_root = os.path.relpath(self.project_root, component_dir)
                        
                        future = executor.submit(
                            self.execute_claude_command,
                            f"user:init-component-ai-docs project-root={rel_project_root},component-dir=.",
                            str(rel_path),
                            working_dir=component_dir
                        )
                        future_to_dir[future] = component_dir
                    
                    # Process completed tasks
                    for future in as_completed(future_to_dir):
                        processed_dirs += 1
                        component_dir = future_to_dir[future]
                        rel_path = component_dir.relative_to(self.project_root)
                        
                        try:
                            success = future.result()
                            if not success:
                                failed_dirs.append(str(rel_path))
                                print(f"   ❌ Failed: {rel_path}")
                        except Exception as e:
                            failed_dirs.append(str(rel_path))
                            print(f"   ❌ Error processing {rel_path}: {e}")
                        
                        # Show progress - don't overwrite on every update to see failures
                        if processed_dirs % 5 == 0 or processed_dirs == total_dirs:
                            elapsed = time.time() - start_time
                            # Clear the line and print progress
                            print(" " * 80, end='\r')
                            print(f"   Progress: {processed_dirs}/{total_dirs} ({processed_dirs/total_dirs*100:.1f}%)", end='\r')
                
                elapsed = time.time() - start_time
                print(f"✅ Completed depth {depth} in {elapsed:.1f}s")
                print()
            
            if failed_dirs:
                print(f"\n⚠️  {len(failed_dirs)} directories failed to process:")
                for dir_path in failed_dirs[:10]:
                    print(f"   - {dir_path}")
                if len(failed_dirs) > 10:
                    print(f"   ... and {len(failed_dirs) - 10} more")
                return False
        
        # Execute project root initialization last
        print("📋 Initializing project-level documentation...")
        success = self.execute_claude_command(
            f"user:init-project-ai-docs project-root={self.project_root}",
            "Project Root",
            working_dir=self.project_root
        )
        
        if not success:
            return False
        
        print()
        
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

  # Run with 20 parallel threads for faster execution
  %(prog)s --max-workers 20
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
    
    parser.add_argument(
        "-w", "--max-workers",
        type=int,
        default=1,
        help="Maximum number of concurrent threads (default: 1). Warning: enabling more than 1 worker may cause a race condition with Claude Code. Use with caution."
    )
    
    args = parser.parse_args()
    
    # Initialize and run
    initializer = DocumentationInitializer(
        project_root=args.project_root,
        dry_run=args.dry_run,
        verbose=args.verbose,
        max_workers=args.max_workers
    )
    
    success = initializer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()