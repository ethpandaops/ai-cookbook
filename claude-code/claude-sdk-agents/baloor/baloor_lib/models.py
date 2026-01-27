"""
Data models for Baloor - Block Access List Comparison and Analysis Tool

Contains all dataclasses used throughout the tool for representing
BAL differences, transaction context, and analysis patterns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class StorageChangeDiff:
    """Differences in storage changes for a specific slot."""
    slot: str
    missing_in_block: List[Dict[str, Any]] = field(default_factory=list)
    extra_in_block: List[Dict[str, Any]] = field(default_factory=list)
    value_differences: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AccountDiff:
    """All differences for a single account."""
    address: str
    storage_missing_slots: List[str] = field(default_factory=list)
    storage_extra_slots: List[str] = field(default_factory=list)
    storage_slot_diffs: List[StorageChangeDiff] = field(default_factory=list)
    storage_missing_reads: List[str] = field(default_factory=list)
    storage_extra_reads: List[str] = field(default_factory=list)
    balance_missing_txs: List[int] = field(default_factory=list)
    balance_extra_txs: List[int] = field(default_factory=list)
    balance_value_diffs: List[Dict[str, Any]] = field(default_factory=list)
    nonce_missing_txs: List[int] = field(default_factory=list)
    nonce_extra_txs: List[int] = field(default_factory=list)
    nonce_value_diffs: List[Dict[str, Any]] = field(default_factory=list)
    code_missing_txs: List[int] = field(default_factory=list)
    code_extra_txs: List[int] = field(default_factory=list)
    code_value_diffs: List[Dict[str, Any]] = field(default_factory=list)

    def has_differences(self) -> bool:
        return any([
            self.storage_missing_slots, self.storage_extra_slots, self.storage_slot_diffs,
            self.storage_missing_reads, self.storage_extra_reads,
            self.balance_missing_txs, self.balance_extra_txs, self.balance_value_diffs,
            self.nonce_missing_txs, self.nonce_extra_txs, self.nonce_value_diffs,
            self.code_missing_txs, self.code_extra_txs, self.code_value_diffs
        ])


@dataclass
class TransactionInfo:
    """Information about a transaction."""
    index: int
    hash: str
    from_addr: str
    to_addr: Optional[str]
    value: str
    gas: str
    gas_price: str
    tx_type: str
    is_contract_creation: bool
    has_access_list: bool
    input_data_size: int

    def type_str(self) -> str:
        if self.is_contract_creation:
            return "Contract Creation"
        elif self.to_addr:
            if self.input_data_size > 0:
                return "Contract Call"
            else:
                return "Transfer"
        return "Unknown"

    def short_desc(self) -> str:
        if self.is_contract_creation:
            return f"TX{self.index}: {self.from_addr[:10]}... → CREATE"
        elif self.to_addr:
            value_eth = int(self.value, 16) / 10**18 if self.value != '0x0' else 0
            if value_eth > 0:
                return f"TX{self.index}: {self.from_addr[:10]}... → {self.to_addr[:10]}... ({value_eth:.4f} ETH)"
            else:
                return f"TX{self.index}: {self.from_addr[:10]}... → {self.to_addr[:10]}..."
        return f"TX{self.index}: {self.from_addr[:10]}..."

    def involves_account(self, address: str) -> bool:
        # Import here to avoid circular dependency
        from .utils import normalize_hex
        addr = normalize_hex(address)
        return addr == normalize_hex(self.from_addr) or \
               (self.to_addr and addr == normalize_hex(self.to_addr))


@dataclass
class TransactionContext:
    """Transaction context for the block."""
    transactions: List[TransactionInfo] = field(default_factory=list)
    total_count: int = 0
    contract_creations: int = 0
    contract_calls: int = 0
    transfers: int = 0

    def get_transaction(self, index: int) -> Optional[TransactionInfo]:
        for tx in self.transactions:
            if tx.index == index:
                return tx
        return None

    def find_transactions_for_account(self, address: str) -> List[TransactionInfo]:
        return [tx for tx in self.transactions if tx.involves_account(address)]


@dataclass
class BALReport:
    """Complete comparison report for a block."""
    block_number: str
    block_hash: str
    client_info: str
    bal_hash_match: bool
    block_bal_hash: str
    generated_bal_hash: str
    tx_context: TransactionContext
    missing_accounts: List[str] = field(default_factory=list)
    extra_accounts: List[str] = field(default_factory=list)
    account_diffs: List[AccountDiff] = field(default_factory=list)
    ordering_violations: List[str] = field(default_factory=list)
    missing_tx_participants: List[str] = field(default_factory=list)
    missing_non_participants: List[str] = field(default_factory=list)

    def has_critical_differences(self) -> bool:
        if not self.bal_hash_match:
            return True
        if self.missing_accounts or self.extra_accounts:
            return True
        if any(diff.has_differences() for diff in self.account_diffs):
            return True
        return False


@dataclass
class Pattern:
    """Detected pattern in BAL differences."""
    pattern_type: str
    description: str
    severity: str
    evidence: List[str] = field(default_factory=list)
    affected_accounts: List[str] = field(default_factory=list)
    root_cause_hypothesis: str = ""
    eip_reference: str = ""
    debugging_steps: List[str] = field(default_factory=list)
