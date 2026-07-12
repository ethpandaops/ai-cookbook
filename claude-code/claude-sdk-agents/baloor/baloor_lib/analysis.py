"""
Pattern detection and analysis for Baloor

Functions for detecting patterns in BAL differences, fetching EIP specifications,
and running AI-powered analysis using Claude SDK.

Includes both legacy single-AI analysis and new multi-agent analysis system.
"""

import json
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Optional

from .models import BALReport, Pattern
from .utils import normalize_hex, shorten_hex

# Try to import Claude Agent SDK
try:
    import anyio
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False


def fetch_eip_7928() -> Optional[str]:
    """Fetch EIP-7928 specification from GitHub."""
    url = "https://raw.githubusercontent.com/ethereum/EIPs/refs/heads/master/EIPS/eip-7928.md"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode('utf-8')
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"Warning: Could not fetch EIP-7928: {e}", file=sys.stderr)
        return None


def fetch_test_files() -> Dict[str, Optional[str]]:
    """Fetch EIP-7928 test files from execution-spec-tests repository."""
    test_urls = {
        "spec.py": "https://raw.githubusercontent.com/ethereum/execution-spec-tests/refs/heads/main/tests/amsterdam/eip7928_block_level_access_lists/spec.py",
        "test_block_access_lists.py": "https://raw.githubusercontent.com/ethereum/execution-spec-tests/refs/heads/main/tests/amsterdam/eip7928_block_level_access_lists/test_block_access_lists.py",
        "test_block_access_lists_eip7702.py": "https://raw.githubusercontent.com/ethereum/execution-spec-tests/refs/heads/main/tests/amsterdam/eip7928_block_level_access_lists/test_block_access_lists_eip7702.py",
        "test_block_access_lists_invalid.py": "https://raw.githubusercontent.com/ethereum/execution-spec-tests/refs/heads/main/tests/amsterdam/eip7928_block_level_access_lists/test_block_access_lists_invalid.py",
        "test_block_access_lists_opcodes.py": "https://raw.githubusercontent.com/ethereum/execution-spec-tests/refs/heads/main/tests/amsterdam/eip7928_block_level_access_lists/test_block_access_lists_opcodes.py",
        "test_cases.md": "https://raw.githubusercontent.com/ethereum/execution-spec-tests/refs/heads/main/tests/amsterdam/eip7928_block_level_access_lists/test_cases.md",
    }

    results = {}
    for filename, url in test_urls.items():
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                results[filename] = response.read().decode('utf-8')
                print(f"  Fetched {filename} ({len(results[filename])} chars)", file=sys.stderr)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  Warning: Could not fetch {filename}: {e}", file=sys.stderr)
            results[filename] = None

    return results


async def ai_analyze_differences(
    diff_type: str,
    differences: str,
    eip_context: Optional[str],
    block_context: str,
    raw_data: Optional[Dict] = None,
    test_files: Optional[Dict[str, Optional[str]]] = None
) -> Optional[str]:
    """Use Claude SDK to analyze specific BAL differences with enhanced context."""
    if not CLAUDE_SDK_AVAILABLE:
        return None

    # Build the analysis prompt with comprehensive context
    prompt_parts = [
        f"# BAL Difference Analysis Request",
        f"",
        f"## Important Context",
        f"",
        f"You are analyzing Block Access List (BAL) differences between TWO implementations:",
        f"",
        f"1. **Block BAL**: The BAL included in the incoming block",
        f"   - Source: The execution client that produced the block (identified by extraData field)",
        f"   - This is what the block proposer calculated and included in their block",
        f"",
        f"2. **Generated BAL**: Besu's local calculation of what the BAL should be",
        f"   - Source: Besu execution client (via Besu's debug endpoint)",
        f"   - This is Besu's independent calculation when validating the block",
        f"",
        f"**CRITICAL**: We do NOT know which implementation is correct. Both could be wrong, or one could be right.",
        f"Your job is to:",
        f"- Analyze the differences objectively",
        f"- Determine which version is more likely EIP-7928 compliant",
        f"- Identify the bug in whichever implementation is incorrect",
        f"- Suggest testing improvements to prevent similar issues",
        f"",
    ]

    # Add RLP structure definitions from EIP-7928
    prompt_parts.extend([
        f"## EIP-7928 Data Structure Definitions",
        f"",
        f"```python",
        f"# Core change structures (RLP encoded as lists)",
        f"StorageChange = [BlockAccessIndex, StorageValue]",
        f"BalanceChange = [BlockAccessIndex, Balance]  # Balance after transaction",
        f"NonceChange = [BlockAccessIndex, Nonce]",
        f"CodeChange = [BlockAccessIndex, CodeData]",
        f"",
        f"# Slot changes: all changes to a single storage slot",
        f"SlotChanges = [StorageKey, List[StorageChange]]",
        f"",
        f"# Account changes: all changes for a single account",
        f"AccountChanges = [",
        f"    Address,                    # account address",
        f"    List[SlotChanges],          # storage_changes (writes)",
        f"    List[StorageKey],           # storage_reads (read-only)",
        f"    List[BalanceChange],        # balance_changes",
        f"    List[NonceChange],          # nonce_changes",
        f"    List[CodeChange]            # code_changes (deployments)",
        f"]",
        f"",
        f"# BlockAccessIndex: transaction index where access occurred",
        f"```",
        f"",
    ])

    # Add block context
    prompt_parts.extend([
        f"## Block Context",
        f"{block_context}",
        f"",
    ])

    # Add raw data if provided (actual BAL structures)
    if raw_data:
        prompt_parts.extend([
            f"## Actual BAL Data Structures",
            f"",
            f"```json",
            f"{json.dumps(raw_data, indent=2)}",
            f"```",
            f"",
        ])

    # Add difference details
    prompt_parts.extend([
        f"## Difference Type: {diff_type}",
        f"{differences}",
        f"",
    ])

    if eip_context:
        # Include more of the EIP spec - extract key sections
        eip_lines = eip_context.split('\n')

        # Try to get more complete sections (up to 12000 chars for better coverage)
        eip_excerpt = eip_context[:12000]

        prompt_parts.extend([
            f"## EIP-7928 Specification",
            f"",
            f"```markdown",
            f"{eip_excerpt}",
            f"```",
            f"",
        ])

    # Add test files context if available
    if test_files:
        prompt_parts.extend([
            f"## EIP-7928 Test Suite Context",
            f"",
            f"The following test files are from the execution-spec-tests repository.",
            f"Use these to understand what scenarios are currently tested and identify gaps.",
            f"",
        ])

        for filename, content in test_files.items():
            if content:
                # Limit each file to reasonable size (3000 chars) to fit in context
                content_excerpt = content[:3000]
                if len(content) > 3000:
                    content_excerpt += "\n... (truncated)"
                prompt_parts.extend([
                    f"### {filename}",
                    f"",
                    f"```python" if filename.endswith('.py') else f"```markdown",
                    f"{content_excerpt}",
                    f"```",
                    f"",
                ])

    prompt_parts.extend([
        f"## Analysis Request",
        f"",
        f"Provide a CONCISE, well-formatted analysis with exactly these 6 sections:",
        f"",
        f"### 1. EXECUTIVE SUMMARY",
        f"Write 1-2 short paragraphs (3-5 sentences each):",
        f"- What differences exist and which implementation appears more compliant",
        f"- Overall severity (CRITICAL/WARNING) and primary impact",
        f"",
        f"### 2. ROOT CAUSE ANALYSIS",
        f"Identify the bug in 1-2 paragraphs, using code examples:",
        f"- The specific implementation flaw (conditional filtering, revert handling, etc.)",
        f"- Show the likely INCORRECT pattern with a code block",
        f"- Show the CORRECT pattern with a code block",
        f"",
        f"Example format:",
        f"```python",
        f"# INCORRECT (likely bug)",
        f"if transaction.success:",
        f"    record_storage_reads()",
        f"",
        f"# CORRECT (per EIP-7928)",
        f"record_storage_reads()  # Always record",
        f"```",
        f"",
        f"### 3. EIP-7928 COMPLIANCE",
        f"Write 1 paragraph with key spec quotes:",
        f"- Which requirement is violated (use a short quote in `backticks`)",
        f"- Which client is compliant and which is not",
        f"",
        f"### 4. DEBUGGING STEPS",
        f"Provide 4-5 concrete actions with commands:",
        f"1. Action with command example: `debug_traceBlock 0x20`",
        f"2. Code location to check: `src/.../FileName.ext:123`",
        f"3. Test case approach",
        f"4. Minimal reproduction steps",
        f"",
        f"### 5. TESTING IMPROVEMENTS",
        f"Based on the current test suite and the found issue, recommend specific improvements:",
        f"- What test scenarios are missing that would have caught this bug?",
        f"- Provide 2-3 concrete test case descriptions with pseudocode",
        f"- Suggest edge cases that should be added to the test suite",
        f"- Include assertions that would fail with the current buggy implementation",
        f"",
        f"Example format:",
        f"```python",
        f"def test_missing_scenario():",
        f"    # Test that would catch this bug",
        f"    bal = execute_block_with_reverted_call()",
        f"    assert zero_address in bal.accounts  # Would fail with current bug",
        f"```",
        f"",
        f"### 6. VERDICT",
        f"Format as structured data:",
        f"```",
        f"Status: CRITICAL",
        f"Compliant: [Client name]",
        f"Finding: [One sentence]",
        f"Action: [Primary fix needed]",
        f"Impact: [What breaks if unresolved]",
        f"```",
        f"",
        f"FORMATTING RULES:",
        f"- Use code blocks for examples (`inline code` or ```blocks```)",
        f"- Use **bold** for emphasis sparingly",
        f"- Keep paragraphs to 3-5 sentences max",
        f"- Use addresses/slots/txIndex numbers directly (no need to repeat 'account X, slot Y')",
        f"- Total response: 1000-1500 words",
    ])

    prompt = "\n".join(prompt_parts)

    # Query Claude with limited turns
    options = ClaudeAgentOptions(
        max_turns=3,
        system_prompt=(
            "You are an expert in Ethereum EIPs and execution client implementations. "
            "Provide CONCISE, well-formatted analysis of BAL differences with OBJECTIVITY. "
            "Use code blocks to illustrate bugs and fixes. Keep paragraphs short (3-5 sentences). "
            "Use markdown formatting: `inline code`, ```code blocks```, **bold** for emphasis. "
            "Be specific with addresses, slots, file paths, and commands. "
            "Your response must have exactly 6 sections: Executive Summary, Root Cause Analysis, "
            "EIP-7928 Compliance, Debugging Steps, Testing Improvements, and Verdict. Target 1000-1500 words. "
            "Do NOT assume either client is correct - evaluate objectively against EIP-7928."
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
        print(f"Warning: AI analysis failed: {e}", file=sys.stderr)
        return None

    return "\n".join(response_text) if response_text else None


def run_ai_analysis(
    diff_type: str,
    differences: str,
    eip_context: Optional[str],
    block_context: str,
    raw_data: Optional[Dict] = None,
    test_files: Optional[Dict[str, Optional[str]]] = None
) -> Optional[str]:
    """Synchronous wrapper for AI analysis."""
    if not CLAUDE_SDK_AVAILABLE:
        return None

    try:
        return anyio.run(ai_analyze_differences, diff_type, differences, eip_context, block_context, raw_data, test_files)
    except Exception as e:
        print(f"Warning: AI analysis failed: {e}", file=sys.stderr)
        return None


def analyze_storage_changes(report: BALReport, eip_context: Optional[str], block_entry: Optional[Dict] = None, test_files: Optional[Dict[str, Optional[str]]] = None) -> List[Pattern]:
    """Analyze storage change differences."""
    patterns = []

    storage_diffs = []
    for diff in report.account_diffs:
        if diff.storage_missing_slots or diff.storage_extra_slots or diff.storage_slot_diffs:
            storage_diffs.append(diff)

    if not storage_diffs:
        return patterns

    # Run AI analysis if available and there are differences
    total_missing_slots = sum(len(d.storage_missing_slots) for d in storage_diffs)
    total_value_diffs = sum(len(d.storage_slot_diffs) for d in storage_diffs)

    if (total_missing_slots > 0 or total_value_diffs > 0) and CLAUDE_SDK_AVAILABLE and eip_context:
        print("  Running enhanced analysis on storage change differences...", file=sys.stderr)

        block_context = f"""
Block: {report.block_number} ({shorten_hex(report.block_hash)})
Client: {report.client_info}
Total Transactions: {report.tx_context.total_count}
Accounts with storage change differences: {len(storage_diffs)}
"""

        diff_details = []
        diff_details.append(f"## Storage Change Differences ({len(storage_diffs)} accounts)")
        diff_details.append("")

        raw_data = {"accounts_with_storage_change_diffs": []}

        if block_entry:
            gen_bal = block_entry.get('generatedBlockAccessList', {})
            gen_accounts = {normalize_hex(acc.get('address')): acc for acc in gen_bal.get('accountChanges', [])}
            block_bal = block_entry.get('block', {}).get('blockAccessList', {})
            block_accounts = {normalize_hex(acc.get('address')): acc for acc in block_bal.get('accountChanges', [])}

            for i, diff in enumerate(storage_diffs[:10]):
                diff_details.append(f"### Account {i+1}: {diff.address}")
                if diff.storage_missing_slots:
                    diff_details.append(f"  - Missing slots in Block BAL: {len(diff.storage_missing_slots)}")
                if diff.storage_extra_slots:
                    diff_details.append(f"  - Extra slots in Block BAL: {len(diff.storage_extra_slots)}")
                if diff.storage_slot_diffs:
                    diff_details.append(f"  - Slots with value differences: {len(diff.storage_slot_diffs)}")

                norm_addr = normalize_hex(diff.address)
                if norm_addr in gen_accounts and norm_addr in block_accounts:
                    gen_data = gen_accounts[norm_addr]
                    block_data = block_accounts[norm_addr]

                    raw_data["accounts_with_storage_change_diffs"].append({
                        "address": diff.address,
                        "generated_storage_changes": gen_data.get('storageChanges', []),
                        "block_storage_changes": block_data.get('storageChanges', []),
                        "missing_slots": diff.storage_missing_slots,
                        "extra_slots": diff.storage_extra_slots,
                        "value_diffs": [vars(sd) for sd in diff.storage_slot_diffs]
                    })
                diff_details.append("")

        diff_text = "\n".join(diff_details)

        ai_analysis = run_ai_analysis(
            diff_type="Storage Change Differences",
            differences=diff_text,
            eip_context=eip_context,
            block_context=block_context,
            raw_data=raw_data if raw_data["accounts_with_storage_change_diffs"] else None,
            test_files=test_files
        )

        if ai_analysis:
            patterns.append(Pattern(
                pattern_type="STORAGE_CHANGE_ANALYSIS",
                description=f"AI analysis of storage change differences",
                severity="critical",
                evidence=[ai_analysis],
                affected_accounts=[d.address for d in storage_diffs],
                root_cause_hypothesis="",
                eip_reference="",
                debugging_steps=[]
            ))
            print("  Enhanced analysis completed", file=sys.stderr)
            return patterns

    # Fallback to rule-based pattern
    if total_missing_slots > 0:
        evidence = [
            f"Total missing storage slots across {len(storage_diffs)} accounts: {total_missing_slots}",
            "Affected accounts:"
        ]
        for diff in storage_diffs[:5]:
            if diff.storage_missing_slots:
                evidence.append(f"  • {diff.address}: {len(diff.storage_missing_slots)} missing slots")

        patterns.append(Pattern(
            pattern_type="STORAGE_CHANGE_EXCLUSION",
            description="Storage changes present in generated BAL but missing in block BAL",
            severity="critical",
            evidence=evidence,
            affected_accounts=[d.address for d in storage_diffs],
            root_cause_hypothesis=(
                "Storage changes (SSTORE operations) are not being recorded correctly in the block BAL. "
                "This could indicate: (1) writes during reverted calls being excluded, "
                "(2) storage changes in delegatecall contexts being missed, or "
                "(3) optimization that incorrectly filters 'redundant' writes."
            ),
            eip_reference="EIP-7928: 'Storage changes (SSTORE)' must be recorded with [block_access_index, new_value]",
            debugging_steps=[
                "Trace transactions with missing storage changes using debug_traceTransaction",
                "Check if missing writes occur in reverted calls or delegate contexts",
                "Verify SSTORE opcodes are being captured in all execution contexts",
                "Compare storage root changes between clients",
            ]
        ))

    return patterns


def analyze_balance_changes(report: BALReport, eip_context: Optional[str], block_entry: Optional[Dict] = None, test_files: Optional[Dict[str, Optional[str]]] = None) -> List[Pattern]:
    """Analyze balance change differences."""
    patterns = []

    balance_diffs = []
    for diff in report.account_diffs:
        if diff.balance_missing_txs or diff.balance_extra_txs or diff.balance_value_diffs:
            balance_diffs.append(diff)

    if not balance_diffs:
        return patterns

    # Run AI analysis if available and there are differences
    total_missing = sum(len(d.balance_missing_txs) for d in balance_diffs)
    total_value_diffs = sum(len(d.balance_value_diffs) for d in balance_diffs)

    if (total_missing > 0 or total_value_diffs > 0) and CLAUDE_SDK_AVAILABLE and eip_context:
        print("  Running enhanced analysis on balance change differences...", file=sys.stderr)

        block_context = f"""
Block: {report.block_number} ({shorten_hex(report.block_hash)})
Client: {report.client_info}
Total Transactions: {report.tx_context.total_count}
Accounts with balance change differences: {len(balance_diffs)}
"""

        diff_details = []
        diff_details.append(f"## Balance Change Differences ({len(balance_diffs)} accounts)")
        diff_details.append("")

        raw_data = {"accounts_with_balance_diffs": []}

        if block_entry:
            gen_bal = block_entry.get('generatedBlockAccessList', {})
            gen_accounts = {normalize_hex(acc.get('address')): acc for acc in gen_bal.get('accountChanges', [])}
            block_bal = block_entry.get('block', {}).get('blockAccessList', {})
            block_accounts = {normalize_hex(acc.get('address')): acc for acc in block_bal.get('accountChanges', [])}

            for i, diff in enumerate(balance_diffs[:10]):
                diff_details.append(f"### Account {i+1}: {diff.address}")
                if diff.balance_missing_txs:
                    diff_details.append(f"  - Missing balance changes (txs): {diff.balance_missing_txs}")
                if diff.balance_value_diffs:
                    diff_details.append(f"  - Balance value mismatches: {len(diff.balance_value_diffs)}")

                norm_addr = normalize_hex(diff.address)
                if norm_addr in gen_accounts and norm_addr in block_accounts:
                    gen_data = gen_accounts[norm_addr]
                    block_data = block_accounts[norm_addr]

                    raw_data["accounts_with_balance_diffs"].append({
                        "address": diff.address,
                        "generated_balance_changes": gen_data.get('balanceChanges', []),
                        "block_balance_changes": block_data.get('balanceChanges', []),
                        "missing_txs": diff.balance_missing_txs,
                        "value_diffs": diff.balance_value_diffs
                    })
                diff_details.append("")

        diff_text = "\n".join(diff_details)

        ai_analysis = run_ai_analysis(
            diff_type="Balance Change Differences",
            differences=diff_text,
            eip_context=eip_context,
            block_context=block_context,
            raw_data=raw_data if raw_data["accounts_with_balance_diffs"] else None,
            test_files=test_files
        )

        if ai_analysis:
            patterns.append(Pattern(
                pattern_type="BALANCE_CHANGE_ANALYSIS",
                description=f"AI analysis of balance change differences",
                severity="critical",
                evidence=[ai_analysis],
                affected_accounts=[d.address for d in balance_diffs],
                root_cause_hypothesis="",
                eip_reference="",
                debugging_steps=[]
            ))
            print("  Enhanced analysis completed", file=sys.stderr)
            return patterns

    # Fallback to rule-based patterns
    if total_missing > 0:
        evidence = [
            f"Missing balance changes across {len(balance_diffs)} accounts",
            f"Total missing balance updates: {total_missing}",
        ]
        for diff in balance_diffs[:5]:
            if diff.balance_missing_txs:
                tx_list = ', '.join([f"TX{tx}" for tx in diff.balance_missing_txs[:5]])
                evidence.append(f"  • {diff.address}: missing in {tx_list}")

        patterns.append(Pattern(
            pattern_type="BALANCE_CHANGE_EXCLUSION",
            description="Balance changes not recorded in block BAL",
            severity="critical",
            evidence=evidence,
            affected_accounts=[d.address for d in balance_diffs],
            root_cause_hypothesis=(
                "Balance changes are not being tracked correctly. This may occur when: "
                "(1) zero-value transfers are excluded, "
                "(2) gas payment balance changes are omitted, "
                "(3) self-destruct balance transfers are missed, or "
                "(4) balance changes in precompile calls are not recorded."
            ),
            eip_reference="EIP-7928: Balance changes recorded as [block_access_index, post_balance]",
            debugging_steps=[
                "Check if missing balance changes are from zero-value transfers",
                "Verify gas payment balance updates are recorded",
                "Trace SELFDESTRUCT operations and beneficiary balance changes",
                "Examine precompile calls for balance modifications",
            ]
        ))

    # Analyze value differences
    value_diffs_count = sum(len(d.balance_value_diffs) for d in balance_diffs)
    if value_diffs_count > 0:
        evidence = [
            f"Balance value mismatches in {value_diffs_count} transaction updates",
        ]
        for diff in balance_diffs[:3]:
            if diff.balance_value_diffs:
                for vd in diff.balance_value_diffs[:2]:
                    evidence.append(
                        f"  • {diff.address} TX{vd['txIndex']}: "
                        f"block={shorten_hex(vd['blockValue'])} vs "
                        f"generated={shorten_hex(vd['generatedValue'])}"
                    )

        patterns.append(Pattern(
            pattern_type="BALANCE_VALUE_MISMATCH",
            description="Post-balance values differ between block and generated BAL",
            severity="critical",
            evidence=evidence,
            affected_accounts=[d.address for d in balance_diffs if d.balance_value_diffs],
            root_cause_hypothesis=(
                "The post_balance values are calculated differently between clients. "
                "Possible causes: (1) gas accounting differences, "
                "(2) different handling of failed transfers, or "
                "(3) rounding or precision errors in balance calculations."
            ),
            eip_reference="EIP-7928: post_balance must reflect the account balance after the transaction",
            debugging_steps=[
                "Compare balance calculations step-by-step for affected transactions",
                "Check gas deduction and refund calculations",
                "Verify balance changes from failed value transfers",
                "Review balance snapshot timing (before vs after gas deduction)",
            ]
        ))

    return patterns


# Continue in the next section due to length...
def analyze_nonce_changes(report: BALReport, eip_context: Optional[str], block_entry: Optional[Dict] = None, test_files: Optional[Dict[str, Optional[str]]] = None) -> List[Pattern]:
    """Analyze nonce change differences."""
    patterns = []

    nonce_diffs = []
    for diff in report.account_diffs:
        if diff.nonce_missing_txs or diff.nonce_extra_txs or diff.nonce_value_diffs:
            nonce_diffs.append(diff)

    if not nonce_diffs:
        return patterns

    # Run AI analysis if available and there are differences
    total_missing = sum(len(d.nonce_missing_txs) for d in nonce_diffs)
    total_value_diffs = sum(len(d.nonce_value_diffs) for d in nonce_diffs)

    if (total_missing > 0 or total_value_diffs > 0) and CLAUDE_SDK_AVAILABLE and eip_context:
        print("  Running enhanced analysis on nonce change differences...", file=sys.stderr)

        block_context = f"""
Block: {report.block_number} ({shorten_hex(report.block_hash)})
Client: {report.client_info}
Total Transactions: {report.tx_context.total_count}
Accounts with nonce change differences: {len(nonce_diffs)}
"""

        diff_details = []
        diff_details.append(f"## Nonce Change Differences ({len(nonce_diffs)} accounts)")
        diff_details.append("")

        raw_data = {"accounts_with_nonce_diffs": []}

        if block_entry:
            gen_bal = block_entry.get('generatedBlockAccessList', {})
            gen_accounts = {normalize_hex(acc.get('address')): acc for acc in gen_bal.get('accountChanges', [])}
            block_bal = block_entry.get('block', {}).get('blockAccessList', {})
            block_accounts = {normalize_hex(acc.get('address')): acc for acc in block_bal.get('accountChanges', [])}

            for i, diff in enumerate(nonce_diffs[:10]):
                diff_details.append(f"### Account {i+1}: {diff.address}")
                if diff.nonce_missing_txs:
                    diff_details.append(f"  - Missing nonce changes (txs): {diff.nonce_missing_txs}")
                if diff.nonce_value_diffs:
                    diff_details.append(f"  - Nonce value mismatches: {len(diff.nonce_value_diffs)}")

                norm_addr = normalize_hex(diff.address)
                if norm_addr in gen_accounts and norm_addr in block_accounts:
                    gen_data = gen_accounts[norm_addr]
                    block_data = block_accounts[norm_addr]

                    raw_data["accounts_with_nonce_diffs"].append({
                        "address": diff.address,
                        "generated_nonce_changes": gen_data.get('nonceChanges', []),
                        "block_nonce_changes": block_data.get('nonceChanges', []),
                        "missing_txs": diff.nonce_missing_txs,
                        "value_diffs": diff.nonce_value_diffs
                    })
                diff_details.append("")

        diff_text = "\n".join(diff_details)

        ai_analysis = run_ai_analysis(
            diff_type="Nonce Change Differences",
            differences=diff_text,
            eip_context=eip_context,
            block_context=block_context,
            raw_data=raw_data if raw_data["accounts_with_nonce_diffs"] else None
        ,
            test_files=test_files
        )

        if ai_analysis:
            patterns.append(Pattern(
                pattern_type="NONCE_CHANGE_ANALYSIS",
                description=f"AI analysis of nonce change differences",
                severity="critical",
                evidence=[ai_analysis],
                affected_accounts=[d.address for d in nonce_diffs],
                root_cause_hypothesis="",
                eip_reference="",
                debugging_steps=[]
            ))
            print("  Enhanced analysis completed", file=sys.stderr)
            return patterns

    # Fallback to rule-based pattern
    if total_missing > 0:
        evidence = [
            f"Missing nonce changes across {len(nonce_diffs)} accounts",
        ]
        for diff in nonce_diffs[:5]:
            if diff.nonce_missing_txs:
                tx_list = ', '.join([f"TX{tx}" for tx in diff.nonce_missing_txs[:5]])
                evidence.append(f"  • {diff.address}: missing in {tx_list}")

        patterns.append(Pattern(
            pattern_type="NONCE_CHANGE_EXCLUSION",
            description="Nonce changes not recorded in block BAL",
            severity="critical",
            evidence=evidence,
            affected_accounts=[d.address for d in nonce_diffs],
            root_cause_hypothesis=(
                "Nonce increments are not being tracked. This typically occurs for: "
                "(1) transaction sender accounts (nonce always increments), "
                "(2) contract creation accounts (nonce set to 1), or "
                "(3) accounts in failed transactions (nonce still increments)."
            ),
            eip_reference="EIP-7928: Nonce changes recorded as [block_access_index, new_nonce]",
            debugging_steps=[
                "Verify nonce increments for transaction senders are recorded",
                "Check contract creation nonce initialization",
                "Confirm failed transaction nonce increments are captured",
            ]
        ))

    return patterns


def analyze_code_changes(report: BALReport, eip_context: Optional[str], block_entry: Optional[Dict] = None, test_files: Optional[Dict[str, Optional[str]]] = None) -> List[Pattern]:
    """Analyze code change differences."""
    patterns = []

    code_diffs = []
    for diff in report.account_diffs:
        if diff.code_missing_txs or diff.code_extra_txs or diff.code_value_diffs:
            code_diffs.append(diff)

    if not code_diffs:
        return patterns

    # Run AI analysis if available and there are differences
    total_missing = sum(len(d.code_missing_txs) for d in code_diffs)
    total_value_diffs = sum(len(d.code_value_diffs) for d in code_diffs)

    if (total_missing > 0 or total_value_diffs > 0) and CLAUDE_SDK_AVAILABLE and eip_context:
        print("  Running enhanced analysis on code change differences...", file=sys.stderr)

        block_context = f"""
Block: {report.block_number} ({shorten_hex(report.block_hash)})
Client: {report.client_info}
Total Transactions: {report.tx_context.total_count}
Accounts with code change differences: {len(code_diffs)}
"""

        diff_details = []
        diff_details.append(f"## Code Change Differences ({len(code_diffs)} accounts)")
        diff_details.append("")

        raw_data = {"accounts_with_code_diffs": []}

        if block_entry:
            gen_bal = block_entry.get('generatedBlockAccessList', {})
            gen_accounts = {normalize_hex(acc.get('address')): acc for acc in gen_bal.get('accountChanges', [])}
            block_bal = block_entry.get('block', {}).get('blockAccessList', {})
            block_accounts = {normalize_hex(acc.get('address')): acc for acc in block_bal.get('accountChanges', [])}

            for i, diff in enumerate(code_diffs[:10]):
                diff_details.append(f"### Account {i+1}: {diff.address}")
                if diff.code_missing_txs:
                    diff_details.append(f"  - Missing code changes (txs): {diff.code_missing_txs}")
                if diff.code_value_diffs:
                    diff_details.append(f"  - Code value mismatches: {len(diff.code_value_diffs)}")

                norm_addr = normalize_hex(diff.address)
                if norm_addr in gen_accounts and norm_addr in block_accounts:
                    gen_data = gen_accounts[norm_addr]
                    block_data = block_accounts[norm_addr]

                    raw_data["accounts_with_code_diffs"].append({
                        "address": diff.address,
                        "generated_code_changes": gen_data.get('codeChanges', []),
                        "block_code_changes": block_data.get('codeChanges', []),
                        "missing_txs": diff.code_missing_txs,
                        "value_diffs": diff.code_value_diffs
                    })
                diff_details.append("")

        diff_text = "\n".join(diff_details)

        ai_analysis = run_ai_analysis(
            diff_type="Code Change Differences",
            differences=diff_text,
            eip_context=eip_context,
            block_context=block_context,
            raw_data=raw_data if raw_data["accounts_with_code_diffs"] else None
        ,
            test_files=test_files
        )

        if ai_analysis:
            patterns.append(Pattern(
                pattern_type="CODE_CHANGE_ANALYSIS",
                description=f"AI analysis of code change differences",
                severity="critical",
                evidence=[ai_analysis],
                affected_accounts=[d.address for d in code_diffs],
                root_cause_hypothesis="",
                eip_reference="",
                debugging_steps=[]
            ))
            print("  Enhanced analysis completed", file=sys.stderr)
            return patterns

    # Fallback to rule-based pattern
    if total_missing > 0:
        evidence = [
            f"Missing code changes across {len(code_diffs)} accounts",
        ]
        for diff in code_diffs[:5]:
            if diff.code_missing_txs:
                tx_list = ', '.join([f"TX{tx}" for tx in diff.code_missing_txs[:5]])
                evidence.append(f"  • {diff.address}: missing in {tx_list}")

        patterns.append(Pattern(
            pattern_type="CODE_CHANGE_EXCLUSION",
            description="Code deployments not recorded in block BAL",
            severity="critical",
            evidence=evidence,
            affected_accounts=[d.address for d in code_diffs],
            root_cause_hypothesis=(
                "Contract deployments are not being tracked correctly. This may indicate: "
                "(1) CREATE/CREATE2 contract deployments being missed, "
                "(2) failed deployments not being recorded, or "
                "(3) code updates via SELFDESTRUCT+CREATE at same address being excluded."
            ),
            eip_reference="EIP-7928: Code changes recorded as [block_access_index, new_code]",
            debugging_steps=[
                "Trace CREATE/CREATE2 operations in affected transactions",
                "Check if failed contract deployments are being recorded",
                "Verify code deployment in edge cases (SELFDESTRUCT+CREATE same address)",
            ]
        ))

    return patterns


def analyze_storage_reads(report: BALReport, eip_context: Optional[str], block_entry: Optional[Dict] = None, test_files: Optional[Dict[str, Optional[str]]] = None) -> List[Pattern]:
    """Analyze storage read differences."""
    patterns = []

    read_diffs = []
    for diff in report.account_diffs:
        if diff.storage_missing_reads or diff.storage_extra_reads:
            read_diffs.append(diff)

    if not read_diffs:
        return patterns

    total_missing = sum(len(d.storage_missing_reads) for d in read_diffs)
    if total_missing > 0:
        # Run AI analysis if available
        if CLAUDE_SDK_AVAILABLE and eip_context:
            print("  Running enhanced analysis on storage read differences...", file=sys.stderr)

            block_context = f"""
Block: {report.block_number} ({shorten_hex(report.block_hash)})
Client: {report.client_info}
Total Transactions: {report.tx_context.total_count}
Accounts with storage read differences: {len(read_diffs)}
"""

            diff_details = []
            diff_details.append(f"## Storage Read Differences ({len(read_diffs)} accounts)")
            diff_details.append("")
            diff_details.append(f"These accounts have storage reads in Generated BAL but NOT in Block BAL.")
            diff_details.append("")

            raw_data = {"accounts_with_read_diffs": []}

            if block_entry:
                gen_bal = block_entry.get('generatedBlockAccessList', {})
                gen_accounts = {normalize_hex(acc.get('address')): acc for acc in gen_bal.get('accountChanges', [])}
                block_bal = block_entry.get('block', {}).get('blockAccessList', {})
                block_accounts = {normalize_hex(acc.get('address')): acc for acc in block_bal.get('accountChanges', [])}

                for i, diff in enumerate(read_diffs[:10]):
                    diff_details.append(f"### Account {i+1}: {diff.address}")
                    diff_details.append(f"  - Missing storage reads: {len(diff.storage_missing_reads)}")
                    diff_details.append(f"  - Slots: {', '.join([shorten_hex(s) for s in diff.storage_missing_reads[:5]])}")

                    norm_addr = normalize_hex(diff.address)
                    if norm_addr in gen_accounts and norm_addr in block_accounts:
                        gen_data = gen_accounts[norm_addr]
                        block_data = block_accounts[norm_addr]
                        diff_details.append(f"  - **Generated BAL**: {len(gen_data.get('storageReads', []))} storage reads")
                        diff_details.append(f"  - **Block BAL**: {len(block_data.get('storageReads', []))} storage reads")

                        raw_data["accounts_with_read_diffs"].append({
                            "address": diff.address,
                            "generated_storage_reads": gen_data.get('storageReads', []),
                            "block_storage_reads": block_data.get('storageReads', []),
                            "missing_reads": diff.storage_missing_reads
                        })
                    diff_details.append("")

            diff_text = "\n".join(diff_details)

            ai_analysis = run_ai_analysis(
                diff_type="Storage Read Differences",
                differences=diff_text,
                eip_context=eip_context,
                block_context=block_context,
                raw_data=raw_data if raw_data["accounts_with_read_diffs"] else None
            ,
            test_files=test_files
        )

            if ai_analysis:
                patterns.append(Pattern(
                    pattern_type="STORAGE_READ_ANALYSIS",
                    description=f"AI analysis of storage read differences",
                    severity="warning",
                    evidence=[ai_analysis],
                    affected_accounts=[d.address for d in read_diffs],
                    root_cause_hypothesis="",
                    eip_reference="",
                    debugging_steps=[]
                ))
                print("  Enhanced analysis completed", file=sys.stderr)
                return patterns

        # Fallback to rule-based pattern
        evidence = [
            f"Missing storage reads across {len(read_diffs)} accounts",
            f"Total missing read-only slots: {total_missing}",
        ]
        for diff in read_diffs[:5]:
            if diff.storage_missing_reads:
                evidence.append(f"  • {diff.address}: {len(diff.storage_missing_reads)} missing reads")

        patterns.append(Pattern(
            pattern_type="STORAGE_READ_EXCLUSION",
            description="Read-only storage accesses not recorded in block BAL",
            severity="warning",
            evidence=evidence,
            affected_accounts=[d.address for d in read_diffs],
            root_cause_hypothesis=(
                "SLOAD operations without corresponding SSTORE are being excluded. "
                "This may be intentional optimization or indicate: "
                "(1) reads in reverted calls being filtered, "
                "(2) reads that are later overwritten being consolidated, or "
                "(3) cached reads being deduplicated."
            ),
            eip_reference="EIP-7928: Storage reads are 'read-only storage keys' (no changes)",
            debugging_steps=[
                "Check if missing reads occur in reverted execution",
                "Verify if reads are being deduplicated across block",
                "Trace SLOAD operations in affected transactions",
            ]
        ))

    return patterns


def analyze_account_presence(report: BALReport, eip_context: Optional[str], block_entry: Optional[Dict] = None, test_files: Optional[Dict[str, Optional[str]]] = None) -> List[Pattern]:
    """Analyze missing/extra account patterns with optional enhanced analysis."""
    patterns = []

    # Prepare context for enhanced analysis
    if report.missing_accounts and CLAUDE_SDK_AVAILABLE and eip_context:
        print("  Running enhanced analysis on account differences...", file=sys.stderr)

        block_context = f"""
Block: {report.block_number} ({shorten_hex(report.block_hash)})
Client: {report.client_info}
Total Transactions: {report.tx_context.total_count}
Missing Accounts: {len(report.missing_accounts)}
Transaction Participants Among Missing: {len(report.missing_tx_participants)}
"""

        # Format differences with actual BAL data
        diff_details = []
        diff_details.append(f"## Accounts in Generated BAL but NOT in Block BAL ({len(report.missing_accounts)} total)")
        diff_details.append("")
        diff_details.append(f"These accounts appear in Besu's generated BAL but are absent from the block BAL (from {report.client_info}).")
        diff_details.append(f"We need to determine which client's implementation is correct.")
        diff_details.append("")

        # Prepare raw data structure
        raw_data = {
            "accounts_only_in_generated": [],
            "accounts_in_both_bals": []
        }

        # Get actual BAL data for missing accounts if block_entry provided
        if block_entry:
            gen_bal = block_entry.get('generatedBlockAccessList', {})
            gen_accounts = {normalize_hex(acc.get('address')): acc for acc in gen_bal.get('accountChanges', [])}
            block_bal = block_entry.get('block', {}).get('blockAccessList', {})
            block_accounts = {normalize_hex(acc.get('address')): acc for acc in block_bal.get('accountChanges', [])}

            # Get common accounts for comparison (show what IS included)
            common_addrs = set(gen_accounts.keys()) & set(block_accounts.keys())
            comparison_sample = list(common_addrs)[:2]  # Take 2 examples

            for i, addr in enumerate(report.missing_accounts[:10]):
                txs = report.tx_context.find_transactions_for_account(addr)
                is_zero = addr == '0x0000000000000000000000000000000000000000'

                diff_details.append(f"### Account {i+1}: {addr}")
                diff_details.append(f"  - Zero address: {'YES' if is_zero else 'NO'}")
                diff_details.append(f"  - Transaction participant: {'YES' if addr in [normalize_hex(a) for a in report.missing_tx_participants] else 'NO'}")

                if txs:
                    diff_details.append(f"  - Appears in transactions: {', '.join([f'TX{tx.index}' for tx in txs[:5]])}")
                    for tx in txs[:2]:
                        diff_details.append(f"    - {tx.short_desc()}")

                # Add actual BAL data from generated BAL
                norm_addr = normalize_hex(addr)
                if norm_addr in gen_accounts:
                    gen_account_data = gen_accounts[norm_addr]
                    diff_details.append(f"  - **Besu's Generated BAL data**: {len(gen_account_data.get('storageChanges', []))} storage, {len(gen_account_data.get('balanceChanges', []))} balance, {len(gen_account_data.get('nonceChanges', []))} nonce, {len(gen_account_data.get('codeChanges', []))} code changes")
                    diff_details.append(f"  - **Block BAL data**: NOT PRESENT (excluded by {report.client_info})")

                    # Add to raw data
                    raw_data["accounts_only_in_generated"].append({
                        "address": addr,
                        "besu_generated_data": gen_account_data,
                        "block_bal_data": None
                    })

                diff_details.append("")

            # Add comparison accounts (what IS included in both)
            if comparison_sample:
                diff_details.append("")
                diff_details.append("## Comparison: Accounts Present in BOTH BALs")
                diff_details.append("")
                diff_details.append(f"These accounts are included by both {report.client_info} AND Besu.")
                diff_details.append("This helps identify what makes accounts 'includable' vs 'excludable' in each implementation.")
                diff_details.append("")
                for addr in comparison_sample:
                    diff_details.append(f"### {addr}")
                    if addr in gen_accounts:
                        gen_data = gen_accounts[addr]
                        diff_details.append(f"  - **Besu's Generated BAL**: {len(gen_data.get('storageChanges', []))} storage, {len(gen_data.get('balanceChanges', []))} balance, {len(gen_data.get('nonceChanges', []))} nonce, {len(gen_data.get('codeChanges', []))} code")
                    if addr in block_accounts:
                        block_data = block_accounts[addr]
                        diff_details.append(f"  - **Block BAL ({report.client_info})**: {len(block_data.get('storageChanges', []))} storage, {len(block_data.get('balanceChanges', []))} balance, {len(block_data.get('nonceChanges', []))} nonce, {len(block_data.get('codeChanges', []))} code")

                        # Add to raw data for comparison
                        raw_data["accounts_in_both_bals"].append({
                            "address": addr,
                            "besu_generated_data": gen_accounts.get(addr, {}),
                            "block_bal_data": block_data
                        })
                    diff_details.append("")

        else:
            # Fallback if no block_entry provided
            for i, addr in enumerate(report.missing_accounts[:10]):
                txs = report.tx_context.find_transactions_for_account(addr)
                is_zero = addr == '0x0000000000000000000000000000000000000000'
                diff_details.append(f"### Account {i+1}: {addr}")
                diff_details.append(f"  - Zero address: {'YES' if is_zero else 'NO'}")
                diff_details.append(f"  - Transaction participant: {'YES' if addr in [normalize_hex(a) for a in report.missing_tx_participants] else 'NO'}")
                if txs:
                    diff_details.append(f"  - Appears in transactions: {', '.join([f'TX{tx.index}' for tx in txs[:5]])}")
                    for tx in txs[:2]:
                        diff_details.append(f"    - {tx.short_desc()}")
                diff_details.append("")

        if len(report.missing_accounts) > 10:
            diff_details.append(f"... and {len(report.missing_accounts) - 10} more accounts")

        diff_text = "\n".join(diff_details)

        # Get AI analysis with raw data
        ai_analysis = run_ai_analysis(
            diff_type="Account Differences Between Block BAL and Generated BAL",
            differences=diff_text,
            eip_context=eip_context,
            block_context=block_context,
            raw_data=raw_data if raw_data["accounts_only_in_generated"] else None
        ,
            test_files=test_files
        )

        if ai_analysis:
            # Create a pattern from enhanced analysis
            patterns.append(Pattern(
                pattern_type="DETAILED_BAL_COMPARISON",
                description=f"Detailed analysis comparing {report.client_info} Block BAL vs Besu Generated BAL",
                severity="critical",
                evidence=[ai_analysis],
                affected_accounts=report.missing_accounts,
                root_cause_hypothesis="",
                eip_reference="",
                debugging_steps=[]
            ))
            print("  Enhanced analysis completed", file=sys.stderr)

    # Zero address pattern (rule-based fallback)
    zero_addr = '0x0000000000000000000000000000000000000000'
    if zero_addr in [normalize_hex(a) for a in report.missing_accounts]:
        txs = report.tx_context.find_transactions_for_account(zero_addr)
        evidence = [f"Zero address appears in {len(txs)} transactions"]
        for tx in txs[:3]:
            evidence.append(f"  • {tx.short_desc()}")
        evidence.append(f"Zero address is used as a contract call target")

        patterns.append(Pattern(
            pattern_type="ZERO_ADDRESS_EXCLUSION",
            description="Zero address called as contract but excluded from block BAL",
            severity="critical",
            evidence=evidence,
            affected_accounts=[zero_addr],
            root_cause_hypothesis=(
                "Client's BAL implementation has a filter that excludes the zero address "
                "from being recorded. However, EIP-7928 requires ALL call targets to be included, "
                "even special addresses like 0x0."
            ),
            eip_reference="EIP-7928 Scope: 'Targets of CALL, CALLCODE, DELEGATECALL, STATICCALL (even if they revert)' MUST be included.",
            debugging_steps=[
                "Use debug_traceTransaction to confirm zero address is actually called",
                "Check client's BAL recording code for address filtering logic",
                "Verify if calls to zero address are reverting or executing",
                "Review EIP-7928 compliance for special address handling",
            ]
        ))

    # Transaction participant pattern (rule-based)
    if report.missing_accounts and len(report.missing_tx_participants) == len(report.missing_accounts):
        evidence = [
            f"100% of missing accounts ({len(report.missing_accounts)}) are transaction participants",
            f"0% are non-participant addresses (accessed via opcodes)"
        ]
        for addr in report.missing_tx_participants[:5]:
            txs = report.tx_context.find_transactions_for_account(addr)
            tx_list = ', '.join([f"TX{tx.index}" for tx in txs[:5]])
            evidence.append(f"  • {addr} in {tx_list}")

        patterns.append(Pattern(
            pattern_type="TX_PARTICIPANT_EXCLUSION",
            description="All missing accounts are explicit transaction 'to' addresses",
            severity="critical",
            evidence=evidence,
            affected_accounts=report.missing_tx_participants,
            root_cause_hypothesis=(
                "Client appears to filter out certain transaction targets from the BAL. "
                "This systematic exclusion suggests: "
                "(1) calls that revert are being excluded, "
                "(2) calls to non-existent contracts (no code) are filtered, "
                "(3) calls with no state changes are optimized away, or "
                "(4) precompile calls are being handled differently."
            ),
            eip_reference="EIP-7928 Scope: 'Transaction sender and recipient addresses (even for zero-value transfers)' MUST be included.",
            debugging_steps=[
                "Trace each missing account's transactions to see execution outcome",
                "Check if these addresses have deployed code (eth_getCode)",
                "Verify if calls revert and check client's handling of reverted calls",
                "Review whether missing accounts are precompiles (0x01-0x09, 0x0a, etc.)",
                "Compare touched addresses set between clients for same block",
            ]
        ))

    return patterns


def detect_patterns(report: BALReport, eip_context: Optional[str] = None, block_entry: Optional[Dict] = None, test_files: Optional[Dict[str, Optional[str]]] = None) -> List[Pattern]:
    """Detect patterns in BAL differences with enhanced EIP-7928 analysis."""
    patterns = []

    # Analyze each type of difference - all with AI analysis capability
    patterns.extend(analyze_account_presence(report, eip_context, block_entry, test_files))
    patterns.extend(analyze_storage_changes(report, eip_context, block_entry, test_files))
    patterns.extend(analyze_storage_reads(report, eip_context, block_entry, test_files))
    patterns.extend(analyze_balance_changes(report, eip_context, block_entry, test_files))
    patterns.extend(analyze_nonce_changes(report, eip_context, block_entry, test_files))
    patterns.extend(analyze_code_changes(report, eip_context, block_entry, test_files))

    return patterns


def run_multi_agent_analysis(
    report: BALReport,
    block_entry: Dict,
    eip_context: Optional[str] = None,
    test_files: Optional[Dict[str, Optional[str]]] = None,
    branch: str = "bal-devnet-0",
    keep_repos: bool = False,
) -> str:
    """
    Run multi-agent BAL analysis with improved methodology.

    This is the new approach that:
    1. Downloads and analyzes client implementation code
    2. Deep-dives into BAL differences with operation sequences
    3. Generates comprehensive report with journal invariants, decision tables, etc.

    Args:
        report: BAL comparison report
        block_entry: Raw block data from bad_blocks.json
        eip_context: EIP-7928 specification text
        test_files: EIP-7928 test suite files
        branch: Git branch to checkout (default: bal-devnet-0)
        keep_repos: If True, preserve cloned repositories for debugging

    Returns:
        Comprehensive bug report as markdown string (includes analysis from all agents)
    """
    try:
        from .agents import run_multi_agent_analysis as run_agents
        return run_agents(
            report=report,
            block_entry=block_entry,
            eip_context=eip_context,
            test_files=test_files,
            branch=branch,
            keep_repos=keep_repos,
        )
    except ImportError as e:
        print(f"Warning: Multi-agent system not available: {e}", file=sys.stderr)
        print("Falling back to standard pattern detection", file=sys.stderr)

        # Fallback to legacy analysis
        patterns = detect_patterns(report, eip_context, block_entry, test_files)

        # Format patterns into a simple report
        lines = [
            "# BAL Analysis Report",
            "",
            f"**Note**: Multi-agent analysis not available, using legacy pattern detection",
            "",
            "## Detected Patterns",
            "",
        ]

        for pattern in patterns:
            lines.append(f"### {pattern.pattern_type}")
            lines.append(f"**Severity**: {pattern.severity}")
            lines.append(f"**Description**: {pattern.description}")
            lines.append("")

            if pattern.evidence:
                lines.append("**Evidence**:")
                for evidence in pattern.evidence:
                    lines.append(evidence)
                lines.append("")

        return "\n".join(lines)
