"""
Multi-Agent Orchestrator

Coordinates the execution of three specialized agents:
1. Codebase Analyzer - Downloads and analyzes client implementation
2. Difference Analyzer - Deep analysis of BAL differences
3. Report Generator - Synthesizes comprehensive bug report

The orchestrator runs agents 1 and 2 in parallel for efficiency,
then passes both contexts to agent 3 for final report generation.
"""

import sys
import asyncio
import shutil
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from ..models import BALReport
from .codebase_analyzer import analyze_codebase
from .difference_analyzer import analyze_differences
from .report_generator import generate_report
from .shared_context import CodebaseContext, DifferenceContext


class MultiAgentOrchestrator:
    """
    Orchestrates the multi-agent BAL analysis workflow.
    """

    def __init__(self, keep_repos: bool = False):
        """
        Initialize orchestrator.

        Args:
            keep_repos: If True, preserve cloned repositories for debugging
        """
        self.keep_repos = keep_repos
        self.codebase_ctx: Optional[CodebaseContext] = None
        self.diff_ctx: Optional[DifferenceContext] = None

    def cleanup(self):
        """Clean up resources (e.g., cloned repositories)."""
        if not self.keep_repos and self.codebase_ctx and self.codebase_ctx.repo_path:
            try:
                print(f"\nCleaning up cloned repository: {self.codebase_ctx.repo_path}", file=sys.stderr)
                shutil.rmtree(self.codebase_ctx.repo_path, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not clean up repository: {e}", file=sys.stderr)

    def run_parallel_analysis(
        self,
        report: BALReport,
        block_entry: Dict,
        branch: str = "bal-devnet-0"
    ) -> Tuple[CodebaseContext, DifferenceContext]:
        """
        Run codebase and difference analyzers in parallel.

        Returns:
            (CodebaseContext, DifferenceContext)
        """
        print("\n" + "=" * 80, file=sys.stderr)
        print("MULTI-AGENT BAL ANALYSIS", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

        # Run both agents in parallel using thread pool
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Launch both agents
            print("\nLaunching agents in parallel...", file=sys.stderr)

            codebase_future = executor.submit(analyze_codebase, block_entry, branch)
            diff_future = executor.submit(analyze_differences, report, block_entry)

            # Wait for both to complete
            codebase_ctx = codebase_future.result()
            diff_ctx = diff_future.result()

        return codebase_ctx, diff_ctx

    def run_analysis(
        self,
        report: BALReport,
        block_entry: Dict,
        eip_context: Optional[str] = None,
        test_files: Optional[Dict[str, Optional[str]]] = None,
        branch: str = "bal-devnet-0",
    ) -> str:
        """
        Run complete multi-agent analysis.

        Args:
            report: BAL comparison report
            block_entry: Raw block data from bad_blocks.json
            eip_context: EIP-7928 specification text
            test_files: EIP-7928 test suite files
            branch: Git branch to checkout (default: bal-devnet-0)

        Returns:
            Comprehensive bug report as markdown string
        """
        try:
            # Phase 1 & 2: Run codebase and difference analyzers in parallel
            self.codebase_ctx, self.diff_ctx = self.run_parallel_analysis(
                report, block_entry, branch
            )

            # Phase 3: Generate comprehensive report
            final_report = generate_report(
                report,
                self.codebase_ctx,
                self.diff_ctx,
                eip_context,
                test_files,
                block_entry,
            )

            print("\n" + "=" * 80, file=sys.stderr)
            print("MULTI-AGENT ANALYSIS COMPLETE", file=sys.stderr)
            print("=" * 80, file=sys.stderr)

            # Add metadata footer
            metadata_footer = [
                "",
                "---",
                "",
                "## Analysis Metadata",
                "",
                f"**Codebase Analysis**:",
                f"- Client: {self.codebase_ctx.client_name} {self.codebase_ctx.client_version}",
                f"- Repository: {self.codebase_ctx.repo_url}",
                f"- Branch: {self.codebase_ctx.branch}",
                f"- Clone successful: {self.codebase_ctx.clone_success}",
                f"- BAL files found: {len(self.codebase_ctx.bal_implementation_files)}",
                f"- Code sections extracted: {len(self.codebase_ctx.journal_code) + len(self.codebase_ctx.sload_sstore_tracking) + len(self.codebase_ctx.snapshot_restore_code) + len(self.codebase_ctx.revert_handling_code)}",
                "",
                f"**Difference Analysis**:",
                f"- Operation sequences: {len(self.diff_ctx.operation_sequences)}",
                f"- Read/write mismatches: {len(self.diff_ctx.read_write_mismatches)}",
                f"- Pattern hypotheses: {len(self.diff_ctx.detected_patterns)}",
                f"- Affected accounts: {self.diff_ctx.total_affected_accounts}",
                "",
                "**Report Generation**:",
                "- Method: Multi-agent with extended thinking",
                "- Agents: Codebase Analyzer, Difference Analyzer, Report Generator",
                "",
            ]

            return final_report + "\n".join(metadata_footer)

        finally:
            # Always cleanup unless keep_repos is True
            if not self.keep_repos:
                self.cleanup()


def run_multi_agent_analysis(
    report: BALReport,
    block_entry: Dict,
    eip_context: Optional[str] = None,
    test_files: Optional[Dict[str, Optional[str]]] = None,
    branch: str = "bal-devnet-0",
    keep_repos: bool = False,
) -> str:
    """
    Convenience function to run multi-agent analysis.

    Args:
        report: BAL comparison report
        block_entry: Raw block data from bad_blocks.json
        eip_context: EIP-7928 specification text
        test_files: EIP-7928 test suite files
        branch: Git branch to checkout (default: bal-devnet-0)
        keep_repos: If True, preserve cloned repositories for debugging

    Returns:
        Comprehensive bug report as markdown string
    """
    orchestrator = MultiAgentOrchestrator(keep_repos=keep_repos)

    return orchestrator.run_analysis(
        report=report,
        block_entry=block_entry,
        eip_context=eip_context,
        test_files=test_files,
        branch=branch,
    )
