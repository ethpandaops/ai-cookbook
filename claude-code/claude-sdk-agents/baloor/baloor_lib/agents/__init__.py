"""
Multi-agent system for BAL (Block Access List) analysis.

This package implements a sophisticated three-agent system for analyzing
BAL inconsistencies between different Ethereum client implementations:

1. Codebase Analyzer Agent - Downloads and analyzes client implementation code
2. Difference Analyzer Agent - Deep analysis of BAL differences
3. Report Generator Agent - Synthesizes findings into comprehensive reports

The multi-agent approach enables:
- Deeper root cause analysis by examining actual implementation code
- Systematic pattern detection across operation sequences
- World-class bug reports following journal invariant methodology
- Actionable debugging recommendations with specific file/line references
"""

from .orchestrator import run_multi_agent_analysis, MultiAgentOrchestrator
from .shared_context import (
    CodebaseContext,
    DifferenceContext,
    JournalInvariant,
    ImplementationPane,
    OperationSequence,
)
from .bal_root_cause_agent import BALRootCauseAnalyzer, analyze_bal_report

__all__ = [
    "run_multi_agent_analysis",
    "MultiAgentOrchestrator",
    "CodebaseContext",
    "DifferenceContext",
    "JournalInvariant",
    "ImplementationPane",
    "OperationSequence",
    "BALRootCauseAnalyzer",
    "analyze_bal_report",
]
