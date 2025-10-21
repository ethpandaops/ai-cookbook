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
from .utils import normalize_hex, shorten_hex


def main():
    parser = argparse.ArgumentParser(
        description='Baloor - Block Access List Comparison and Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all blocks (summary)
  baloor bad_blocks.json

  # Analyze specific block by hash (recommended - unique identifier)
  baloor bad_blocks.json --block-hash 0xb14216c12fc317f97e7981ed6b800eb0f9f8690910a9b4c7300efd077baba808

  # Analyze with multi-agent system (downloads client code, deep analysis)
  baloor bad_blocks.json --block-hash 0xb14216... --multi-agent

  # Multi-agent with custom branch and preserved repos for debugging
  baloor bad_blocks.json --block-hash 0xb14216... --multi-agent --branch bal-devnet-0 --keep-repos

  # Save report to file
  baloor bad_blocks.json --block-hash 0xb14216... -o report.txt

  # Show verbose output with all transaction details
  baloor bad_blocks.json --block-hash 0xb14216... -v
        """
    )

    parser.add_argument('input_file', help='Path to bad_blocks.json')
    parser.add_argument('--block-hash', help='Block hash (hex with 0x) - primary selector for a specific block')
    parser.add_argument('--block-number', help='Block number (hex with 0x) - use block-hash instead if multiple blocks share the same number')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')

    # Multi-agent analysis options
    parser.add_argument('--multi-agent', action='store_true',
                        help='Use multi-agent analysis system (downloads client code, deep analysis with journal invariants)')
    parser.add_argument('--branch', default='bal-devnet-0',
                        help='Git branch to checkout for codebase analysis (default: bal-devnet-0)')
    parser.add_argument('--keep-repos', action='store_true',
                        help='Preserve cloned repositories for debugging (default: cleanup after analysis)')

    args = parser.parse_args()

    # Load data
    try:
        with open(args.input_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}", file=sys.stderr)
        sys.exit(1)

    results = data.get('result', [])
    if not results:
        print("No results found", file=sys.stderr)
        sys.exit(1)

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
