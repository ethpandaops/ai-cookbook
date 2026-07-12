"""
Codebase Analyzer Agent

Downloads and analyzes the client implementation to find BAL-related code.
Uses Claude Agent SDK for intelligent code analysis and extraction.
"""

import os
import sys
import tempfile
import subprocess
import shutil
from typing import Optional, Dict, List, Tuple
from pathlib import Path

try:
    import anyio
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False

from .shared_context import CodebaseContext, CodeSection


# Client repository mapping
CLIENT_REPOS = {
    "nethermind": "https://github.com/NethermindEth/nethermind.git",
    "besu": "https://github.com/hyperledger/besu.git",
    "geth": "https://github.com/ethereum/go-ethereum.git",
    "erigon": "https://github.com/ledgerwatch/erigon.git",
    "reth": "https://github.com/paradigmxyz/reth.git",
}


def parse_client_from_extra_data(extra_data: str) -> Tuple[str, str]:
    """
    Parse client name and version from block extraData field.

    Returns:
        (client_name, version)
    """
    if not extra_data or extra_data == "0x":
        return ("unknown", "unknown")

    try:
        # Remove 0x prefix and decode hex to string
        hex_data = extra_data[2:] if extra_data.startswith("0x") else extra_data
        text = bytes.fromhex(hex_data).decode('utf-8', errors='ignore').strip()

        # Parse common formats
        text_lower = text.lower()

        if "nethermind" in text_lower:
            # Nethermind format: "Nethermind v1.35.0a"
            parts = text.split()
            version = parts[1] if len(parts) > 1 else "unknown"
            return ("nethermind", version.lstrip('v'))
        elif "besu" in text_lower:
            # Besu format: "besu/v24.1.0"
            parts = text.split('/')
            version = parts[1] if len(parts) > 1 else "unknown"
            return ("besu", version.lstrip('v'))
        elif "geth" in text_lower or "go-ethereum" in text_lower:
            # Geth format: various
            return ("geth", "unknown")
        elif "erigon" in text_lower:
            return ("erigon", "unknown")
        elif "reth" in text_lower:
            return ("reth", "unknown")
        else:
            return ("unknown", text[:50])  # Return truncated text as version

    except Exception as e:
        print(f"Warning: Could not parse extraData: {e}", file=sys.stderr)
        return ("unknown", "unknown")


def clone_repository(client_name: str, branch: str = "bal-devnet-0") -> Tuple[Optional[str], Optional[str]]:
    """
    Clone the client repository to a temporary directory.

    Returns:
        (repo_path, error_message)
    """
    if client_name not in CLIENT_REPOS:
        return (None, f"Unknown client: {client_name}")

    repo_url = CLIENT_REPOS[client_name]

    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"baloor_{client_name}_")

        print(f"  Cloning {client_name} repository from {repo_url}...", file=sys.stderr)
        print(f"  Target branch: {branch}", file=sys.stderr)
        print(f"  Destination: {temp_dir}", file=sys.stderr)

        # Clone with depth 1 for faster download, specific branch
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, repo_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            error = result.stderr
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            return (None, f"Git clone failed: {error}")

        print(f"  Repository cloned successfully", file=sys.stderr)
        return (temp_dir, None)

    except subprocess.TimeoutExpired:
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return (None, "Git clone timed out after 5 minutes")
    except Exception as e:
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return (None, f"Failed to clone repository: {str(e)}")


async def analyze_codebase_with_ai(
    repo_path: str,
    client_name: str,
    bal_files: List[str],
) -> Dict[str, List[CodeSection]]:
    """
    Use Claude Agent SDK to analyze the codebase and extract relevant code sections.

    Returns dict with keys: journal_code, snapshot_restore_code, sload_sstore_tracking, revert_handling_code
    """
    if not CLAUDE_SDK_AVAILABLE:
        return {
            "journal_code": [],
            "snapshot_restore_code": [],
            "sload_sstore_tracking": [],
            "revert_handling_code": [],
        }

    # Read the BAL-related files
    file_contents = {}
    for file_path in bal_files[:10]:  # Limit to 10 files to avoid context overflow
        full_path = os.path.join(repo_path, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Limit file size to 10k chars to manage context
                if len(content) > 10000:
                    content = content[:10000] + "\n... (truncated)"
                file_contents[file_path] = content
        except Exception as e:
            print(f"    Warning: Could not read {file_path}: {e}", file=sys.stderr)

    if not file_contents:
        return {
            "journal_code": [],
            "snapshot_restore_code": [],
            "sload_sstore_tracking": [],
            "revert_handling_code": [],
        }

    # Build analysis prompt
    prompt_parts = [
        f"# Codebase Analysis Request",
        f"",
        f"You are analyzing the {client_name} Ethereum client implementation for EIP-7928 Block Access Lists (BAL).",
        f"",
        f"## Task",
        f"Extract and categorize key code sections related to BAL implementation. Focus on:",
        f"",
        f"1. **Journal/Change Tracking Code**: Code that records state changes to a journal/change stack",
        f"2. **Snapshot/Restore Code**: Code that creates snapshots and restores state on revert",
        f"3. **SLOAD/SSTORE Tracking**: Code that tracks storage read (SLOAD) and write (SSTORE) operations",
        f"4. **Revert Handling**: Code that handles transaction reverts and rollbacks",
        f"",
        f"## Files to Analyze",
        f"",
    ]

    for file_path, content in file_contents.items():
        prompt_parts.extend([
            f"### {file_path}",
            f"```",
            f"{content}",
            f"```",
            f"",
        ])

    prompt_parts.extend([
        f"## Output Format",
        f"",
        f"For each code section you identify, provide:",
        f"",
        f"```",
        f"FILE: <file_path>",
        f"LINES: <start_line>-<end_line>",
        f"CATEGORY: [journal | snapshot_restore | sload_sstore | revert_handling]",
        f"DESCRIPTION: <brief description>",
        f"RELEVANCE: <why this is relevant to BAL bugs>",
        f"CODE:",
        f"<the actual code snippet>",
        f"---",
        f"```",
        f"",
        f"Provide 2-3 most relevant sections per category. Be concise.",
    ])

    prompt = "\n".join(prompt_parts)

    options = ClaudeAgentOptions(
        max_turns=2,
        system_prompt=(
            "You are an expert in Ethereum client implementations and EVM state management. "
            "Identify and extract the most relevant code sections for BAL implementation analysis. "
            "Focus on journal/change tracking, snapshot/restore mechanisms, and SLOAD/SSTORE operations."
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
        print(f"    Warning: AI codebase analysis failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {
            "journal_code": [],
            "snapshot_restore_code": [],
            "sload_sstore_tracking": [],
            "revert_handling_code": [],
        }

    full_response = "\n".join(response_text)

    # Debug: print first 500 chars of response
    print(f"    AI response preview (first 500 chars):", file=sys.stderr)
    print(f"    {full_response[:500]}", file=sys.stderr)

    # Parse the response to extract code sections
    return parse_code_sections(full_response)


def parse_code_sections(response: str) -> Dict[str, List[CodeSection]]:
    """Parse AI response into structured code sections."""
    sections = {
        "journal_code": [],
        "snapshot_restore_code": [],
        "sload_sstore_tracking": [],
        "revert_handling_code": [],
    }

    # Simple parser for the structured output
    current_section = {}
    in_code_block = False
    code_lines = []

    for line in response.split('\n'):
        line = line.strip()

        if line.startswith("FILE:"):
            current_section["file_path"] = line.replace("FILE:", "").strip()
        elif line.startswith("LINES:"):
            line_range = line.replace("LINES:", "").strip()
            if '-' in line_range:
                start, end = line_range.split('-')
                current_section["start_line"] = int(start.strip())
                current_section["end_line"] = int(end.strip())
        elif line.startswith("CATEGORY:"):
            category = line.replace("CATEGORY:", "").strip().lower()
            category_map = {
                "journal": "journal_code",
                "snapshot_restore": "snapshot_restore_code",
                "sload_sstore": "sload_sstore_tracking",
                "revert_handling": "revert_handling_code",
            }
            current_section["category"] = category_map.get(category)
        elif line.startswith("DESCRIPTION:"):
            current_section["description"] = line.replace("DESCRIPTION:", "").strip()
        elif line.startswith("RELEVANCE:"):
            current_section["relevance"] = line.replace("RELEVANCE:", "").strip()
        elif line.startswith("CODE:"):
            in_code_block = True
            code_lines = []
        elif line == "---":
            # End of section
            if in_code_block and current_section.get("category"):
                current_section["code"] = "\n".join(code_lines)

                section = CodeSection(
                    file_path=current_section.get("file_path", "unknown"),
                    start_line=current_section.get("start_line", 0),
                    end_line=current_section.get("end_line", 0),
                    code=current_section.get("code", ""),
                    description=current_section.get("description", ""),
                    relevance=current_section.get("relevance", ""),
                )

                category = current_section["category"]
                sections[category].append(section)

            # Reset
            current_section = {}
            in_code_block = False
            code_lines = []
        elif in_code_block:
            code_lines.append(line)

    return sections


def run_codebase_analysis(
    repo_path: str,
    client_name: str,
) -> Tuple[List[str], Dict[str, List[CodeSection]]]:
    """
    Run synchronous wrapper for codebase analysis.

    Returns:
        (bal_files, code_sections_dict)
    """
    # Search for BAL-related files
    print(f"  Searching for BAL implementation files...", file=sys.stderr)

    bal_files = []
    search_patterns = [
        "BlockAccessList",
        "StorageRead",
        "StorageChange",
        "BalanceChange",
        "NonceChange",
        "CodeChange",
        "balHash",
        "BAL",
    ]

    # Use simple file search (could be enhanced with ripgrep/ast-grep)
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'vendor', 'test', 'tests']]

        for file in files:
            # Focus on source files
            if file.endswith(('.cs', '.go', '.rs', '.java', '.cpp', '.c', '.h')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Check if file contains any of our search patterns
                        if any(pattern in content for pattern in search_patterns):
                            rel_path = os.path.relpath(file_path, repo_path)
                            bal_files.append(rel_path)
                            print(f"    Found: {rel_path}", file=sys.stderr)
                except Exception:
                    pass

    print(f"  Found {len(bal_files)} BAL-related files", file=sys.stderr)

    # Read the most relevant files directly
    print(f"  Reading key implementation files...", file=sys.stderr)

    code_sections_dict = {
        "journal_code": [],
        "snapshot_restore_code": [],
        "sload_sstore_tracking": [],
        "revert_handling_code": [],
    }

    # Prioritize most relevant files
    priority_patterns = {
        "sload_sstore_tracking": ["EvmInstructions.Storage.cs", "TracedAccessWorldState.cs"],
        "snapshot_restore_code": ["Snapshot.cs", "StateProvider.cs"],
        "journal_code": ["BlockProcessor", "TransactionProcessor"],
    }

    for category, patterns in priority_patterns.items():
        for pattern in patterns:
            matching_files = [f for f in bal_files if pattern in f]
            for file_path in matching_files[:2]:  # Max 2 files per pattern
                full_path = os.path.join(repo_path, file_path)
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Extract relevant sections (simple approach: take first 3000 chars)
                        code_section = CodeSection(
                            file_path=file_path,
                            start_line=1,
                            end_line=min(100, content.count('\n')),
                            code=content[:3000],  # First 3000 chars
                            description=f"Key implementation file for {category}",
                            relevance=f"Contains {pattern} which is central to BAL implementation"
                        )
                        code_sections_dict[category].append(code_section)
                        print(f"    Read: {file_path} ({len(content)} chars)", file=sys.stderr)
                except Exception as e:
                    print(f"    Warning: Could not read {file_path}: {e}", file=sys.stderr)

    total_sections = sum(len(sections) for sections in code_sections_dict.values())
    print(f"  Extracted {total_sections} code sections", file=sys.stderr)

    return (bal_files, code_sections_dict)


def analyze_codebase(block_entry: Dict, branch: str = "bal-devnet-0") -> CodebaseContext:
    """
    Main entry point for codebase analysis.

    Args:
        block_entry: Block data from bad_blocks.json
        branch: Git branch to checkout (default: bal-devnet-0)

    Returns:
        CodebaseContext with analysis results
    """
    # Extract client info from extraData
    extra_data = block_entry.get('block', {}).get('extraData', '0x')
    client_name, client_version = parse_client_from_extra_data(extra_data)

    print(f"\nCodebase Analyzer Agent:", file=sys.stderr)
    print(f"  Detected client: {client_name} {client_version}", file=sys.stderr)

    # Create initial context
    context = CodebaseContext(
        client_name=client_name,
        client_version=client_version,
        branch=branch,
        repo_url=CLIENT_REPOS.get(client_name, ""),
        repo_path=None,
    )

    # Clone repository
    if client_name == "unknown":
        context.clone_success = False
        context.clone_error = "Unknown client, cannot clone repository"
        print(f"  Skipping clone: {context.clone_error}", file=sys.stderr)
        return context

    repo_path, clone_error = clone_repository(client_name, branch)

    if clone_error:
        context.clone_success = False
        context.clone_error = clone_error
        print(f"  Clone failed: {clone_error}", file=sys.stderr)
        return context

    context.repo_path = repo_path

    try:
        # Analyze the codebase
        bal_files, code_sections = run_codebase_analysis(repo_path, client_name)

        context.bal_implementation_files = bal_files
        context.journal_code = code_sections.get("journal_code", [])
        context.snapshot_restore_code = code_sections.get("snapshot_restore_code", [])
        context.sload_sstore_tracking = code_sections.get("sload_sstore_tracking", [])
        context.revert_handling_code = code_sections.get("revert_handling_code", [])

        # Generate architecture notes
        context.architecture_notes = f"Analyzed {client_name} implementation with {len(bal_files)} BAL-related files."

        print(f"  Codebase analysis complete", file=sys.stderr)

    except Exception as e:
        context.search_warnings.append(f"Analysis error: {str(e)}")
        print(f"  Warning: {str(e)}", file=sys.stderr)

    return context
