"""
Command-line interface for Baloor

Main entry point for the CLI tool with argument parsing and execution logic.
"""

import json
import sys
import argparse
from datetime import datetime

from .comparisons import compare_block
from .analysis import fetch_eip_7928, fetch_test_files, detect_patterns, run_multi_agent_analysis
from .formatters import format_comprehensive_report, format_multi_block_analysis
from .utils import (
    normalize_hex,
    shorten_hex,
    fetch_bad_blocks_from_besu,
    fetch_block_by_number,
    fetch_block_by_hash,
    fetch_transaction_receipt,
    debug_trace_transaction,
)


def fetch_client_debug_info(client_rpc: str, report, block_entry) -> str:
    """
    Fetch additional debugging information from the client RPC that produced the bad block.

    Args:
        client_rpc: Client RPC endpoint URL (Nethermind, Reth, Geth, etc.)
        report: BALReport object with block information
        block_entry: Original block entry from debug_getBadBlocks (contains full transaction list)

    Returns:
        Formatted debug information as string
    """
    debug_info = []
    debug_info.append("\n" + "=" * 80)
    debug_info.append("CLIENT DEBUG INFORMATION")
    debug_info.append("=" * 80)

    block_hash = report.block_hash
    block_number = report.block_number

    debug_info.append(f"\nAnalyzing block {block_number} ({block_hash})...")
    debug_info.append(f"Client: {report.client_info}")

    # Get transactions from the bad block data (already available)
    transactions = block_entry.get('block', {}).get('transactions', [])
    debug_info.append(f"\nTotal Transactions: {len(transactions)}")

    # Fetch receipts and analyze transaction outcomes
    debug_info.append("\nTransaction Receipt Analysis:")

    if transactions:
        success_count = 0
        failed_count = 0

        for idx, tx in enumerate(transactions[:10]):  # Limit to first 10 for brevity
            tx_hash = tx.get('hash') if isinstance(tx, dict) else tx
            debug_info.append(f"\n  Transaction {idx}: {tx_hash}")

            if isinstance(tx, dict):
                debug_info.append(f"    From: {tx.get('from', 'N/A')}")
                to_addr = tx.get('to')
                debug_info.append(f"    To: {to_addr if to_addr else 'contract creation'}")
                debug_info.append(f"    Value: {tx.get('value', 'N/A')}")
                debug_info.append(f"    Gas Limit: {tx.get('gas', 'N/A')}")

            # Fetch receipt from client
            receipt = fetch_transaction_receipt(client_rpc, tx_hash)
            if receipt:
                status = receipt.get('status') == '0x1'
                if status:
                    success_count += 1
                    debug_info.append(f"    Status: ✓ Success")
                else:
                    failed_count += 1
                    debug_info.append(f"    Status: ✗ Failed")
                debug_info.append(f"    Gas Used: {receipt.get('gasUsed', 'N/A')}")

                # Show contract address if creation
                if receipt.get('contractAddress'):
                    debug_info.append(f"    Contract: {receipt.get('contractAddress')}")
            else:
                debug_info.append(f"    Status: Unable to fetch receipt")

        if len(transactions) > 10:
            debug_info.append(f"\n  ... and {len(transactions) - 10} more transaction(s)")

        debug_info.append(f"\nTransaction Summary: {success_count} succeeded, {failed_count} failed")

    # Provide debugging suggestions
    debug_info.append("\n" + "-" * 80)
    debug_info.append("DEBUGGING COMMANDS:")
    debug_info.append("-" * 80)

    if report.missing_accounts:
        debug_info.append(f"\n1. Missing accounts in Block BAL (present in Besu, absent from client):")
        for acc in report.missing_accounts[:5]:  # Show first 5
            debug_info.append(f"   {acc}")

        debug_info.append(f"\n   To trace account access, use debug_traceTransaction on relevant TXs:")
        if transactions:
            sample_tx = transactions[0].get('hash') if isinstance(transactions[0], dict) else transactions[0]
            debug_info.append(f"   curl -X POST {client_rpc} -H 'Content-Type: application/json' \\")
            debug_info.append(f"     --data '{{\"jsonrpc\":\"2.0\",\"method\":\"debug_traceTransaction\",\"params\":[\"{sample_tx}\",{{\"tracer\":\"prestateTracer\"}}],\"id\":1}}'")

    if report.extra_accounts:
        debug_info.append(f"\n2. Extra accounts in Block BAL (absent from Besu, present in client):")
        for acc in report.extra_accounts[:5]:  # Show first 5
            debug_info.append(f"   {acc}")

    # Show accounts involved in differences
    if report.account_diffs:
        debug_info.append(f"\n3. Accounts with field differences: {len(report.account_diffs)}")
        for diff in report.account_diffs[:3]:
            debug_info.append(f"   {diff.address}")

    # Generic debugging suggestions
    debug_info.append("\n4. Trace specific transaction (replace TX_HASH with transaction hash):")
    debug_info.append(f"   curl -X POST {client_rpc} -H 'Content-Type: application/json' \\")
    debug_info.append(f"     --data '{{\"jsonrpc\":\"2.0\",\"method\":\"debug_traceTransaction\",\"params\":[\"TX_HASH\",{{\"tracer\":\"callTracer\"}}],\"id\":1}}'")

    debug_info.append("\n5. Get transaction receipt:")
    debug_info.append(f"   curl -X POST {client_rpc} -H 'Content-Type: application/json' \\")
    debug_info.append(f"     --data '{{\"jsonrpc\":\"2.0\",\"method\":\"eth_getTransactionReceipt\",\"params\":[\"TX_HASH\"],\"id\":1}}'")

    debug_info.append("\n" + "=" * 80)

    return "\n".join(debug_info)


def main():
    parser = argparse.ArgumentParser(
        description='Baloor - Block Access List Comparison and Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze from file - all blocks (summary)
  baloor bad_blocks.json

  # Analyze from file - specific block by hash
  baloor bad_blocks.json --block-hash 0xb14216c12fc317f97e7981ed6b800eb0f9f8690910a9b4c7300efd077baba808

  # Fetch bad blocks from Besu RPC and analyze
  baloor --besu-rpc http://10.20.212.70:33133

  # Fetch from Besu and analyze specific block with client debugging
  baloor --besu-rpc http://10.20.212.70:33133 --client-rpc http://10.20.212.70:33118 --block-hash 0xb14216...

  # Multi-agent analysis with RPC endpoints
  baloor --besu-rpc http://10.20.212.70:33133 --block-hash 0xb14216... --multi-agent

  # Multi-agent with custom branch and preserved repos for debugging
  baloor bad_blocks.json --block-hash 0xb14216... --multi-agent --branch bal-devnet-0 --keep-repos

  # SDK Agent analysis (interactive root cause finding)
  baloor --besu-rpc http://10.20.212.70:33133 --client-rpc http://10.20.212.70:33118 \
    --block-hash 0xb14216... --analyze

  # Save report to file
  baloor --besu-rpc http://10.20.212.70:33133 --block-hash 0xb14216... -o report.txt

  # Show verbose output with all transaction details
  baloor bad_blocks.json --block-hash 0xb14216... -v
        """
    )

    # Input source (file or RPC)
    parser.add_argument('input_file', nargs='?', help='Path to bad_blocks.json (optional if using --besu-rpc)')
    parser.add_argument('--besu-rpc', help='Besu RPC endpoint URL for fetching bad blocks (e.g., http://10.20.212.70:33133)')
    parser.add_argument('--client-rpc', help='Client RPC endpoint for additional debugging - receipts and traces (e.g., http://10.20.212.70:33118 for Nethermind)')

    # Block selection
    parser.add_argument('--block-hash', help='Block hash (hex with 0x) - primary selector for a specific block')
    parser.add_argument('--block-number', help='Block number (hex with 0x) - use block-hash instead if multiple blocks share the same number')

    # Output options
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')

    # Multi-agent analysis options
    parser.add_argument('--multi-agent', action='store_true',
                        help='Use multi-agent analysis system (downloads client code, deep analysis with journal invariants)')
    parser.add_argument('--branch', default='bal-devnet-0',
                        help='Git branch to checkout for codebase analysis (default: bal-devnet-0)')
    parser.add_argument('--keep-repos', action='store_true',
                        help='Preserve cloned repositories for debugging (default: cleanup after analysis)')

    # SDK Agent analysis
    parser.add_argument('--analyze', action='store_true',
                        help='Use Claude SDK agent for interactive root cause analysis (requires --client-rpc)')

    args = parser.parse_args()

    # Validate arguments
    if args.analyze and not args.client_rpc:
        print("Error: --analyze requires --client-rpc", file=sys.stderr)
        sys.exit(1)

    if args.analyze and not (args.block_hash or args.block_number):
        print("Error: --analyze requires --block-hash or --block-number", file=sys.stderr)
        sys.exit(1)

    # Validate input source
    if not args.input_file and not args.besu_rpc:
        print("Error: Must provide either input_file or --besu-rpc", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.input_file and args.besu_rpc:
        print("Error: Cannot specify both input_file and --besu-rpc", file=sys.stderr)
        sys.exit(1)

    # Load data from file or RPC
    if args.besu_rpc:
        print(f"Fetching bad blocks from Besu RPC: {args.besu_rpc}", file=sys.stderr)
        data = fetch_bad_blocks_from_besu(args.besu_rpc)
        if not data:
            print("Error: Failed to fetch bad blocks from Besu", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Loading bad blocks from file: {args.input_file}", file=sys.stderr)
        try:
            with open(args.input_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading file: {e}", file=sys.stderr)
            sys.exit(1)

    results = data.get('result', [])
    if not results:
        print("No bad blocks found", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(results)} bad block(s)", file=sys.stderr)

    # Validate arguments
    if args.block_hash and args.block_number:
        print("Error: Cannot specify both --block-hash and --block-number", file=sys.stderr)
        sys.exit(1)

    # Fetch EIP-7928 for enhanced analysis
    eip_context = None
    if args.block_hash or args.block_number:
        print("Fetching EIP-7928 specification for enhanced analysis...", file=sys.stderr)
        eip_context = fetch_eip_7928()
        if eip_context:
            print("EIP-7928 fetched successfully", file=sys.stderr)
        else:
            print("Continuing without EIP context", file=sys.stderr)

        # Fetch test files for testing improvements analysis
        print("Fetching EIP-7928 test files...", file=sys.stderr)
        test_files = fetch_test_files()
        print(f"Test files fetched: {sum(1 for v in test_files.values() if v)} of {len(test_files)}", file=sys.stderr)
    else:
        test_files = None

    # Execute command
    if args.block_hash or args.block_number:
        # Single block analysis
        if args.block_hash:
            # Filter by block hash (unique identifier)
            filtered_results = [r for r in results if normalize_hex(r.get('block', {}).get('hash')) == normalize_hex(args.block_hash)]
            if not filtered_results:
                print(f"Block with hash {args.block_hash} not found", file=sys.stderr)
                sys.exit(1)
        else:
            # Filter by block number (may match multiple blocks)
            filtered_results = [r for r in results if normalize_hex(r.get('block', {}).get('number')) == normalize_hex(args.block_number)]
            if not filtered_results:
                print(f"Block {args.block_number} not found", file=sys.stderr)
                sys.exit(1)

            # Warn if multiple blocks share the same number
            if len(filtered_results) > 1:
                print(f"WARNING: Found {len(filtered_results)} different blocks with number {args.block_number}!", file=sys.stderr)
                print("Block hashes:", file=sys.stderr)
                for r in filtered_results:
                    block_hash = r.get('block', {}).get('hash', 'unknown')
                    print(f"  - {block_hash}", file=sys.stderr)
                print(f"\nUsing the first match. Consider using --block-hash instead for precise selection.", file=sys.stderr)
                print("", file=sys.stderr)

        block_entry = filtered_results[0]
        report = compare_block(block_entry)

        # Fetch client debug info if RPC provided
        client_debug = ""
        if args.client_rpc:
            print("\nFetching additional debug information from client RPC...", file=sys.stderr)
            client_debug = fetch_client_debug_info(args.client_rpc, report, block_entry)

        # Use multi-agent analysis if requested
        if args.multi_agent:
            print("\n" + "=" * 80, file=sys.stderr)
            print("RUNNING MULTI-AGENT ANALYSIS", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print("This will:", file=sys.stderr)
            print("  1. Download and analyze client implementation code", file=sys.stderr)
            print("  2. Deep-dive into BAL differences with operation sequences", file=sys.stderr)
            print("  3. Generate comprehensive report with journal invariants", file=sys.stderr)
            print("", file=sys.stderr)

            output = run_multi_agent_analysis(
                report=report,
                block_entry=block_entry,
                eip_context=eip_context,
                test_files=test_files,
                branch=args.branch,
                keep_repos=args.keep_repos,
            )
        else:
            # Use legacy pattern-based analysis
            patterns = detect_patterns(report, eip_context, block_entry, test_files)
            output = format_comprehensive_report(report, patterns, verbose=args.verbose)

        # Append client debug info if available
        if client_debug:
            output += client_debug

        # Run SDK agent analysis if requested
        if args.analyze:
            print("\n" + "=" * 80, file=sys.stderr)
            print("RUNNING SDK AGENT ANALYSIS", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print("The agent will investigate the BAL differences and find the root cause...", file=sys.stderr)
            print("", file=sys.stderr)

            try:
                # Import agent module
                from .agents.bal_root_cause_agent import analyze_bal_report
                import anyio

                # Prepare report data
                report_data = {
                    'missing_accounts': report.missing_accounts,
                    'extra_accounts': report.extra_accounts,
                    'block_hash': report.block_hash,
                    'block_number': report.block_number,
                }

                # Run agent analysis
                agent_analysis = anyio.run(
                    analyze_bal_report,
                    output,  # Pass the generated report as text
                    args.client_rpc,
                    args.besu_rpc if args.besu_rpc else None,
                    report_data,
                    block_entry,
                )

                # Append agent analysis to output
                output += "\n\n" + "=" * 80 + "\n"
                output += "SDK AGENT ROOT CAUSE ANALYSIS\n"
                output += "=" * 80 + "\n\n"
                output += agent_analysis

            except Exception as e:
                print(f"\nError running SDK agent analysis: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)

    else:
        # Multi-block analysis
        reports = [compare_block(entry) for entry in results]
        output = format_multi_block_analysis(reports)

    # Output
    output_file = args.output

    # Generate default filename for single block analysis
    if not output_file and (args.block_hash or args.block_number):
        block_num = report.block_number
        block_hash_short = shorten_hex(report.block_hash)
        date_str = datetime.now().strftime('%Y-%m-%d')
        analysis_type = "multiagent" if args.multi_agent else "standard"
        output_file = f"baloor_{analysis_type}_block_{block_num}_{block_hash_short}_{date_str}.md"

    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
        print(f"Report written to {output_file}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
