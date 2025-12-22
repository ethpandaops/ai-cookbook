"""
Difference Analyzer Agent

Deep analysis of BAL differences between block BAL and generated BAL.
Builds operation sequences, detects patterns, and creates structured analysis.
"""

import sys
from typing import Dict, List, Optional, Tuple

try:
    import anyio
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False

from ..models import BALReport, AccountDiff
from ..utils import normalize_hex, shorten_hex
from .shared_context import (
    DifferenceContext,
    OperationSequence,
    PatternHypothesis,
    TxResult,
    Operation,
)


def categorize_accounts(report: BALReport) -> Tuple[List[str], List[str], List[str]]:
    """
    Categorize accounts into tx participants, opcode-accessed, and special addresses.

    Returns:
        (tx_participants, opcode_accessed, special_addresses)
    """
    tx_participants = []
    special_addresses = []
    opcode_accessed = []

    for addr in report.missing_accounts:
        norm_addr = normalize_hex(addr)

        # Check if special address
        if norm_addr == '0x0000000000000000000000000000000000000000':
            special_addresses.append(addr)
        # Check if precompile (0x01-0x0a)
        elif norm_addr.startswith('0x000000000000000000000000000000000000000') and \
             len(norm_addr) == 42 and \
             norm_addr[-1] in '123456789a':
            special_addresses.append(addr)

        # Check if tx participant
        txs = report.tx_context.find_transactions_for_account(addr)
        if txs:
            tx_participants.append(addr)
        else:
            opcode_accessed.append(addr)

    return (tx_participants, opcode_accessed, special_addresses)


def build_operation_sequences(
    report: BALReport,
    block_entry: Dict
) -> List[OperationSequence]:
    """
    Build operation sequences for affected accounts based on BAL differences.

    This creates a detailed trace of what operations occurred and what the
    expected vs actual BAL state is for each account/transaction.
    """
    sequences = []

    # Get BAL data
    gen_bal = block_entry.get('generatedBlockAccessList', {})
    gen_accounts = {normalize_hex(acc.get('address')): acc for acc in gen_bal.get('accountChanges', [])}
    block_bal = block_entry.get('block', {}).get('blockAccessList', {})
    block_accounts = {normalize_hex(acc.get('address')): acc for acc in block_bal.get('accountChanges', [])}

    # Process missing accounts
    for addr in report.missing_accounts[:20]:  # Limit to 20 for performance
        norm_addr = normalize_hex(addr)

        # Get transactions for this account
        txs = report.tx_context.find_transactions_for_account(addr)

        if not txs:
            # Account accessed via opcode, not direct tx participant
            # Still create a sequence if we have BAL data
            if norm_addr in gen_accounts:
                gen_data = gen_accounts[norm_addr]

                seq = OperationSequence(
                    tx_index=-1,  # Not a specific tx
                    tx_hash="opcode_access",
                    account=addr,
                    slot=None,
                )

                # Infer operations from BAL data
                if gen_data.get('storageChanges'):
                    seq.operations.append(Operation.SLOAD)
                    seq.operations.append(Operation.SSTORE)
                    seq.expected_in_storage_changes = True

                if gen_data.get('storageReads'):
                    if Operation.SLOAD not in seq.operations:
                        seq.operations.append(Operation.SLOAD)
                    seq.expected_in_storage_reads = True

                if gen_data.get('balanceChanges'):
                    seq.operations.append(Operation.BALANCE)
                    seq.expected_in_balance_changes = True

                if gen_data.get('codeChanges'):
                    seq.operations.append(Operation.CREATE)
                    seq.expected_in_code_changes = True

                # Actual state
                seq.actual_in_generated_bal = {
                    "storage_reads": bool(gen_data.get('storageReads')),
                    "storage_changes": bool(gen_data.get('storageChanges')),
                    "balance_changes": bool(gen_data.get('balanceChanges')),
                    "nonce_changes": bool(gen_data.get('nonceChanges')),
                    "code_changes": bool(gen_data.get('codeChanges')),
                }

                seq.actual_in_block_bal = {
                    "storage_reads": False,
                    "storage_changes": False,
                    "balance_changes": False,
                    "nonce_changes": False,
                    "code_changes": False,
                }

                seq.has_mismatch = True
                seq.mismatch_description = "Account missing entirely from block BAL"

                sequences.append(seq)

        else:
            # Process each transaction
            for tx in txs:
                seq = OperationSequence(
                    tx_index=tx.index,
                    tx_hash=tx.hash,
                    account=addr,
                    slot=None,
                )

                # Infer operations from transaction type
                if tx.is_contract_creation:
                    seq.operations.append(Operation.CREATE)
                    seq.expected_in_code_changes = True
                    seq.expected_in_nonce_changes = True
                elif tx.input_data_size > 0:
                    # Contract call - likely has storage operations
                    seq.operations.append(Operation.CALL)
                else:
                    # Simple transfer
                    seq.operations.append(Operation.CALL)

                # Always expect balance changes for value transfers
                if tx.value != '0x0':
                    seq.expected_in_balance_changes = True

                # Check actual state in BALs
                if norm_addr in gen_accounts:
                    gen_data = gen_accounts[norm_addr]

                    # Check if this tx is present in the BAL data
                    has_storage_in_tx = any(
                        tx.index in [change[0] for change in slot_changes[1]]
                        for slot_changes in gen_data.get('storageChanges', [])
                    )

                    has_reads_in_tx = bool(gen_data.get('storageReads'))

                    seq.actual_in_generated_bal = {
                        "storage_reads": has_reads_in_tx,
                        "storage_changes": has_storage_in_tx,
                        "balance_changes": any(
                            tx.index == bc[0]
                            for bc in gen_data.get('balanceChanges', [])
                        ),
                        "nonce_changes": any(
                            tx.index == nc[0]
                            for nc in gen_data.get('nonceChanges', [])
                        ),
                        "code_changes": any(
                            tx.index == cc[0]
                            for cc in gen_data.get('codeChanges', [])
                        ),
                    }

                if norm_addr in block_accounts:
                    block_data = block_accounts[norm_addr]

                    has_storage_in_tx = any(
                        tx.index in [change[0] for change in slot_changes[1]]
                        for slot_changes in block_data.get('storageChanges', [])
                    )

                    has_reads_in_tx = bool(block_data.get('storageReads'))

                    seq.actual_in_block_bal = {
                        "storage_reads": has_reads_in_tx,
                        "storage_changes": has_storage_in_tx,
                        "balance_changes": any(
                            tx.index == bc[0]
                            for bc in block_data.get('balanceChanges', [])
                        ),
                        "nonce_changes": any(
                            tx.index == nc[0]
                            for nc in block_data.get('nonceChanges', [])
                        ),
                        "code_changes": any(
                            tx.index == cc[0]
                            for cc in block_data.get('codeChanges', [])
                        ),
                    }
                else:
                    seq.actual_in_block_bal = {
                        "storage_reads": False,
                        "storage_changes": False,
                        "balance_changes": False,
                        "nonce_changes": False,
                        "code_changes": False,
                    }

                # Check for mismatches
                seq.has_mismatch = (
                    seq.actual_in_generated_bal != seq.actual_in_block_bal
                )

                if seq.has_mismatch:
                    seq.mismatch_description = "BAL state differs between block and generated"

                sequences.append(seq)

    # Process account diffs (accounts present in both but with differences)
    for diff in report.account_diffs[:20]:  # Limit to 20 for performance
        norm_addr = normalize_hex(diff.address)

        # Storage read/write cross-references
        if diff.storage_missing_reads and diff.storage_extra_slots:
            cross_ref = set(diff.storage_missing_reads) & set(diff.storage_extra_slots)
            for slot in cross_ref:
                seq = OperationSequence(
                    tx_index=-1,
                    tx_hash="cross_reference",
                    account=diff.address,
                    slot=slot,
                )
                seq.operations = [Operation.SLOAD, Operation.SSTORE]
                seq.expected_in_storage_reads = True  # Should be read-only
                seq.has_mismatch = True
                seq.mismatch_description = (
                    f"Slot appears as storage change in block BAL but storage read in generated BAL"
                )
                sequences.append(seq)

    return sequences


def analyze_read_write_mismatches(report: BALReport) -> List[Dict]:
    """
    Find cases where a slot appears as a read in one BAL and a write in another.
    This is a critical pattern indicating journal/change tracking issues.
    """
    mismatches = []

    for diff in report.account_diffs:
        # Check for cross-references
        if diff.storage_missing_reads and diff.storage_extra_slots:
            # Slots in generated BAL reads but not in block BAL reads
            # AND in block BAL changes but not in generated BAL changes
            cross_ref = set(diff.storage_missing_reads) & set(diff.storage_extra_slots)
            for slot in cross_ref:
                mismatches.append({
                    "account": diff.address,
                    "slot": slot,
                    "pattern": "read_in_generated_write_in_block",
                    "description": "Slot is read-only in generated BAL but appears as write in block BAL",
                })

        if diff.storage_extra_reads and diff.storage_missing_slots:
            cross_ref = set(diff.storage_extra_reads) & set(diff.storage_missing_slots)
            for slot in cross_ref:
                mismatches.append({
                    "account": diff.address,
                    "slot": slot,
                    "pattern": "write_in_generated_read_in_block",
                    "description": "Slot is written in generated BAL but appears as read-only in block BAL",
                })

    return mismatches


async def detect_patterns_with_ai(
    report: BALReport,
    operation_sequences: List[OperationSequence],
    read_write_mismatches: List[Dict],
) -> List[PatternHypothesis]:
    """
    Use AI to detect patterns in the differences based on operation sequences.
    """
    if not CLAUDE_SDK_AVAILABLE or not operation_sequences:
        return []

    # Build analysis prompt
    prompt_parts = [
        f"# Pattern Detection Request",
        f"",
        f"Analyze the following BAL difference patterns and identify the root cause.",
        f"",
        f"## Context",
        f"Block: {report.block_number}",
        f"Client: {report.client_info}",
        f"Missing accounts: {len(report.missing_accounts)}",
        f"Accounts with diffs: {len(report.account_diffs)}",
        f"",
        f"## Operation Sequences",
        f"",
    ]

    # Add operation sequences
    for seq in operation_sequences[:15]:  # Limit to 15
        prompt_parts.append(f"Account: {seq.account}")
        if seq.slot:
            prompt_parts.append(f"Slot: {seq.slot}")
        prompt_parts.append(f"TX{seq.tx_index}: {', '.join([op.value for op in seq.operations])}")
        prompt_parts.append(f"Expected in Generated BAL: {seq.actual_in_generated_bal}")
        prompt_parts.append(f"Actual in Block BAL: {seq.actual_in_block_bal}")
        if seq.has_mismatch:
            prompt_parts.append(f"❌ MISMATCH: {seq.mismatch_description}")
        prompt_parts.append("")

    # Add read/write mismatches
    if read_write_mismatches:
        prompt_parts.append("## Storage Read/Write Cross-References")
        prompt_parts.append("")
        for mismatch in read_write_mismatches[:10]:
            prompt_parts.append(f"Account: {mismatch['account']}")
            prompt_parts.append(f"Slot: {mismatch['slot']}")
            prompt_parts.append(f"Pattern: {mismatch['pattern']}")
            prompt_parts.append(f"Description: {mismatch['description']}")
            prompt_parts.append("")

    prompt_parts.extend([
        f"## Task",
        f"",
        f"Identify 2-3 high-confidence pattern hypotheses that explain these differences.",
        f"",
        f"For each pattern, provide:",
        f"- Pattern name (concise)",
        f"- Description",
        f"- Confidence (high/medium/low)",
        f"- Supporting evidence (2-3 bullet points)",
        f"",
        f"Focus on:",
        f"- Journal/change tracking issues",
        f"- Revert handling problems",
        f"- SLOAD/SSTORE recording bugs",
        f"- Special address filtering",
    ])

    prompt = "\n".join(prompt_parts)

    options = ClaudeAgentOptions(
        max_turns=2,
        system_prompt=(
            "You are an expert in Ethereum client BAL implementations and EIP-7928. "
            "Analyze operation sequences to detect systematic patterns in BAL differences. "
            "Focus on journal coverage, revert handling, and state change tracking."
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
        print(f"    Warning: AI pattern detection failed: {e}", file=sys.stderr)
        return []

    # Parse patterns from response (simple parsing)
    # In production, this would be more sophisticated
    return [
        PatternHypothesis(
            pattern_name="AI Detected Pattern",
            description="\n".join(response_text),
            confidence="medium",
            supporting_evidence=[],
        )
    ]


def analyze_differences(report: BALReport, block_entry: Dict) -> DifferenceContext:
    """
    Main entry point for difference analysis.

    Args:
        report: BAL comparison report
        block_entry: Raw block data

    Returns:
        DifferenceContext with detailed analysis
    """
    print(f"\nDifference Analyzer Agent:", file=sys.stderr)

    # Categorize accounts
    tx_participants, opcode_accessed, special_addresses = categorize_accounts(report)

    print(f"  Transaction participants: {len(tx_participants)}", file=sys.stderr)
    print(f"  Opcode-accessed accounts: {len(opcode_accessed)}", file=sys.stderr)
    print(f"  Special addresses: {len(special_addresses)}", file=sys.stderr)

    # Build operation sequences
    print(f"  Building operation sequences...", file=sys.stderr)
    sequences = build_operation_sequences(report, block_entry)
    print(f"  Created {len(sequences)} operation sequences", file=sys.stderr)

    # Analyze read/write mismatches
    print(f"  Analyzing storage read/write mismatches...", file=sys.stderr)
    read_write_mismatches = analyze_read_write_mismatches(report)
    print(f"  Found {len(read_write_mismatches)} read/write cross-references", file=sys.stderr)

    # Detect patterns with AI
    print(f"  Running AI pattern detection...", file=sys.stderr)
    if CLAUDE_SDK_AVAILABLE:
        patterns = anyio.run(detect_patterns_with_ai, report, sequences, read_write_mismatches)
        print(f"  Detected {len(patterns)} patterns", file=sys.stderr)
    else:
        patterns = []
        print(f"  Skipping AI pattern detection (SDK not available)", file=sys.stderr)

    # Create context
    context = DifferenceContext(
        operation_sequences=sequences,
        tx_participant_accounts=tx_participants,
        opcode_accessed_accounts=opcode_accessed,
        special_addresses=special_addresses,
        read_write_mismatches=read_write_mismatches,
        detected_patterns=patterns,
        total_affected_accounts=len(report.missing_accounts) + len(report.account_diffs),
        total_affected_transactions=report.tx_context.total_count,
        total_missing_in_block_bal=len(report.missing_accounts),
        total_extra_in_block_bal=len(report.extra_accounts),
        has_storage_read_diffs=any(d.storage_missing_reads or d.storage_extra_reads for d in report.account_diffs),
        has_storage_change_diffs=any(d.storage_missing_slots or d.storage_extra_slots for d in report.account_diffs),
        has_balance_diffs=any(d.balance_missing_txs or d.balance_value_diffs for d in report.account_diffs),
        has_nonce_diffs=any(d.nonce_missing_txs or d.nonce_value_diffs for d in report.account_diffs),
        has_code_diffs=any(d.code_missing_txs or d.code_value_diffs for d in report.account_diffs),
    )

    print(f"  Difference analysis complete", file=sys.stderr)

    return context
