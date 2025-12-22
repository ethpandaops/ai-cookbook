"""
Comparison logic for Baloor

Functions for comparing Block Access Lists between block BAL and generated BAL,
including account-level comparisons, storage changes, balance changes, etc.
"""

from typing import Dict, List, Tuple

from .models import (
    StorageChangeDiff,
    AccountDiff,
    TransactionInfo,
    TransactionContext,
    BALReport,
)
from .utils import normalize_hex, decode_client_from_extra_data


def compare_storage_changes(block_changes: List[Dict], gen_changes: List[Dict]) -> Tuple[List[str], List[str], List[StorageChangeDiff]]:
    """Compare storage changes between block and generated BALs."""
    block_slots = {normalize_hex(sc['slot']): sc for sc in block_changes}
    gen_slots = {normalize_hex(sc['slot']): sc for sc in gen_changes}

    block_slot_set = set(block_slots.keys())
    gen_slot_set = set(gen_slots.keys())

    missing_slots = sorted(list(gen_slot_set - block_slot_set))
    extra_slots = sorted(list(block_slot_set - gen_slot_set))
    common_slots = block_slot_set & gen_slot_set

    slot_diffs = []
    for slot in sorted(common_slots):
        block_sc = block_slots[slot]
        gen_sc = gen_slots[slot]

        block_changes_map = {
            change.get('txIndex'): normalize_hex(change.get('newValue'))
            for change in block_sc.get('changes', [])
        }
        gen_changes_map = {
            change.get('txIndex'): normalize_hex(change.get('newValue'))
            for change in gen_sc.get('changes', [])
        }

        block_tx_set = set(block_changes_map.keys())
        gen_tx_set = set(gen_changes_map.keys())

        diff = StorageChangeDiff(slot=slot)

        missing_txs = sorted(list(gen_tx_set - block_tx_set))
        extra_txs = sorted(list(block_tx_set - gen_tx_set))

        if missing_txs:
            diff.missing_in_block = [
                {'txIndex': tx, 'newValue': gen_changes_map[tx]} for tx in missing_txs
            ]

        if extra_txs:
            diff.extra_in_block = [
                {'txIndex': tx, 'newValue': block_changes_map[tx]} for tx in extra_txs
            ]

        for tx in sorted(block_tx_set & gen_tx_set):
            if block_changes_map[tx] != gen_changes_map[tx]:
                diff.value_differences.append({
                    'txIndex': tx,
                    'blockValue': block_changes_map[tx],
                    'generatedValue': gen_changes_map[tx]
                })

        if diff.missing_in_block or diff.extra_in_block or diff.value_differences:
            slot_diffs.append(diff)

    return missing_slots, extra_slots, slot_diffs


def compare_reads(block_reads: List[str], gen_reads: List[str]) -> Tuple[List[str], List[str]]:
    """Compare storage reads."""
    block_set = {normalize_hex(r) for r in block_reads}
    gen_set = {normalize_hex(r) for r in gen_reads}
    missing = sorted(list(gen_set - block_set))
    extra = sorted(list(block_set - gen_set))
    return missing, extra


def compare_indexed_changes(block_changes: List[Dict], gen_changes: List[Dict],
                           value_key: str) -> Tuple[List[int], List[int], List[Dict]]:
    """Compare balance, nonce, or code changes."""
    block_map = {
        change.get('txIndex'): normalize_hex(change.get(value_key)) if value_key != 'newNonce'
                               else change.get(value_key)
        for change in block_changes
    }
    gen_map = {
        change.get('txIndex'): normalize_hex(change.get(value_key)) if value_key != 'newNonce'
                               else change.get(value_key)
        for change in gen_changes
    }

    block_tx_set = set(block_map.keys())
    gen_tx_set = set(gen_map.keys())

    missing_txs = sorted(list(gen_tx_set - block_tx_set))
    extra_txs = sorted(list(block_tx_set - gen_tx_set))

    value_diffs = []
    for tx in sorted(block_tx_set & gen_tx_set):
        if block_map[tx] != gen_map[tx]:
            value_diffs.append({
                'txIndex': tx,
                'blockValue': block_map[tx],
                'generatedValue': gen_map[tx]
            })

    return missing_txs, extra_txs, value_diffs


def compare_account(block_account: Dict, gen_account: Dict) -> AccountDiff:
    """Compare all fields for a single account."""
    address = normalize_hex(block_account.get('address', gen_account.get('address')))
    diff = AccountDiff(address=address)

    block_storage = block_account.get('storageChanges', [])
    gen_storage = gen_account.get('storageChanges', [])
    diff.storage_missing_slots, diff.storage_extra_slots, diff.storage_slot_diffs = \
        compare_storage_changes(block_storage, gen_storage)

    block_reads = block_account.get('storageReads', [])
    gen_reads = gen_account.get('storageReads', [])
    diff.storage_missing_reads, diff.storage_extra_reads = compare_reads(block_reads, gen_reads)

    block_balance = block_account.get('balanceChanges', [])
    gen_balance = gen_account.get('balanceChanges', [])
    diff.balance_missing_txs, diff.balance_extra_txs, diff.balance_value_diffs = \
        compare_indexed_changes(block_balance, gen_balance, 'postBalance')

    block_nonce = block_account.get('nonceChanges', [])
    gen_nonce = gen_account.get('nonceChanges', [])
    diff.nonce_missing_txs, diff.nonce_extra_txs, diff.nonce_value_diffs = \
        compare_indexed_changes(block_nonce, gen_nonce, 'newNonce')

    block_code = block_account.get('codeChanges', [])
    gen_code = gen_account.get('codeChanges', [])
    diff.code_missing_txs, diff.code_extra_txs, diff.code_value_diffs = \
        compare_indexed_changes(block_code, gen_code, 'newCode')

    return diff


def parse_transaction_context(block: Dict) -> TransactionContext:
    """Parse transaction data from block."""
    transactions = block.get('transactions', [])
    context = TransactionContext(total_count=len(transactions))

    for tx in transactions:
        tx_index = int(tx.get('transactionIndex', '0x0'), 16)
        to_addr = tx.get('to')
        input_data = tx.get('input', '0x')
        input_size = (len(input_data) - 2) // 2 if input_data.startswith('0x') else len(input_data) // 2

        tx_info = TransactionInfo(
            index=tx_index,
            hash=normalize_hex(tx.get('hash', '')),
            from_addr=normalize_hex(tx.get('from', '')),
            to_addr=normalize_hex(to_addr) if to_addr else None,
            value=normalize_hex(tx.get('value', '0x0')),
            gas=normalize_hex(tx.get('gas', '0x0')),
            gas_price=normalize_hex(tx.get('gasPrice', '0x0')),
            tx_type=tx.get('type', '0x0'),
            is_contract_creation=(to_addr is None),
            has_access_list=bool(tx.get('accessList', [])),
            input_data_size=input_size
        )

        context.transactions.append(tx_info)

        if tx_info.is_contract_creation:
            context.contract_creations += 1
        elif input_size > 0:
            context.contract_calls += 1
        else:
            context.transfers += 1

    return context


def compare_block(block_entry: Dict) -> BALReport:
    """Compare BALs for a single block entry."""
    block = block_entry.get('block', {})
    block_bal = block.get('blockAccessList', {})
    gen_bal = block_entry.get('generatedBlockAccessList', {})

    block_number = block.get('number', 'unknown')
    block_hash = block.get('hash', 'unknown')
    extra_data = block.get('extraData', '')
    client_info = decode_client_from_extra_data(extra_data)

    block_bal_hash = normalize_hex(block.get('balHash', ''))
    generated_bal_hash = "N/A"
    bal_hash_match = False

    tx_context = parse_transaction_context(block)

    block_accounts = block_bal.get('accountChanges', [])
    gen_accounts = gen_bal.get('accountChanges', [])

    block_map = {normalize_hex(acc.get('address')): acc for acc in block_accounts}
    gen_map = {normalize_hex(acc.get('address')): acc for acc in gen_accounts}

    block_addr_set = set(block_map.keys())
    gen_addr_set = set(gen_map.keys())

    missing_accounts = sorted(list(gen_addr_set - block_addr_set))
    extra_accounts = sorted(list(block_addr_set - gen_addr_set))
    common_accounts = block_addr_set & gen_addr_set

    account_diffs = []
    for addr in sorted(common_accounts):
        diff = compare_account(block_map[addr], gen_map[addr])
        if diff.has_differences():
            account_diffs.append(diff)

    # Categorize missing accounts
    participant_addrs = set()
    for tx in tx_context.transactions:
        participant_addrs.add(normalize_hex(tx.from_addr))
        if tx.to_addr:
            participant_addrs.add(normalize_hex(tx.to_addr))

    missing_tx_participants = []
    missing_non_participants = []
    for addr in missing_accounts:
        norm_addr = normalize_hex(addr)
        if norm_addr in participant_addrs:
            missing_tx_participants.append(addr)
        else:
            missing_non_participants.append(addr)

    report = BALReport(
        block_number=block_number,
        block_hash=block_hash,
        client_info=client_info,
        bal_hash_match=bal_hash_match,
        block_bal_hash=block_bal_hash,
        generated_bal_hash=generated_bal_hash,
        tx_context=tx_context,
        missing_accounts=missing_accounts,
        extra_accounts=extra_accounts,
        account_diffs=account_diffs,
        missing_tx_participants=missing_tx_participants,
        missing_non_participants=missing_non_participants
    )

    return report
