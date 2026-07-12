"""
Report Generator Agent

Synthesizes findings from codebase and difference analyzers to create
world-class bug reports following the improved methodology:
- Journal coverage invariants
- Decision trees/tables
- Implementation panes
- Root cause templates
- EIP-7928 compliance analysis
"""

import sys
import json
from typing import Dict, List, Optional

try:
    import anyio
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ThinkingBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False

from ..models import BALReport
from ..utils import shorten_hex
from .shared_context import CodebaseContext, DifferenceContext


def build_report_prompt(
    report: BALReport,
    codebase_ctx: CodebaseContext,
    diff_ctx: DifferenceContext,
    eip_context: Optional[str],
    test_files: Optional[Dict[str, Optional[str]]],
    block_entry: Dict,
) -> str:
    """
    Build comprehensive prompt for report generation following improved methodology.
    """
    prompt_parts = [
        "# BAL Bug Analysis and Report Generation",
        "",
        "You are tasked with generating a world-class bug report for a Block Access List (BAL) inconsistency",
        "between two Ethereum client implementations. Use extended thinking to deeply analyze the root cause.",
        "",
        "## Context Overview",
        "",
        f"**Block**: {report.block_number} ({shorten_hex(report.block_hash)})",
        f"**Block Client**: {report.client_info}",
        f"**Comparing Against**: Besu (generated BAL)",
        f"**Transactions**: {report.tx_context.total_count}",
        "",
        "**CRITICAL**: We do NOT know which implementation is correct. Analyze objectively.",
        "",
    ]

    # 1. CODEBASE CONTEXT
    prompt_parts.extend([
        "## 1. Codebase Analysis Context",
        "",
        f"**Client**: {codebase_ctx.client_name} {codebase_ctx.client_version}",
        f"**Repository**: {codebase_ctx.repo_url}",
        f"**Branch**: {codebase_ctx.branch}",
        "",
    ])

    if codebase_ctx.clone_success:
        prompt_parts.append(f"**BAL Implementation Files** ({len(codebase_ctx.bal_implementation_files)} found):")
        for file in codebase_ctx.bal_implementation_files[:10]:
            prompt_parts.append(f"- {file}")
        prompt_parts.append("")

        if codebase_ctx.journal_code:
            prompt_parts.append("**Journal/Change Tracking Code**:")
            for section in codebase_ctx.journal_code[:3]:
                prompt_parts.extend([
                    f"",
                    f"File: {section.file_path}:{section.start_line}-{section.end_line}",
                    f"Description: {section.description}",
                    f"Relevance: {section.relevance}",
                    f"```",
                    f"{section.code[:500]}",  # Limit code length
                    f"```",
                ])

        if codebase_ctx.sload_sstore_tracking:
            prompt_parts.append("")
            prompt_parts.append("**SLOAD/SSTORE Tracking Code**:")
            for section in codebase_ctx.sload_sstore_tracking[:3]:
                prompt_parts.extend([
                    f"",
                    f"File: {section.file_path}:{section.start_line}-{section.end_line}",
                    f"Description: {section.description}",
                    f"```",
                    f"{section.code[:500]}",
                    f"```",
                ])

        if codebase_ctx.snapshot_restore_code:
            prompt_parts.append("")
            prompt_parts.append("**Snapshot/Restore Code**:")
            for section in codebase_ctx.snapshot_restore_code[:2]:
                prompt_parts.extend([
                    f"",
                    f"File: {section.file_path}:{section.start_line}-{section.end_line}",
                    f"Description: {section.description}",
                    f"```",
                    f"{section.code[:500]}",
                    f"```",
                ])

        prompt_parts.append("")
    else:
        prompt_parts.append(f"**Repository Clone Failed**: {codebase_ctx.clone_error}")
        prompt_parts.append("Proceeding with limited codebase context.")
        prompt_parts.append("")

    # 2. DIFFERENCE ANALYSIS CONTEXT
    prompt_parts.extend([
        "## 2. Difference Analysis Context",
        "",
        f"**Total Affected Accounts**: {diff_ctx.total_affected_accounts}",
        f"**Missing in Block BAL**: {diff_ctx.total_missing_in_block_bal}",
        f"**Extra in Block BAL**: {diff_ctx.total_extra_in_block_bal}",
        "",
        "**Account Categories**:",
        f"- Transaction participants: {len(diff_ctx.tx_participant_accounts)}",
        f"- Opcode-accessed: {len(diff_ctx.opcode_accessed_accounts)}",
        f"- Special addresses (0x0, precompiles): {len(diff_ctx.special_addresses)}",
        "",
        "**Difference Types**:",
        f"- Storage reads: {diff_ctx.has_storage_read_diffs}",
        f"- Storage changes: {diff_ctx.has_storage_change_diffs}",
        f"- Balance changes: {diff_ctx.has_balance_diffs}",
        f"- Nonce changes: {diff_ctx.has_nonce_diffs}",
        f"- Code changes: {diff_ctx.has_code_diffs}",
        "",
    ])

    # Operation sequences
    if diff_ctx.operation_sequences:
        prompt_parts.append("**Operation Sequences** (showing patterns of ops → BAL state):")
        prompt_parts.append("")
        for seq in diff_ctx.operation_sequences[:10]:
            prompt_parts.append(f"Account: {seq.account}")
            if seq.slot:
                prompt_parts.append(f"  Slot: {seq.slot}")
            prompt_parts.append(f"  TX{seq.tx_index}: {', '.join([op.value for op in seq.operations])}")
            prompt_parts.append(f"  Result: {seq.tx_result.value}")
            prompt_parts.append(f"  Generated BAL: {seq.actual_in_generated_bal}")
            prompt_parts.append(f"  Block BAL: {seq.actual_in_block_bal}")
            if seq.has_mismatch:
                prompt_parts.append(f"  ❌ {seq.mismatch_description}")
            prompt_parts.append("")

    # Read/Write mismatches
    if diff_ctx.read_write_mismatches:
        prompt_parts.append("**Storage Read/Write Cross-References** (CRITICAL PATTERN):")
        prompt_parts.append("")
        prompt_parts.append("These slots appear as READS in one BAL but WRITES in another.")
        prompt_parts.append("This often indicates journal coverage or SLOAD/SSTORE tracking bugs.")
        prompt_parts.append("")
        for mismatch in diff_ctx.read_write_mismatches[:5]:
            prompt_parts.append(f"- Account: {mismatch['account']}")
            prompt_parts.append(f"  Slot: {mismatch['slot']}")
            prompt_parts.append(f"  Pattern: {mismatch['pattern']}")
            prompt_parts.append(f"  {mismatch['description']}")
            prompt_parts.append("")

    # 3. RAW BAL DATA
    prompt_parts.extend([
        "## 3. Raw BAL Data",
        "",
        "Sample of actual BAL structures for verification:",
        "",
    ])

    gen_bal = block_entry.get('generatedBlockAccessList', {})
    block_bal = block_entry.get('block', {}).get('blockAccessList', {})

    # Show a few example accounts
    gen_accounts = gen_bal.get('accountChanges', [])[:3]
    block_accounts = block_bal.get('accountChanges', [])[:3]

    prompt_parts.append("**Generated BAL (Besu) Sample**:")
    prompt_parts.append(f"```json")
    prompt_parts.append(json.dumps(gen_accounts, indent=2)[:2000])  # Limit length
    prompt_parts.append(f"```")
    prompt_parts.append("")

    prompt_parts.append("**Block BAL Sample**:")
    prompt_parts.append(f"```json")
    prompt_parts.append(json.dumps(block_accounts, indent=2)[:2000])
    prompt_parts.append(f"```")
    prompt_parts.append("")

    # 4. EIP-7928 SPECIFICATION
    if eip_context:
        prompt_parts.extend([
            "## 4. EIP-7928 Specification (Ground Truth)",
            "",
            "```markdown",
            eip_context[:8000],  # Include substantial portion
            "```",
            "",
        ])

    # 5. TEST SUITE CONTEXT
    if test_files:
        prompt_parts.append("## 5. EIP-7928 Test Suite")
        prompt_parts.append("")
        prompt_parts.append("Use these to identify missing test scenarios.")
        prompt_parts.append("")

        for filename, content in test_files.items():
            if content and filename.endswith('.md'):  # Show test case documentation
                prompt_parts.append(f"### {filename}")
                prompt_parts.append(f"```markdown")
                prompt_parts.append(content[:1500])
                prompt_parts.append(f"```")
                prompt_parts.append("")
                break  # Just show one for context

    # 6. REPORT GENERATION INSTRUCTIONS
    prompt_parts.extend([
        "## Report Generation Instructions",
        "",
        "Generate a comprehensive bug report following this EXACT structure:",
        "",
        "### 1. ROOT CAUSE TEMPLATE",
        "",
        "**Spec Requirement**: (Direct quote from EIP-7928 that is violated)",
        "",
        "**Journal Coverage Invariant**: (Define the invariant that should hold)",
        "- Format: 'For every [state mutation type], a corresponding journal entry must...'",
        "",
        "**Failing Scenario Trace**: (3-5 line pseudo-log showing bug)",
        "```",
        "1. TX starts",
        "2. SLOAD slot 0x123 (new read)",
        "3. TX reverts",
        "4. Restore called, but no journal entry for SLOAD",
        "5. Storage read persists incorrectly",
        "```",
        "",
        "**Code Sketch**: (KISS explanation of the bug, 5-10 lines pseudocode)",
        "```python",
        "# INCORRECT (current implementation)",
        "def on_sload(slot):",
        "    storage_reads.add(slot)",
        "    # BUG: no journal entry created",
        "",
        "# CORRECT (should be)",
        "def on_sload(slot):",
        "    if slot not in storage_reads:",
        "        journal.push(ChangeType.StorageRead, slot)",
        "        storage_reads.add(slot)",
        "```",
        "",
        "**Test Case Proposal**: (Minimum test to demonstrate bug)",
        "",
        "**Resolution**: (1-2 sentences on primary fix needed)",
        "",
        "**Risk Analysis**:",
        "- Consensus impact: [yes/no and why]",
        "- DB migration needed: [yes/no]",
        "- Hash invariants affected: [yes/no]",
        "",
        "---",
        "",
        "### 2. DECISION TREE / OPERATION TABLE",
        "",
        "Create a markdown table mapping operation sequences to BAL state:",
        "",
        "| Operation Sequence | Tx Result | Storage Reads | Storage Changes | Should Appear in BAL? | Block BAL ✓/✗ | Generated BAL ✓/✗ |",
        "|-------------------|-----------|---------------|-----------------|----------------------|---------------|-------------------|",
        "| SLOAD             | Success   | +slot         | -               | Yes (read only)      | ✗             | ✓                 |",
        "| SLOAD→SSTORE      | Success   | -             | +slot           | Yes (write only)     | ✓             | ✓                 |",
        "| SLOAD→SSTORE      | Revert    | -             | -               | No (reverted)        | ?             | ?                 |",
        "",
        "Fill in based on actual patterns found in the data.",
        "",
        "---",
        "",
        "### 3. IMPLEMENTATION PANES",
        "",
        "**Conceptual Diff**:",
        "- What needs to change in the implementation",
        "",
        "**Incorrect Pattern** (from codebase analysis):",
        "```",
        "[Show actual code or pseudocode of buggy pattern]",
        "```",
        "",
        "**Correct Pattern**:",
        "```",
        "[Show how it should work]",
        "```",
        "",
        "**Narrative Explanation**: (2-3 sentences explaining the fix)",
        "",
        "**Invariant Guarantee**: (What invariant this fix ensures)",
        "",
        "**Regression Testing**:",
        "- Test case 1: [Specific scenario]",
        "- Test case 2: [Edge case]",
        "- Test case 3: [Interaction with other features]",
        "",
        "---",
        "",
        "### 4. EIP-7928 COMPLIANCE ANALYSIS",
        "",
        "**Requirement Analysis**:",
        "Quote 2-3 specific requirements from EIP-7928 and analyze compliance:",
        "",
        '1. EIP-7928: "..." (quote)',
        "   - Besu compliance: ✓/✗ [explanation]",
        f"   - {codebase_ctx.client_name} compliance: ✓/✗ [explanation]",
        "",
        "**Verdict**: Which client is EIP-7928 compliant and why",
        "",
        "---",
        "",
        "### 5. DEBUGGING RECOMMENDATIONS",
        "",
        "Provide 5-7 concrete debugging steps with specific commands and file references:",
        "",
        "1. **Verify the bug exists**:",
        f"   - Run: `debug_traceBlockByNumber {report.block_number}`",
        "   - Check: Compare SLOAD operations with BAL storage reads",
        "",
        "2. **Locate journal code** (if codebase analysis succeeded):",
        f"   - File: {codebase_ctx.bal_implementation_files[0] if codebase_ctx.bal_implementation_files else '[search for ChangeType or Journal class]'}",
        "   - Look for: SLOAD handling in journal push operations",
        "",
        "3. **Create minimal reproduction**:",
        "   - [Specific test scenario based on failing pattern]",
        "",
        "4. **Validate fix**:",
        "   - [How to verify the fix works]",
        "",
        "---",
        "",
        "### 6. CLOSING CHECKLIST",
        "",
        "Systematic validation questions:",
        "",
        "- [ ] Is every BAL-relevant state mutation journaled?",
        "- [ ] Can every journaled change be undone with no residual effect?",
        "- [ ] Does this fix change consensus rules or break compatibility?",
        "- [ ] Are hash invariants preserved (BAL hash must be deterministic)?",
        "- [ ] Have we added tests to prevent regression?",
        "",
        "---",
        "",
        "### 7. EXECUTIVE SUMMARY",
        "",
        "(Write this last, after deep analysis)",
        "",
        "**Status**: CRITICAL/WARNING",
        "",
        "**Finding**: (1-2 sentence summary)",
        "",
        "**Compliant Client**: [Name] - (why)",
        "",
        "**Bug Location**: (Specific component/file if known)",
        "",
        "**Impact**: (What breaks if unresolved)",
        "",
        "**Recommended Action**: (Primary next step)",
        "",
        "---",
        "",
        "## Important Guidelines",
        "",
        "1. **Use Extended Thinking**: Take time to deeply analyze root cause before generating report",
        "2. **Be Objective**: Do not assume either client is correct",
        "3. **Be Specific**: Use actual file paths, line numbers, account addresses, slot numbers",
        "4. **Use Evidence**: Reference actual operation sequences and code sections provided",
        "5. **Quote EIP-7928**: Use direct quotes with markdown backticks",
        "6. **Focus on Invariants**: Frame bugs in terms of violated journal/state invariants",
        "7. **Be Actionable**: Every debugging step should have specific commands or file locations",
        "",
        "Now generate the comprehensive bug report following this structure exactly.",
    ])

    return "\n".join(prompt_parts)


async def generate_report_with_ai(
    report: BALReport,
    codebase_ctx: CodebaseContext,
    diff_ctx: DifferenceContext,
    eip_context: Optional[str],
    test_files: Optional[Dict[str, Optional[str]]],
    block_entry: Dict,
) -> str:
    """
    Use Claude Agent SDK with extended thinking to generate comprehensive report.
    """
    if not CLAUDE_SDK_AVAILABLE:
        return "AI report generation not available (Claude SDK not installed)"

    print(f"  Building comprehensive analysis prompt...", file=sys.stderr)
    prompt = build_report_prompt(report, codebase_ctx, diff_ctx, eip_context, test_files, block_entry)

    print(f"  Invoking Claude with ultra-thinking mode...", file=sys.stderr)

    options = ClaudeAgentOptions(
        max_turns=5,  # Allow more turns for deep analysis
        system_prompt=(
            "You are an elite Ethereum client developer and EIP-7928 expert. "
            "You specialize in root cause analysis of BAL implementation bugs. "
            "Use extended thinking to deeply analyze the evidence before generating your report. "
            "Your reports are known for precision, actionability, and systematic invariant-based analysis. "
            "Follow the report structure exactly. Be specific, use evidence, and think like a compiler engineer."
        )
    )

    response_parts = []
    thinking_summaries = []

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_parts.append(block.text)
                    elif isinstance(block, ThinkingBlock):
                        # Capture thinking for transparency
                        thinking_summaries.append(f"[Thinking: {len(block.thinking)} chars]")

        if thinking_summaries:
            print(f"  Agent used extended thinking: {len(thinking_summaries)} blocks", file=sys.stderr)

    except Exception as e:
        print(f"  Error: Report generation failed: {e}", file=sys.stderr)
        return f"Error generating AI report: {str(e)}"

    return "\n".join(response_parts) if response_parts else "No report generated"


def generate_report(
    report: BALReport,
    codebase_ctx: CodebaseContext,
    diff_ctx: DifferenceContext,
    eip_context: Optional[str],
    test_files: Optional[Dict[str, Optional[str]]],
    block_entry: Dict,
) -> str:
    """
    Main entry point for report generation.

    Returns:
        Comprehensive bug report as markdown string
    """
    print(f"\nReport Generator Agent:", file=sys.stderr)
    print(f"  Synthesizing findings from codebase and difference analysis...", file=sys.stderr)

    if not CLAUDE_SDK_AVAILABLE:
        print(f"  Warning: Claude SDK not available, using fallback report", file=sys.stderr)
        return generate_fallback_report(report, codebase_ctx, diff_ctx)

    # Generate with AI
    ai_report = anyio.run(
        generate_report_with_ai,
        report,
        codebase_ctx,
        diff_ctx,
        eip_context,
        test_files,
        block_entry,
    )

    print(f"  Report generation complete ({len(ai_report)} chars)", file=sys.stderr)

    return ai_report


def generate_fallback_report(
    report: BALReport,
    codebase_ctx: CodebaseContext,
    diff_ctx: DifferenceContext,
) -> str:
    """
    Fallback report generation when AI is not available.
    """
    lines = [
        "# BAL Analysis Report",
        "",
        f"## Block {report.block_number}",
        f"**Client**: {report.client_info}",
        "",
        "## Summary",
        f"- Missing accounts: {diff_ctx.total_missing_in_block_bal}",
        f"- Storage read differences: {diff_ctx.has_storage_read_diffs}",
        f"- Storage change differences: {diff_ctx.has_storage_change_diffs}",
        "",
        "## Codebase Context",
        f"Client: {codebase_ctx.client_name} {codebase_ctx.client_version}",
        f"Repository: {codebase_ctx.repo_url}",
        "",
        "## Patterns Detected",
        f"- Read/write mismatches: {len(diff_ctx.read_write_mismatches)}",
        "",
        "*Note: Full AI-powered analysis requires Claude SDK installation*",
    ]

    return "\n".join(lines)
