"""
Baloor - Block Access List Comparison and Analysis Tool

A comprehensive toolkit for comparing and analyzing Block Access Lists (BALs)
from Teku's debug endpoint, identifying differences between incoming blocks
and Besu generated BALs.

Based on EIP-7928: Block-Level Access Lists
"""

# Import main CLI entry point
from .cli import main

# Import key models for external use
from .models import (
    StorageChangeDiff,
    AccountDiff,
    TransactionInfo,
    TransactionContext,
    BALReport,
    Pattern,
)

# Import utilities
from .utils import (
    normalize_hex,
    shorten_hex,
    decode_client_from_extra_data,
    rpc_call,
    fetch_bad_blocks_from_besu,
    fetch_block_by_number,
    fetch_block_by_hash,
    fetch_transaction_receipt,
    debug_trace_transaction,
)

# Import comparison functions
from .comparisons import (
    compare_storage_changes,
    compare_reads,
    compare_indexed_changes,
    compare_account,
    parse_transaction_context,
    compare_block,
)

# Import analysis functions
from .analysis import (
    fetch_eip_7928,
    fetch_test_files,
    ai_analyze_differences,
    run_ai_analysis,
    analyze_storage_changes,
    analyze_balance_changes,
    analyze_nonce_changes,
    analyze_code_changes,
    analyze_storage_reads,
    analyze_account_presence,
    detect_patterns,
    run_multi_agent_analysis,
)

# Import formatters
from .formatters import (
    format_standard_report,
    format_diff_report,
    format_debug_card,
    format_insights_report,
    format_multi_block_analysis,
    format_comprehensive_report,
)

__version__ = "1.0.0"
__all__ = [
    # CLI
    "main",
    # Models
    "StorageChangeDiff",
    "AccountDiff",
    "TransactionInfo",
    "TransactionContext",
    "BALReport",
    "Pattern",
    # Utils
    "normalize_hex",
    "shorten_hex",
    "decode_client_from_extra_data",
    "rpc_call",
    "fetch_bad_blocks_from_besu",
    "fetch_block_by_number",
    "fetch_block_by_hash",
    "fetch_transaction_receipt",
    "debug_trace_transaction",
    # Comparisons
    "compare_storage_changes",
    "compare_reads",
    "compare_indexed_changes",
    "compare_account",
    "parse_transaction_context",
    "compare_block",
    # Analysis
    "fetch_eip_7928",
    "fetch_test_files",
    "ai_analyze_differences",
    "run_ai_analysis",
    "analyze_storage_changes",
    "analyze_balance_changes",
    "analyze_nonce_changes",
    "analyze_code_changes",
    "analyze_storage_reads",
    "analyze_account_presence",
    "detect_patterns",
    "run_multi_agent_analysis",
    # Formatters
    "format_standard_report",
    "format_diff_report",
    "format_debug_card",
    "format_insights_report",
    "format_multi_block_analysis",
    "format_comprehensive_report",
]
