"""
Shared context data structures for inter-agent communication.

These models enable the three agents to pass structured information:
- Codebase Analyzer → CodebaseContext
- Difference Analyzer → DifferenceContext
- Both contexts → Report Generator
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class TxResult(Enum):
    """Transaction execution result."""
    SUCCESS = "success"
    REVERT = "revert"
    OUT_OF_GAS = "out_of_gas"
    UNKNOWN = "unknown"


class Operation(Enum):
    """EVM operations relevant to BAL."""
    SLOAD = "SLOAD"
    SSTORE = "SSTORE"
    BALANCE = "BALANCE"
    EXTCODESIZE = "EXTCODESIZE"
    EXTCODEHASH = "EXTCODEHASH"
    EXTCODECOPY = "EXTCODECOPY"
    CALL = "CALL"
    STATICCALL = "STATICCALL"
    DELEGATECALL = "DELEGATECALL"
    CALLCODE = "CALLCODE"
    CREATE = "CREATE"
    CREATE2 = "CREATE2"
    SELFDESTRUCT = "SELFDESTRUCT"


@dataclass
class CodeSection:
    """A section of code from the client implementation."""
    file_path: str
    start_line: int
    end_line: int
    code: str
    description: str
    relevance: str  # Why this code is relevant to the bug


@dataclass
class CodebaseContext:
    """Context from analyzing the client codebase."""
    client_name: str
    client_version: str
    branch: str
    repo_url: str
    repo_path: Optional[str]  # Local path if cloned successfully

    # Code sections found
    bal_implementation_files: List[str] = field(default_factory=list)
    journal_code: List[CodeSection] = field(default_factory=list)
    snapshot_restore_code: List[CodeSection] = field(default_factory=list)
    sload_sstore_tracking: List[CodeSection] = field(default_factory=list)
    revert_handling_code: List[CodeSection] = field(default_factory=list)

    # Architecture notes
    architecture_notes: str = ""

    # Errors/warnings
    clone_success: bool = True
    clone_error: Optional[str] = None
    search_warnings: List[str] = field(default_factory=list)


@dataclass
class OperationSequence:
    """A sequence of operations on an account/slot in a transaction."""
    tx_index: int
    tx_hash: str
    account: str
    slot: Optional[str]  # None for account-level operations

    operations: List[Operation] = field(default_factory=list)
    tx_result: TxResult = TxResult.UNKNOWN

    # Expected BAL state
    expected_in_storage_reads: bool = False
    expected_in_storage_changes: bool = False
    expected_in_balance_changes: bool = False
    expected_in_nonce_changes: bool = False
    expected_in_code_changes: bool = False

    # Actual BAL state
    actual_in_block_bal: Dict[str, bool] = field(default_factory=dict)
    actual_in_generated_bal: Dict[str, bool] = field(default_factory=dict)

    # Mismatch flags
    has_mismatch: bool = False
    mismatch_description: str = ""


@dataclass
class PatternHypothesis:
    """A hypothesis about a pattern in the differences."""
    pattern_name: str
    description: str
    confidence: str  # "high", "medium", "low"
    supporting_evidence: List[str] = field(default_factory=list)
    affected_accounts: List[str] = field(default_factory=list)
    affected_transactions: List[int] = field(default_factory=list)


@dataclass
class DifferenceContext:
    """Context from deep analysis of BAL differences."""

    # Operation sequences for all affected accounts/transactions
    operation_sequences: List[OperationSequence] = field(default_factory=list)

    # Account categorization
    tx_participant_accounts: List[str] = field(default_factory=list)
    opcode_accessed_accounts: List[str] = field(default_factory=list)
    special_addresses: List[str] = field(default_factory=list)  # 0x0, precompiles, etc.

    # Cross-reference analysis
    read_write_mismatches: List[Dict[str, Any]] = field(default_factory=list)

    # Pattern detection
    detected_patterns: List[PatternHypothesis] = field(default_factory=list)

    # Summary statistics
    total_affected_accounts: int = 0
    total_affected_transactions: int = 0
    total_missing_in_block_bal: int = 0
    total_extra_in_block_bal: int = 0

    # Raw data references
    has_storage_read_diffs: bool = False
    has_storage_change_diffs: bool = False
    has_balance_diffs: bool = False
    has_nonce_diffs: bool = False
    has_code_diffs: bool = False


@dataclass
class JournalInvariant:
    """Definition of a journal invariant and its violation."""
    name: str
    description: str
    eip_reference: str  # Quote from EIP-7928

    # Invariant definition
    condition: str  # When this invariant applies
    requirement: str  # What must be journaled

    # Violation details
    is_violated: bool = False
    violation_description: str = ""
    affected_code: Optional[CodeSection] = None

    # Fix guidance
    fix_approach: str = ""


@dataclass
class ImplementationPane:
    """A structured view of the fix with multiple perspectives."""

    # Conceptual diff
    diff_description: str
    incorrect_pattern: str  # Code example showing the bug
    correct_pattern: str  # Code example showing the fix

    # Narrative explanation
    narrative: str

    # Invariant guarantee
    invariant_guarantee: str  # What invariant this fix ensures

    # Testing recommendations
    regression_tests: List[str] = field(default_factory=list)
    edge_cases: List[str] = field(default_factory=list)

    # Risk analysis
    consensus_impact: bool = False
    db_migration_needed: bool = False
    hash_invariant_changes: bool = False
    performance_impact: str = "none"  # "none", "low", "medium", "high"
