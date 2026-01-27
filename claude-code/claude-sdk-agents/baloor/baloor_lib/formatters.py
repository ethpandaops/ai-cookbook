"""
Output formatting functions for Baloor

Functions for formatting BAL comparison reports in various formats:
standard, diff, debug card, insights, multi-block, and comprehensive.
"""

from typing import List
from collections import defaultdict, Counter

from .models import BALReport, Pattern
from .utils import normalize_hex, shorten_hex


def format_standard_report(report: BALReport, verbose: bool = False) -> str:
    """Format standard comparison report."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"Block {report.block_number} ({shorten_hex(report.block_hash)})")
    lines.append(f"Client: {report.client_info}")
    lines.append(f"Transactions: {report.tx_context.total_count} " +
                 f"({report.tx_context.contract_creations} creations, " +
                 f"{report.tx_context.contract_calls} calls, " +
                 f"{report.tx_context.transfers} transfers)")
    lines.append("=" * 80)
    lines.append("")

    if not report.has_critical_differences():
        lines.append("✓ BALs match perfectly")
        return "\n".join(lines)

    lines.append("✗ BAL hash mismatch" if not report.bal_hash_match else "")
    if report.missing_accounts:
        lines.append(f"✗ {len(report.missing_accounts)} missing accounts")
    if report.extra_accounts:
        lines.append(f"✗ {len(report.extra_accounts)} extra accounts")
    if report.account_diffs:
        lines.append(f"✗ {len(report.account_diffs)} accounts with field differences")
    lines.append("")

    if verbose and report.tx_context.transactions:
        lines.append("📋 Transaction Summary:")
        for tx in report.tx_context.transactions[:10]:
            lines.append(f"  {tx.short_desc()} [{tx.type_str()}]")
        if len(report.tx_context.transactions) > 10:
            lines.append(f"  ... and {len(report.tx_context.transactions) - 10} more")
        lines.append("")

    if report.missing_accounts:
        lines.append(f"🔴 Missing Accounts ({len(report.missing_accounts)}):")
        lines.append("  Accounts present in Besu generated BAL but not in block BAL:")
        if report.missing_tx_participants:
            lines.append(f"\n  📍 Transaction Participants ({len(report.missing_tx_participants)}):")
            for addr in report.missing_tx_participants[:10]:
                related_txs = report.tx_context.find_transactions_for_account(addr)
                tx_indices = [f"TX{tx.index}" for tx in related_txs]
                lines.append(f"    - {addr} (in {', '.join(tx_indices)})")
        if report.missing_non_participants:
            lines.append(f"\n  🔍 Non-Participants ({len(report.missing_non_participants)}):")
            for addr in report.missing_non_participants[:10]:
                lines.append(f"    - {addr}")
        lines.append("")

    if report.account_diffs:
        lines.append(f"🔴 Field Differences ({len(report.account_diffs)} accounts):")
        for i, diff in enumerate(report.account_diffs):
            if not verbose and i >= 5:
                lines.append(f"\n  ... and {len(report.account_diffs) - 5} more")
                break
            lines.append(f"\n  {diff.address}")
            if diff.storage_missing_slots:
                lines.append(f"    • Missing storage slots: {len(diff.storage_missing_slots)}")
            if diff.balance_value_diffs:
                lines.append(f"    • Balance differences: {len(diff.balance_value_diffs)}")

    return "\n".join(lines)


def format_diff_report(report: BALReport) -> str:
    """Format as unified diff."""
    lines = []
    lines.append(f"diff --bal a/block b/generated")
    lines.append(f"Block: {report.block_number} ({shorten_hex(report.block_hash)})")
    lines.append(f"Client: {report.client_info}")
    lines.append(f"--- a/block.balHash\t{report.block_bal_hash}")
    lines.append(f"+++ b/generated.balHash\t{report.generated_bal_hash}")
    lines.append("")

    if report.missing_accounts:
        lines.append("@@ Accounts @@")
        for addr in report.missing_accounts:
            related_txs = report.tx_context.find_transactions_for_account(addr)
            tx_info = f" # in {', '.join([f'TX{tx.index}' for tx in related_txs])}" if related_txs else ""
            marker = " ⚠️ zero-address" if addr == '0x0000000000000000000000000000000000000000' else ""
            lines.append(f"+ {addr}{tx_info}{marker}")

    if report.extra_accounts:
        if not any("@@ Accounts @@" in l for l in lines[-5:]):
            lines.append("@@ Accounts @@")
        for addr in report.extra_accounts:
            lines.append(f"- {addr}")

    return "\n".join(lines)


def format_debug_card(report: BALReport, account_address: str) -> str:
    """Generate detailed debug card for specific account."""
    addr = normalize_hex(account_address)
    is_missing = addr in [normalize_hex(a) for a in report.missing_accounts]

    if not is_missing:
        return f"No critical issues found for {addr}"

    lines = []
    lines.append("╔" + "═" * 78 + "╗")
    lines.append("║" + f" DEBUG CARD: {addr}".ljust(78) + "║")
    lines.append("╠" + "═" * 78 + "╣")

    related_txs = report.tx_context.find_transactions_for_account(addr)
    if related_txs:
        lines.append("║ TRANSACTION CONTEXT:".ljust(79) + "║")
        for tx in related_txs[:5]:
            lines.append("║   " + tx.short_desc().ljust(75) + "║")
        lines.append("╟" + "─" * 78 + "╢")

    lines.append("║ STATUS: ❌ MISSING IN BLOCK BAL".ljust(79) + "║")
    lines.append("║         ✓ Present in Besu generated BAL".ljust(79) + "║")

    if addr == '0x0000000000000000000000000000000000000000':
        lines.append("║".ljust(79) + "║")
        lines.append("║ ⚠️  ZERO ADDRESS".ljust(79) + "║")
        lines.append("║   Per EIP-7928: \"Targets of CALL, CALLCODE, DELEGATECALL,".ljust(79) + "║")
        lines.append("║   STATICCALL (even if they revert)\" must be included.".ljust(79) + "║")

    lines.append("╟" + "─" * 78 + "╢")
    lines.append("║ DEBUGGING RECOMMENDATIONS:".ljust(79) + "║")
    lines.append("║   1. Trace transaction execution to see when account is accessed".ljust(79) + "║")
    lines.append("║   2. Check if account exists (has code/balance/nonce)".ljust(79) + "║")
    lines.append("║   3. Verify CALL/STATICCALL/DELEGATECALL opcodes".ljust(79) + "║")
    lines.append("║   4. Review client's BAL recording logic for transaction targets".ljust(79) + "║")
    lines.append("╚" + "═" * 78 + "╝")

    return "\n".join(lines)


def format_insights_report(report: BALReport, patterns: List[Pattern]) -> str:
    """Format contextual insights report."""
    lines = []
    lines.append("=" * 80)
    lines.append("CONTEXTUAL ANALYSIS & INSIGHTS")
    lines.append("=" * 80)
    lines.append(f"Block: {report.block_number} | Client: {report.client_info}")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    lines.append("## SUMMARY")
    lines.append("")
    lines.append(
        f"Block {report.block_number} from {report.client_info} shows "
        f"{'CRITICAL' if any(p.severity == 'critical' for p in patterns) else 'notable'} "
        f"differences between block BAL and Besu generated BAL."
    )

    if report.missing_accounts:
        pct = 100.0 * len(report.missing_tx_participants) / len(report.missing_accounts)
        lines.append("")
        lines.append(f"**Missing Accounts ({len(report.missing_accounts)}):** "
                    f"{len(report.missing_tx_participants)} ({pct:.0f}%) are transaction participants.")
        if pct == 100:
            lines.append("This is highly significant - ALL missing accounts are explicit transaction targets.")

    if patterns:
        lines.append("")
        lines.append(f"**Detected Patterns ({len(patterns)}):**")
        for pattern in patterns:
            icon = "🔴" if pattern.severity == "critical" else "⚠️"
            lines.append(f"{icon} {pattern.pattern_type}: {pattern.description}")

    # Detailed patterns
    if patterns:
        lines.append("")
        lines.append("=" * 80)
        lines.append("## DETECTED PATTERNS")
        lines.append("=" * 80)

        for i, pattern in enumerate(patterns, 1):
            lines.append("")
            severity_badge = {'critical': '🔴 CRITICAL', 'warning': '⚠️  WARNING', 'info': 'ℹ️  INFO'}[pattern.severity]
            lines.append(f"### Pattern {i}: {pattern.pattern_type}")
            lines.append(f"**Severity:** {severity_badge}")
            lines.append(f"**Description:** {pattern.description}")
            lines.append("")

            if pattern.evidence:
                lines.append("**Evidence:**")
                for evidence in pattern.evidence:
                    # Evidence contains the full AI analysis with sections
                    lines.append(f"{evidence}")
                lines.append("")

            # Skip empty fields (for AI-generated patterns these will be empty)
            if pattern.root_cause_hypothesis and pattern.root_cause_hypothesis.strip():
                lines.append("**Root Cause Hypothesis:**")
                for line in pattern.root_cause_hypothesis.split('\n'):
                    lines.append(f"  {line}")
                lines.append("")

            if pattern.eip_reference and pattern.eip_reference.strip():
                lines.append("**EIP-7928 Reference:**")
                lines.append(f"  {pattern.eip_reference}")
                lines.append("")

            if pattern.debugging_steps:
                lines.append("**Debugging Steps:**")
                for step in pattern.debugging_steps:
                    lines.append(f"  • {step}")
                lines.append("")

            if pattern.debugging_steps:
                lines.append("**Debugging Steps:**")
                for step in pattern.debugging_steps:
                    lines.append(f"  • {step}")
                lines.append("")

    return "\n".join(lines)


def format_multi_block_analysis(reports: List[BALReport]) -> str:
    """Format analysis across multiple blocks."""
    lines = []
    lines.append("=" * 80)
    lines.append("MULTI-BLOCK PATTERN ANALYSIS")
    lines.append("=" * 80)
    lines.append("")

    total_with_diffs = sum(1 for r in reports if r.has_critical_differences())
    lines.append(f"Total blocks analyzed: {len(reports)}")
    lines.append(f"Blocks with differences: {total_with_diffs} ({100.0*total_with_diffs/len(reports):.1f}%)")
    lines.append("")

    # By client
    by_client = defaultdict(lambda: {'total': 0, 'with_diffs': 0})
    for r in reports:
        client = r.client_info.split('(')[0].strip()
        by_client[client]['total'] += 1
        if r.has_critical_differences():
            by_client[client]['with_diffs'] += 1

    lines.append("BY CLIENT:")
    for client, stats in sorted(by_client.items()):
        pct = 100.0 * stats['with_diffs'] / stats['total'] if stats['total'] > 0 else 0
        lines.append(f"  {client}: {stats['with_diffs']}/{stats['total']} ({pct:.1f}%)")

    # Common missing accounts
    missing_counter = Counter()
    for r in reports:
        for addr in r.missing_accounts:
            missing_counter[addr] += 1

    if missing_counter:
        lines.append("")
        lines.append("MOST COMMON MISSING ACCOUNTS:")
        for addr, count in missing_counter.most_common(10):
            pct = 100.0 * count / len(reports)
            lines.append(f"  {addr}: {count} blocks ({pct:.1f}%)")

    return "\n".join(lines)


def format_account_diff_detailed(diff: 'AccountDiff', verbose: bool = False, indent: str = "  ") -> List[str]:
    """Format detailed account differences with all field types.

    This is a general-purpose formatter that handles all types of differences:
    - Storage reads (missing/extra)
    - Storage changes (slot-level with tx indices and values)
    - Balance changes (with actual values)
    - Nonce changes (with actual values)
    - Code changes (with actual code hashes)

    Args:
        diff: AccountDiff object containing all differences
        verbose: If True, show all details. If False, show summaries with limits
        indent: Base indentation level

    Returns:
        List of formatted lines
    """
    lines = []

    # Detect cross-reference cases: slots that appear as changes in one BAL and reads in the other
    cross_ref_slots = []
    if diff.storage_missing_reads and diff.storage_extra_slots:
        # Slots in generated BAL's reads but not in block BAL's reads
        # AND in block BAL's changes but not in generated BAL's changes
        cross_ref = set(diff.storage_missing_reads) & set(diff.storage_extra_slots)
        if cross_ref:
            cross_ref_slots.extend(sorted(cross_ref))

    if diff.storage_extra_reads and diff.storage_missing_slots:
        # Opposite case: slots in block BAL's reads but in generated BAL's changes
        cross_ref = set(diff.storage_extra_reads) & set(diff.storage_missing_slots)
        if cross_ref:
            cross_ref_slots.extend(sorted(cross_ref))

    # Show cross-reference cases first as they are particularly interesting
    if cross_ref_slots:
        lines.append(f"{indent}⚠️  Storage Read/Write Cross-Reference Detected:")
        lines.append(f"{indent}  The following {len(cross_ref_slots)} slot(s) appear as storage CHANGES in one BAL")
        lines.append(f"{indent}  but only as storage READS in the other BAL:")
        for slot in cross_ref_slots:
            if slot in diff.storage_extra_slots:
                lines.append(f"{indent}    • {slot}")
                lines.append(f"{indent}      → Block BAL: storageChanges (write operation)")
                lines.append(f"{indent}      → Generated BAL: storageReads (read-only)")
            else:
                lines.append(f"{indent}    • {slot}")
                lines.append(f"{indent}      → Block BAL: storageReads (read-only)")
                lines.append(f"{indent}      → Generated BAL: storageChanges (write operation)")
        lines.append(f"{indent}  This indicates different interpretation of write vs read operations.")
        lines.append("")

    # Storage Read Differences
    if diff.storage_missing_reads or diff.storage_extra_reads:
        lines.append(f"{indent}Storage Read Differences:")

        if diff.storage_missing_reads:
            count = len(diff.storage_missing_reads)
            lines.append(f"{indent}  Missing in block BAL (present in generated): {count} slot(s)")
            display_limit = None if verbose else 5
            for i, slot in enumerate(diff.storage_missing_reads):
                if display_limit and i >= display_limit:
                    lines.append(f"{indent}    ... and {count - display_limit} more slots")
                    break
                lines.append(f"{indent}    • {slot}")

        if diff.storage_extra_reads:
            count = len(diff.storage_extra_reads)
            lines.append(f"{indent}  Extra in block BAL (not in generated): {count} slot(s)")
            display_limit = None if verbose else 5
            for i, slot in enumerate(diff.storage_extra_reads):
                if display_limit and i >= display_limit:
                    lines.append(f"{indent}    ... and {count - display_limit} more slots")
                    break
                lines.append(f"{indent}    • {slot}")

    # Storage Change Differences (slot-level details)
    if diff.storage_slot_diffs:
        lines.append(f"{indent}Storage Change Differences:")
        display_limit = None if verbose else 3
        for i, slot_diff in enumerate(diff.storage_slot_diffs):
            if display_limit and i >= display_limit:
                lines.append(f"{indent}  ... and {len(diff.storage_slot_diffs) - display_limit} more slots")
                break

            lines.append(f"{indent}  Slot {slot_diff.slot}:")

            if slot_diff.missing_in_block:
                lines.append(f"{indent}    Missing in block BAL:")
                for change in slot_diff.missing_in_block[:5 if not verbose else None]:
                    lines.append(f"{indent}      • TX{change['txIndex']}: {change['newValue']}")

            if slot_diff.extra_in_block:
                lines.append(f"{indent}    Extra in block BAL:")
                for change in slot_diff.extra_in_block[:5 if not verbose else None]:
                    lines.append(f"{indent}      • TX{change['txIndex']}: {change['newValue']}")

            if slot_diff.value_differences:
                lines.append(f"{indent}    Value differences:")
                for vdiff in slot_diff.value_differences[:5 if not verbose else None]:
                    lines.append(f"{indent}      • TX{vdiff['txIndex']}:")
                    lines.append(f"{indent}        Block BAL:     {vdiff['blockValue']}")
                    lines.append(f"{indent}        Generated BAL: {vdiff['generatedValue']}")

    # Storage Slot Differences (missing/extra slots)
    if diff.storage_missing_slots or diff.storage_extra_slots:
        lines.append(f"{indent}Storage Slot Differences:")

        if diff.storage_missing_slots:
            count = len(diff.storage_missing_slots)
            lines.append(f"{indent}  Missing slots in block BAL: {count}")
            display_limit = None if verbose else 5
            for i, slot in enumerate(diff.storage_missing_slots):
                if display_limit and i >= display_limit:
                    lines.append(f"{indent}    ... and {count - display_limit} more")
                    break
                lines.append(f"{indent}    • {slot}")

        if diff.storage_extra_slots:
            count = len(diff.storage_extra_slots)
            lines.append(f"{indent}  Extra slots in block BAL: {count}")
            display_limit = None if verbose else 5
            for i, slot in enumerate(diff.storage_extra_slots):
                if display_limit and i >= display_limit:
                    lines.append(f"{indent}    ... and {count - display_limit} more")
                    break
                lines.append(f"{indent}    • {slot}")

    # Balance Differences
    if diff.balance_missing_txs or diff.balance_extra_txs or diff.balance_value_diffs:
        lines.append(f"{indent}Balance Differences:")

        if diff.balance_missing_txs:
            lines.append(f"{indent}  Missing balance changes in block BAL: TX {', '.join(map(str, diff.balance_missing_txs))}")

        if diff.balance_extra_txs:
            lines.append(f"{indent}  Extra balance changes in block BAL: TX {', '.join(map(str, diff.balance_extra_txs))}")

        if diff.balance_value_diffs:
            lines.append(f"{indent}  Balance value differences: {len(diff.balance_value_diffs)} transaction(s)")
            if verbose:
                for vdiff in diff.balance_value_diffs:
                    lines.append(f"{indent}    • TX{vdiff['txIndex']}:")
                    lines.append(f"{indent}      Block BAL:     {vdiff['blockValue']}")
                    lines.append(f"{indent}      Generated BAL: {vdiff['generatedValue']}")
            else:
                # Show first 2 in non-verbose mode
                for vdiff in diff.balance_value_diffs[:2]:
                    lines.append(f"{indent}    • TX{vdiff['txIndex']}: {vdiff['blockValue']} → {vdiff['generatedValue']}")
                if len(diff.balance_value_diffs) > 2:
                    lines.append(f"{indent}    ... and {len(diff.balance_value_diffs) - 2} more")

    # Nonce Differences
    if diff.nonce_missing_txs or diff.nonce_extra_txs or diff.nonce_value_diffs:
        lines.append(f"{indent}Nonce Differences:")

        if diff.nonce_missing_txs:
            lines.append(f"{indent}  Missing nonce changes in block BAL: TX {', '.join(map(str, diff.nonce_missing_txs))}")

        if diff.nonce_extra_txs:
            lines.append(f"{indent}  Extra nonce changes in block BAL: TX {', '.join(map(str, diff.nonce_extra_txs))}")

        if diff.nonce_value_diffs:
            lines.append(f"{indent}  Nonce value differences: {len(diff.nonce_value_diffs)} transaction(s)")
            display_limit = None if verbose else 5
            for i, vdiff in enumerate(diff.nonce_value_diffs):
                if display_limit and i >= display_limit:
                    lines.append(f"{indent}    ... and {len(diff.nonce_value_diffs) - display_limit} more")
                    break
                lines.append(f"{indent}    • TX{vdiff['txIndex']}: {vdiff['blockValue']} → {vdiff['generatedValue']}")

    # Code Differences
    if diff.code_missing_txs or diff.code_extra_txs or diff.code_value_diffs:
        lines.append(f"{indent}Code Differences:")

        if diff.code_missing_txs:
            lines.append(f"{indent}  Missing code changes in block BAL: TX {', '.join(map(str, diff.code_missing_txs))}")

        if diff.code_extra_txs:
            lines.append(f"{indent}  Extra code changes in block BAL: TX {', '.join(map(str, diff.code_extra_txs))}")

        if diff.code_value_diffs:
            lines.append(f"{indent}  Code value differences: {len(diff.code_value_diffs)} transaction(s)")
            if verbose:
                for vdiff in diff.code_value_diffs:
                    lines.append(f"{indent}    • TX{vdiff['txIndex']}:")
                    lines.append(f"{indent}      Block BAL:     {vdiff['blockValue'][:66]}...")
                    lines.append(f"{indent}      Generated BAL: {vdiff['generatedValue'][:66]}...")
            else:
                lines.append(f"{indent}    (use -v to see code hashes)")

    return lines


def format_comprehensive_report(report: BALReport, patterns: List[Pattern], verbose: bool = False) -> str:
    """Format comprehensive report with all views."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"Block {report.block_number} ({shorten_hex(report.block_hash)})")
    lines.append(f"Client: {report.client_info}")
    lines.append(f"Transactions: {report.tx_context.total_count} " +
                 f"({report.tx_context.contract_creations} creations, " +
                 f"{report.tx_context.contract_calls} calls, " +
                 f"{report.tx_context.transfers} transfers)")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    if not report.has_critical_differences():
        lines.append("✓ BALs match perfectly")
        return "\n".join(lines)

    lines.append("## SUMMARY")
    lines.append("")
    if report.missing_accounts:
        lines.append(f"✗ {len(report.missing_accounts)} missing accounts")
    if report.extra_accounts:
        lines.append(f"✗ {len(report.extra_accounts)} extra accounts")
    if report.account_diffs:
        lines.append(f"✗ {len(report.account_diffs)} accounts with field differences")
    lines.append("")

    # Insights section
    if patterns:
        lines.append("## DETECTED PATTERNS")
        lines.append("")
        for i, pattern in enumerate(patterns, 1):
            severity_badge = {'critical': '🔴 CRITICAL', 'warning': '⚠️  WARNING', 'info': 'ℹ️  INFO'}[pattern.severity]
            lines.append(f"### Pattern {i}: {pattern.pattern_type}")
            lines.append(f"**Severity:** {severity_badge}")
            lines.append(f"**Description:** {pattern.description}")
            lines.append("")

            if pattern.evidence:
                lines.append("**Evidence:**")
                for evidence in pattern.evidence:
                    # Evidence contains the full AI analysis with sections
                    lines.append(f"{evidence}")
                lines.append("")

            # Skip empty fields (for AI-generated patterns these will be empty)
            if pattern.root_cause_hypothesis and pattern.root_cause_hypothesis.strip():
                lines.append("**Root Cause Hypothesis:**")
                for line in pattern.root_cause_hypothesis.split('\n'):
                    lines.append(f"  {line}")
                lines.append("")

            if pattern.eip_reference and pattern.eip_reference.strip():
                lines.append("**EIP-7928 Reference:**")
                lines.append(f"  {pattern.eip_reference}")
                lines.append("")

            if pattern.debugging_steps:
                lines.append("**Debugging Steps:**")
                for step in pattern.debugging_steps:
                    lines.append(f"  • {step}")
                lines.append("")

    # Diff section
    lines.append("")
    lines.append("=" * 80)
    lines.append("## DIFFERENCES (Diff View)")
    lines.append("=" * 80)
    lines.append("")

    if report.missing_accounts:
        lines.append("### Missing Accounts (in generated BAL, not in block BAL)")
        for addr in report.missing_accounts:
            related_txs = report.tx_context.find_transactions_for_account(addr)
            tx_info = f" # in {', '.join([f'TX{tx.index}' for tx in related_txs])}" if related_txs else ""
            marker = " ⚠️ zero-address" if addr == '0x0000000000000000000000000000000000000000' else ""
            lines.append(f"  + {addr}{tx_info}{marker}")
        lines.append("")

    if report.extra_accounts:
        lines.append("### Extra Accounts (in block BAL, not in generated BAL)")
        for addr in report.extra_accounts:
            lines.append(f"  - {addr}")
        lines.append("")

    if report.account_diffs:
        lines.append(f"### Field Differences ({len(report.account_diffs)} accounts)")
        display_limit = None if verbose else 5
        for i, diff in enumerate(report.account_diffs):
            if display_limit and i >= display_limit:
                lines.append(f"  ... and {len(report.account_diffs) - display_limit} more (use -v to see all)")
                break

            lines.append("")
            lines.append(f"  Account: {diff.address}")

            # Use the detailed formatter to show all difference types
            detail_lines = format_account_diff_detailed(diff, verbose=verbose, indent="  ")
            if detail_lines:
                lines.extend(detail_lines)
            else:
                lines.append("    No field differences (unexpected)")

        lines.append("")

    return "\n".join(lines)
