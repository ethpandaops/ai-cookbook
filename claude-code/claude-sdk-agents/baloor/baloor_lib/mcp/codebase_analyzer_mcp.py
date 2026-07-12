#!/usr/bin/env python3
"""
Codebase Analyzer MCP Server

An in-process MCP server that can clone repositories, search codebases,
and suggest fixes for bugs based on error analysis.

This server is designed to work with baloor.py to provide specific code-level
fixes for issues found in Block Access List analysis.
"""

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool,
)


class CodebaseAnalyzer:
    """Manages cloned repositories and provides code analysis capabilities."""

    def __init__(self):
        self.temp_dir = None
        self.repo_path = None
        self.repo_url = None
        self.current_branch = None

    def cleanup(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            self.repo_path = None

    async def clone_repo(self, repo_url: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """Clone a repository to a temporary directory."""
        # Cleanup any existing repo
        self.cleanup()

        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="codebase_analyzer_")
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        self.repo_path = os.path.join(self.temp_dir, repo_name)

        try:
            # Clone the repository
            cmd = ['git', 'clone', repo_url, self.repo_path]
            if branch:
                cmd.extend(['--branch', branch])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Git clone failed: {result.stderr}",
                    "repo_path": None
                }

            self.repo_url = repo_url
            self.current_branch = branch

            return {
                "success": True,
                "repo_path": self.repo_path,
                "repo_url": repo_url,
                "branch": branch or "default"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Clone operation timed out after 5 minutes",
                "repo_path": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Clone failed: {str(e)}",
                "repo_path": None
            }

    async def checkout_branch(self, branch: str) -> Dict[str, Any]:
        """Checkout a specific branch in the cloned repository."""
        if not self.repo_path or not os.path.exists(self.repo_path):
            return {
                "success": False,
                "error": "No repository cloned. Use clone_repository first."
            }

        try:
            result = subprocess.run(
                ['git', 'checkout', branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Checkout failed: {result.stderr}"
                }

            self.current_branch = branch
            return {
                "success": True,
                "branch": branch,
                "message": f"Successfully checked out branch: {branch}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Checkout failed: {str(e)}"
            }

    async def search_code(self, pattern: str, file_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Search for a pattern in the codebase using ripgrep."""
        if not self.repo_path or not os.path.exists(self.repo_path):
            return {
                "success": False,
                "error": "No repository cloned. Use clone_repository first.",
                "matches": []
            }

        try:
            cmd = ['rg', '--json', '--context', '3', pattern]
            if file_pattern:
                cmd.extend(['--glob', file_pattern])

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse ripgrep JSON output
            matches = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    import json
                    entry = json.loads(line)
                    if entry.get('type') == 'match':
                        data = entry.get('data', {})
                        matches.append({
                            'file': data.get('path', {}).get('text', ''),
                            'line_number': data.get('line_number'),
                            'line': data.get('lines', {}).get('text', '').rstrip('\n'),
                        })
                except json.JSONDecodeError:
                    continue

            return {
                "success": True,
                "pattern": pattern,
                "matches": matches,
                "total_matches": len(matches)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Search timed out after 60 seconds",
                "matches": []
            }
        except FileNotFoundError:
            # Fallback to grep if ripgrep not available
            try:
                cmd = ['grep', '-r', '-n', pattern]
                if file_pattern:
                    cmd.extend(['--include', file_pattern])
                cmd.append('.')

                result = subprocess.run(
                    cmd,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                matches = []
                for line in result.stdout.splitlines():
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        matches.append({
                            'file': parts[0],
                            'line_number': int(parts[1]) if parts[1].isdigit() else 0,
                            'line': parts[2]
                        })

                return {
                    "success": True,
                    "pattern": pattern,
                    "matches": matches,
                    "total_matches": len(matches)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Search failed: {str(e)}",
                    "matches": []
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "matches": []
            }

    async def read_file(self, file_path: str, start_line: Optional[int] = None,
                       end_line: Optional[int] = None) -> Dict[str, Any]:
        """Read a file from the cloned repository."""
        if not self.repo_path or not os.path.exists(self.repo_path):
            return {
                "success": False,
                "error": "No repository cloned. Use clone_repository first.",
                "content": None
            }

        full_path = os.path.join(self.repo_path, file_path)

        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "content": None
            }

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            if start_line is not None or end_line is not None:
                start_line = start_line or 1
                end_line = end_line or len(lines)
                lines = lines[start_line-1:end_line]

            return {
                "success": True,
                "file_path": file_path,
                "content": ''.join(lines),
                "line_count": len(lines)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}",
                "content": None
            }

    async def analyze_with_claude(self, context: str, question: str) -> str:
        """Use Claude to analyze code and provide insights."""
        prompt = f"""# Code Analysis Request

{context}

## Question
{question}

Please provide a concise, specific analysis focusing on:
1. The likely location of the bug
2. The root cause
3. A specific code fix with before/after examples
4. Any related code that should be reviewed

Use code blocks for examples and be specific about file paths and line numbers where possible.
"""

        options = ClaudeAgentOptions(
            max_turns=2,
            system_prompt=(
                "You are an expert code reviewer specializing in Ethereum client implementations. "
                "Provide specific, actionable analysis with code examples. "
                "Be concise but thorough."
            )
        )

        response_text = []
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text.append(block.text)
        except Exception as e:
            return f"Analysis failed: {str(e)}"

        return "\n".join(response_text) if response_text else "No analysis generated"


# Global analyzer instance
_analyzer = CodebaseAnalyzer()


# Define MCP tools

@tool("clone_repository",
      "Clone a git repository for analysis",
      {"repo_url": str, "branch": str})
async def clone_repository(args: Dict[str, Any]) -> Dict[str, Any]:
    """Clone a repository to analyze its code."""
    repo_url = args["repo_url"]
    branch = args.get("branch")

    result = await _analyzer.clone_repo(repo_url, branch)

    if result["success"]:
        return {
            "content": [{
                "type": "text",
                "text": f"Successfully cloned {repo_url}\nBranch: {result['branch']}\nPath: {result['repo_path']}"
            }]
        }
    else:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to clone repository: {result['error']}"
            }],
            "is_error": True
        }


@tool("checkout_branch",
      "Checkout a specific branch in the cloned repository",
      {"branch": str})
async def checkout_branch(args: Dict[str, Any]) -> Dict[str, Any]:
    """Checkout a specific branch."""
    branch = args["branch"]

    result = await _analyzer.checkout_branch(branch)

    if result["success"]:
        return {
            "content": [{
                "type": "text",
                "text": result["message"]
            }]
        }
    else:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to checkout branch: {result['error']}"
            }],
            "is_error": True
        }


@tool("search_code",
      "Search for a pattern in the codebase",
      {"pattern": str, "file_pattern": str})
async def search_code(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search the codebase for a specific pattern."""
    pattern = args["pattern"]
    file_pattern = args.get("file_pattern")

    result = await _analyzer.search_code(pattern, file_pattern)

    if result["success"]:
        if result["total_matches"] == 0:
            text = f"No matches found for pattern: {pattern}"
        else:
            text = f"Found {result['total_matches']} matches for pattern: {pattern}\n\n"
            # Limit to first 20 matches to avoid overwhelming output
            for match in result["matches"][:20]:
                text += f"{match['file']}:{match['line_number']}\n"
                text += f"  {match['line']}\n"

            if result["total_matches"] > 20:
                text += f"\n... and {result['total_matches'] - 20} more matches"

        return {
            "content": [{
                "type": "text",
                "text": text
            }]
        }
    else:
        return {
            "content": [{
                "type": "text",
                "text": f"Search failed: {result['error']}"
            }],
            "is_error": True
        }


@tool("read_file",
      "Read a file from the cloned repository",
      {"file_path": str, "start_line": int, "end_line": int})
async def read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read a specific file from the repository."""
    file_path = args["file_path"]
    start_line = args.get("start_line")
    end_line = args.get("end_line")

    result = await _analyzer.read_file(file_path, start_line, end_line)

    if result["success"]:
        return {
            "content": [{
                "type": "text",
                "text": f"File: {result['file_path']}\nLines: {result['line_count']}\n\n{result['content']}"
            }]
        }
    else:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to read file: {result['error']}"
            }],
            "is_error": True
        }


@tool("suggest_fix",
      "Analyze code and suggest a fix based on error context",
      {"error_description": str, "relevant_files": str, "error_pattern": str})
async def suggest_fix(args: Dict[str, Any]) -> Dict[str, Any]:
    """Use Claude to analyze code and suggest a fix."""
    error_description = args["error_description"]
    relevant_files = args.get("relevant_files", "")
    error_pattern = args.get("error_pattern", "")

    # Build context
    context = f"""## Error Description
{error_description}

## Relevant Files
{relevant_files}

## Error Pattern
{error_pattern}
"""

    question = """Based on this error, please:
1. Identify the likely file and function where the bug exists
2. Explain the root cause
3. Provide a specific code fix with before/after examples
4. Suggest any additional files that should be reviewed
"""

    analysis = await _analyzer.analyze_with_claude(context, question)

    return {
        "content": [{
            "type": "text",
            "text": f"## Code Analysis and Fix Suggestion\n\n{analysis}"
        }]
    }


def create_codebase_analyzer_server():
    """Create the codebase analyzer MCP server."""
    return create_sdk_mcp_server(
        name="codebase-analyzer",
        version="1.0.0",
        tools=[
            clone_repository,
            checkout_branch,
            search_code,
            read_file,
            suggest_fix,
        ],
    )


def cleanup():
    """Cleanup resources."""
    _analyzer.cleanup()


# Example usage
async def example_usage():
    """Example of using the codebase analyzer server."""
    server = create_codebase_analyzer_server()

    options = ClaudeAgentOptions(
        mcp_servers={"analyzer": server},
        allowed_tools=[
            "mcp__analyzer__clone_repository",
            "mcp__analyzer__checkout_branch",
            "mcp__analyzer__search_code",
            "mcp__analyzer__read_file",
            "mcp__analyzer__suggest_fix",
        ],
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            # Example: Analyze the nethermind repository
            await client.query(
                "Clone the nethermind repository from https://github.com/NethermindEth/nethermind.git "
                "and checkout the bal-devnet-0 branch"
            )

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text)
    finally:
        cleanup()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
