#!/usr/bin/env python3
"""
BAL Root Cause Analyzer Agent

Uses Claude SDK to analyze BAL inconsistencies and find root causes with fixes.
This agent has access to:
- Transaction tracing (debug_traceTransaction)
- Transaction receipts
- Block data
- Client RPC endpoints
"""

import json
import anyio
from typing import Dict, Any, List, Optional
from pathlib import Path

from claude_agent_sdk import (
    create_sdk_mcp_server,
    tool,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from ..utils import (
    rpc_call,
    debug_trace_transaction,
    fetch_transaction_receipt,
    fetch_block_by_hash,
)


class BALRootCauseAnalyzer:
    """Agent for analyzing BAL inconsistencies and finding root causes."""

    def __init__(self, client_rpc: str, besu_rpc: str, report_data: Dict[str, Any], block_entry: Dict[str, Any]):
        """
        Initialize the analyzer.

        Args:
            client_rpc: Client RPC endpoint (e.g., Nethermind)
            besu_rpc: Besu RPC endpoint
            report_data: Parsed BAL report data
            block_entry: Block entry from debug_getBadBlocks
        """
        self.client_rpc = client_rpc
        self.besu_rpc = besu_rpc
        self.report_data = report_data
        self.block_entry = block_entry
        self.traced_transactions: Dict[str, Any] = {}
        self.receipts: Dict[str, Any] = {}

    def _get_transactions(self) -> List[Dict[str, Any]]:
        """Get transactions from the block."""
        return self.block_entry.get('block', {}).get('transactions', [])

    def _get_missing_accounts(self) -> List[str]:
        """Extract missing accounts from report data."""
        # Parse from report or use provided data
        if 'missing_accounts' in self.report_data:
            return self.report_data['missing_accounts']
        return []

    def _get_extra_accounts(self) -> List[str]:
        """Extract extra accounts from report data."""
        if 'extra_accounts' in self.report_data:
            return self.report_data['extra_accounts']
        return []

    async def _tool_trace_transaction(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Trace a transaction using debug_traceTransaction."""
        tx_hash = args['tx_hash']
        tracer = args.get('tracer', 'prestateTracer')

        print(f"🔍 Tracing transaction {tx_hash} with {tracer}...")

        # Check cache
        cache_key = f"{tx_hash}:{tracer}"
        if cache_key in self.traced_transactions:
            return {"content": [{"type": "text", "text": f"Using cached trace for {tx_hash}"}]}

        # Trace transaction
        trace = debug_trace_transaction(self.client_rpc, tx_hash, tracer)

        if trace:
            self.traced_transactions[cache_key] = trace
            # Format output
            trace_str = json.dumps(trace, indent=2)
            if len(trace_str) > 5000:
                trace_str = trace_str[:5000] + "\n... (truncated)"

            return {
                "content": [{
                    "type": "text",
                    "text": f"Transaction trace for {tx_hash} (tracer: {tracer}):\n\n```json\n{trace_str}\n```"
                }]
            }
        else:
            return {
                "content": [{"type": "text", "text": f"Failed to trace transaction {tx_hash}"}],
                "is_error": True
            }

    async def _tool_get_receipt(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Get transaction receipt."""
        tx_hash = args['tx_hash']

        print(f"📄 Getting receipt for {tx_hash}...")

        # Check cache
        if tx_hash in self.receipts:
            return {"content": [{"type": "text", "text": f"Using cached receipt for {tx_hash}"}]}

        # Get receipt
        receipt = fetch_transaction_receipt(self.client_rpc, tx_hash)

        if receipt:
            self.receipts[tx_hash] = receipt
            receipt_str = json.dumps(receipt, indent=2)

            return {
                "content": [{
                    "type": "text",
                    "text": f"Transaction receipt for {tx_hash}:\n\n```json\n{receipt_str}\n```"
                }]
            }
        else:
            return {
                "content": [{"type": "text", "text": f"Failed to get receipt for {tx_hash}"}],
                "is_error": True
            }

    async def _tool_list_missing_accounts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: List accounts missing from Block BAL (present in Besu, absent from client)."""
        missing = self._get_missing_accounts()

        if missing:
            accounts_list = "\n".join([f"  - {acc}" for acc in missing])
            return {
                "content": [{
                    "type": "text",
                    "text": f"Missing accounts ({len(missing)}):\n{accounts_list}"
                }]
            }
        else:
            return {
                "content": [{"type": "text", "text": "No missing accounts found."}]
            }

    async def _tool_list_extra_accounts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: List accounts extra in Block BAL (absent from Besu, present in client)."""
        extra = self._get_extra_accounts()

        if extra:
            accounts_list = "\n".join([f"  - {acc}" for acc in extra])
            return {
                "content": [{
                    "type": "text",
                    "text": f"Extra accounts ({len(extra)}):\n{accounts_list}"
                }]
            }
        else:
            return {
                "content": [{"type": "text", "text": "No extra accounts found."}]
            }

    async def _tool_list_transactions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: List all transactions in the block."""
        transactions = self._get_transactions()

        if transactions:
            tx_list = []
            for idx, tx in enumerate(transactions[:20]):  # Limit to first 20
                tx_hash = tx.get('hash') if isinstance(tx, dict) else tx
                from_addr = tx.get('from', 'N/A') if isinstance(tx, dict) else 'N/A'
                to_addr = tx.get('to', 'contract creation') if isinstance(tx, dict) else 'N/A'
                to_addr = to_addr if to_addr else 'contract creation'
                tx_list.append(f"  {idx}: {tx_hash}\n      From: {from_addr}\n      To: {to_addr}")

            if len(transactions) > 20:
                tx_list.append(f"\n  ... and {len(transactions) - 20} more transactions")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Transactions ({len(transactions)} total):\n\n" + "\n\n".join(tx_list)
                }]
            }
        else:
            return {
                "content": [{"type": "text", "text": "No transactions found in block."}]
            }

    async def _tool_get_block_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Get block information."""
        block = self.block_entry.get('block', {})

        info = f"""Block Information:
- Number: {block.get('number', 'N/A')}
- Hash: {block.get('hash', 'N/A')}
- Parent Hash: {block.get('parentHash', 'N/A')}
- Timestamp: {block.get('timestamp', 'N/A')}
- Gas Used: {block.get('gasUsed', 'N/A')}
- Gas Limit: {block.get('gasLimit', 'N/A')}
- Transaction Count: {len(block.get('transactions', []))}
- Extra Data: {block.get('extraData', 'N/A')}
"""

        return {
            "content": [{"type": "text", "text": info}]
        }

    async def _tool_search_account_in_transactions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Search for an account address in transaction data."""
        address = args['address'].lower()
        transactions = self._get_transactions()

        found_in = []
        for idx, tx in enumerate(transactions):
            if not isinstance(tx, dict):
                continue

            # Check from/to
            tx_from = tx.get('from', '')
            tx_to = tx.get('to', '')

            if tx_from and address == tx_from.lower():
                found_in.append({
                    'index': idx,
                    'hash': tx.get('hash'),
                    'location': 'sender',
                    'details': f"From: {tx_from}"
                })
            if tx_to and address == tx_to.lower():
                found_in.append({
                    'index': idx,
                    'hash': tx.get('hash'),
                    'location': 'recipient',
                    'details': f"To: {tx_to}"
                })

            # Check input data (embedded address)
            input_data = tx.get('input', '')
            if input_data and address.replace('0x', '') in input_data.lower():
                found_in.append({
                    'index': idx,
                    'hash': tx.get('hash'),
                    'location': 'input_data',
                    'details': f"Address embedded in input data"
                })

            # Check access list (EIP-2930)
            access_list = tx.get('accessList', [])
            if access_list:
                for entry in access_list:
                    if entry.get('address', '').lower() == address:
                        found_in.append({
                            'index': idx,
                            'hash': tx.get('hash'),
                            'location': 'access_list',
                            'details': f"In EIP-2930 access list"
                        })

        if found_in:
            result_text = f"Account {address} found in {len(found_in)} transaction(s):\n\n"
            for item in found_in:
                result_text += f"  TX[{item['index']}]: {item['hash']}\n"
                result_text += f"    Location: {item['location']}\n"
                result_text += f"    Details: {item['details']}\n\n"

            # Add recommendation
            result_text += "RECOMMENDATION: Trace these transactions to find which opcode accessed the account.\n"
            result_text += f"Use: trace_transaction_opcodes with tx_hash and target_address={address}"

            return {
                "content": [{
                    "type": "text",
                    "text": result_text
                }]
            }
        else:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Account {address} not found in transaction from/to/input/accessList fields.\n\n"
                           f"This suggests INDIRECT access via opcodes during contract execution.\n"
                           f"You should trace transactions systematically to find which one accessed it."
                }]
            }

    async def _tool_trace_transaction_opcodes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Trace transaction with opcode-level detail (struct logger)."""
        tx_hash = args['tx_hash']
        target_address = args.get('target_address', '').lower()

        print(f"🔍 Tracing transaction {tx_hash} with struct logger (opcode-level)...")

        # Use struct logger tracer (no tracer = default)
        trace = rpc_call(self.client_rpc, "debug_traceTransaction", [tx_hash, {}])

        if not trace or 'result' not in trace:
            return {
                "content": [{"type": "text", "text": f"Failed to trace transaction {tx_hash}"}],
                "is_error": True
            }

        result = trace['result']
        struct_logs = result.get('structLogs', [])

        output = f"Transaction Trace (Opcode Level):\n"
        output += f"  Transaction: {tx_hash}\n"
        output += f"  Total Operations: {len(struct_logs)}\n"
        output += f"  Gas Used: {result.get('gas', 'N/A')}\n"
        output += f"  Failed: {result.get('failed', False)}\n"
        output += f"  Return Value: {result.get('returnValue', 'N/A')}\n\n"

        # If target address specified, search for it
        if target_address:
            target_addr_clean = target_address.replace('0x', '')
            account_access_ops = ['BALANCE', 'EXTCODESIZE', 'EXTCODEHASH', 'EXTCODECOPY',
                                  'CALL', 'STATICCALL', 'DELEGATECALL', 'CALLCODE']

            found_accesses = []
            for i, log in enumerate(struct_logs):
                op = log.get('op', '')

                if op in account_access_ops:
                    stack = log.get('stack', [])

                    # Check if target address is in the stack
                    for stack_item in stack:
                        if target_addr_clean in stack_item.lower():
                            found_accesses.append({
                                'step': i,
                                'pc': log.get('pc'),
                                'op': op,
                                'depth': log.get('depth'),
                                'gas': log.get('gas'),
                                'stack': stack[:3]
                            })
                            break

            if found_accesses:
                output += f"✓ FOUND {len(found_accesses)} opcode access(es) to {target_address}:\n\n"
                for access in found_accesses:
                    output += f"  Step {access['step']}:\n"
                    output += f"    🎯 Opcode: {access['op']} ← THIS IS THE OPCODE!\n"
                    output += f"    Program Counter: {access['pc']}\n"
                    output += f"    Call Depth: {access['depth']}\n"
                    output += f"    Gas Remaining: {access['gas']}\n"
                    output += f"    Stack (top 3): {access['stack']}\n\n"

                output += "\n" + "=" * 80 + "\n"
                output += "ROOT CAUSE IDENTIFIED!\n"
                output += "=" * 80 + "\n"
                output += f"The account {target_address} was accessed via the {found_accesses[0]['op']} opcode.\n"
                output += f"This confirms the client bug: it failed to track this account access in the BAL.\n"
            else:
                output += f"✗ No direct opcode access found to {target_address} in struct logs.\n"
                output += f"The address might be:\n"
                output += f"  - In an EIP-2930 access list but never actually accessed (Besu bug)\n"
                output += f"  - Accessed via a different mechanism\n"
        else:
            # Just show summary without target
            ops_summary = {}
            for log in struct_logs:
                op = log.get('op', 'UNKNOWN')
                ops_summary[op] = ops_summary.get(op, 0) + 1

            output += "Top 10 opcodes by frequency:\n"
            for op, count in sorted(ops_summary.items(), key=lambda x: x[1], reverse=True)[:10]:
                output += f"  {op}: {count}\n"

        return {
            "content": [{
                "type": "text",
                "text": output
            }]
        }

    async def _tool_get_transaction_details(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Get detailed transaction information including from/to/value/input."""
        tx_hash = args['tx_hash']

        print(f"📋 Getting transaction details for {tx_hash}...")

        # Find transaction in block
        transactions = self._get_transactions()
        tx = None
        tx_index = None

        for idx, t in enumerate(transactions):
            if isinstance(t, dict) and t.get('hash') == tx_hash:
                tx = t
                tx_index = idx
                break

        if not tx:
            return {
                "content": [{"type": "text", "text": f"Transaction {tx_hash} not found in block"}],
                "is_error": True
            }

        output = f"Transaction Details:\n"
        output += f"  Hash: {tx.get('hash')}\n"
        output += f"  Index: {tx_index}\n"
        output += f"  From: {tx.get('from')}\n"
        output += f"  To: {tx.get('to') if tx.get('to') else 'None (Contract Creation)'}\n"
        output += f"  Value: {tx.get('value')}\n"
        output += f"  Gas: {tx.get('gas')}\n"
        output += f"  Gas Price: {tx.get('gasPrice')}\n"
        output += f"  Nonce: {tx.get('nonce')}\n"
        output += f"  Input: {tx.get('input')[:66]}..." if len(tx.get('input', '')) > 66 else f"  Input: {tx.get('input')}\n"

        # Check for access list
        access_list = tx.get('accessList', [])
        if access_list:
            output += f"\n  EIP-2930 Access List:\n"
            for entry in access_list:
                output += f"    - Address: {entry.get('address')}\n"
                storage_keys = entry.get('storageKeys', [])
                if storage_keys:
                    output += f"      Storage Keys: {len(storage_keys)}\n"

        return {
            "content": [{
                "type": "text",
                "text": output
            }]
        }

    def create_tools(self) -> List:
        """Create SDK MCP tools for the agent."""

        @tool("trace_transaction", "Trace a transaction using debug_traceTransaction", {
            "tx_hash": str,
            "tracer": str  # prestateTracer, callTracer, etc.
        })
        async def trace_transaction(args):
            return await self._tool_trace_transaction(args)

        @tool("get_transaction_receipt", "Get a transaction receipt", {
            "tx_hash": str
        })
        async def get_receipt(args):
            return await self._tool_get_receipt(args)

        @tool("list_missing_accounts", "List accounts missing from Block BAL", {})
        async def list_missing_accounts(args):
            return await self._tool_list_missing_accounts(args)

        @tool("list_extra_accounts", "List accounts extra in Block BAL", {})
        async def list_extra_accounts(args):
            return await self._tool_list_extra_accounts(args)

        @tool("list_transactions", "List all transactions in the block", {})
        async def list_transactions(args):
            return await self._tool_list_transactions(args)

        @tool("get_block_info", "Get block information", {})
        async def get_block_info(args):
            return await self._tool_get_block_info(args)

        @tool("search_account_in_transactions", "Search for an account address in transactions", {
            "address": str
        })
        async def search_account(args):
            return await self._tool_search_account_in_transactions(args)

        @tool("trace_transaction_opcodes", "Trace transaction with opcode-level detail to find exact opcode that accessed an account", {
            "tx_hash": str,
            "target_address": str  # The account address to search for
        })
        async def trace_opcodes(args):
            return await self._tool_trace_transaction_opcodes(args)

        @tool("get_transaction_details", "Get detailed transaction information including from/to/value/input/accessList", {
            "tx_hash": str
        })
        async def get_tx_details(args):
            return await self._tool_get_transaction_details(args)

        return [
            trace_transaction,
            get_receipt,
            list_missing_accounts,
            list_extra_accounts,
            list_transactions,
            get_block_info,
            search_account,
            trace_opcodes,
            get_tx_details
        ]

    def create_analysis_prompt(self, report_text: str) -> str:
        """Create the analysis prompt for the agent."""

        return f"""You are a blockchain EIP-7928 Block Access List (BAL) debugging expert. Your task is to analyze BAL inconsistencies between a client implementation and Besu's reference implementation and identify the EXACT OPCODE that caused the issue.

# Context

You have been provided with a BAL comparison report that shows differences between:
- **Block BAL**: The BAL produced by the client (e.g., Nethermind, Reth, Geth)
- **Generated BAL**: The BAL generated by Besu (reference implementation)

# Report

{report_text}

# Your Task

Analyze this BAL inconsistency and find the EXACT root cause, including the specific opcode. Follow these steps SYSTEMATICALLY:

## Step 1: Identify Missing/Extra Accounts
- Use `list_missing_accounts` to see which accounts are in Besu but not in the client
- Use `list_extra_accounts` to see which accounts are in the client but not in Besu
- Focus on the first missing account as your primary investigation target

## Step 2: Search for the Account in Transactions
- Use `search_account_in_transactions` with the missing account address
- This will tell you if the account appears in:
  - Transaction from/to fields (direct interaction)
  - Transaction input data (embedded in contract call)
  - EIP-2930 access lists (pre-warmed)
- If found in input data or access list, note the transaction hash(es)

## Step 3: Get Transaction Details
- For each transaction that mentions the account:
  - Use `get_transaction_details` to see full transaction info
  - Note if it's a contract creation (to=null) or contract call
  - Check if there's an EIP-2930 access list

## Step 4: Trace with prestateTracer
- Use `trace_transaction` with prestateTracer on the identified transaction(s)
- This shows which accounts were accessed during execution
- Confirm the missing account appears in the trace (proving it was accessed)

## Step 5: Get Transaction Receipt
- Use `get_transaction_receipt` to check:
  - Did the transaction succeed or fail?
  - How much gas was used?
  - Was a contract created?
- Failed transactions are especially important (revert handling bugs)

## Step 6: CRITICAL - Find the Exact Opcode
- Use `trace_transaction_opcodes` with:
  - tx_hash: the transaction that accessed the account
  - target_address: the missing account address
- This will show you THE EXACT OPCODE that accessed the account
- Possible opcodes: BALANCE, EXTCODESIZE, EXTCODEHASH, EXTCODECOPY, CALL, STATICCALL, DELEGATECALL, CALLCODE
- The tool will tell you: opcode name, program counter, call depth, gas remaining

## Step 7: Root Cause Analysis
Based on the exact opcode you found:
- **Determine which client method failed to track the access**
  - EXTCODEHASH → GetCodeHash() method
  - EXTCODESIZE → GetCodeSize() method
  - BALANCE → GetBalance() method
  - CALL/STATICCALL → Call handling code
- **Identify why it failed**
  - No journal entry created for the account access?
  - Journal entry not properly restored on revert?
  - Account access only tracked on state changes, not reads?
- **Locate the bug in the codebase**
  - For Nethermind: TracedAccessWorldState.cs
  - For Reth: revm integration
  - For Geth: state_accessor.go

## Step 8: Generate Comprehensive Report
Your final report MUST include:

### 🎯 ROOT CAUSE IDENTIFIED
- **Exact Opcode**: [The specific opcode that accessed the account]
- **Transaction**: [Hash and index]
- **Transaction Type**: [CREATE/CALL and success/failure]
- **Program Counter**: [Where in bytecode]
- **Call Depth**: [How deep in call stack]

### 🔴 BUG CONFIRMATION
- **Buggy Client**: [Which client has the bug]
- **Bug Location**: [Specific file and method]
- **Root Cause**: [Why the account wasn't tracked]

### 📊 EVIDENCE
- Transaction details (from/to/value/gas)
- Receipt (status/gasUsed)
- prestateTracer output (proving account was accessed)
- Struct logger output (exact opcode)

### 🔧 FIX RECOMMENDATION
- Specific code changes needed
- Method(s) that need modification
- Journal entry handling improvements

### 📝 TEST CASE
- How to reproduce the bug
- Python test case for regression prevention

# EIP-7928 Key Requirements

- **ALL accessed accounts MUST be in BAL**, even with no state changes
- Accounts accessed via BALANCE, EXTCODESIZE, EXTCODEHASH, EXTCODECOPY must be tracked
- CALL/STATICCALL targets (including reverted calls) must be tracked
- Account access tracking must be reversible (journal-based)
- **Empty accounts** with no state changes must still appear with empty change lists

# Available Tools

- `list_missing_accounts`: See which accounts are missing from Block BAL
- `list_extra_accounts`: See which accounts are extra in Block BAL
- `list_transactions`: List all transactions in the block
- `search_account_in_transactions`: Find where an account appears in transaction data
- `get_transaction_details`: Get full transaction details including input data and access lists
- `trace_transaction`: Trace with prestateTracer or callTracer to see account accesses
- `trace_transaction_opcodes`: **CRITICAL** - Get opcode-level trace to find exact opcode that accessed an account
- `get_transaction_receipt`: Get receipt with status, gas, and contract address
- `get_block_info`: Get block metadata

# IMPORTANT Instructions

1. **Follow the steps in order** - Each step builds on the previous
2. **Always use trace_transaction_opcodes** - This is critical for finding the exact opcode
3. **Be thorough** - Check transaction status, look for reverts, examine access lists
4. **Provide evidence** - Include actual data from traces and receipts
5. **Be specific** - Name the exact opcode, file, and method that has the bug

Start your systematic analysis now. Your goal is to identify the EXACT OPCODE that caused this BAL inconsistency.
"""

    async def analyze(self, report_text: str) -> str:
        """
        Run the analysis agent.

        Args:
            report_text: The BAL report as markdown text

        Returns:
            Analysis report from the agent
        """
        # Create MCP server with tools
        tools = self.create_tools()
        mcp_server = create_sdk_mcp_server(
            name="bal_analyzer",
            version="1.0.0",
            tools=tools
        )

        # Configure agent options
        options = ClaudeAgentOptions(
            mcp_servers={"bal": mcp_server},
            allowed_tools=[
                "trace_transaction",
                "get_transaction_receipt",
                "list_missing_accounts",
                "list_extra_accounts",
                "list_transactions",
                "get_block_info",
                "search_account_in_transactions",
                "trace_transaction_opcodes",
                "get_transaction_details",
            ],
            system_prompt="You are an expert blockchain debugger specializing in EIP-7928 Block Access Lists. Your goal is to find the EXACT opcode that caused BAL inconsistencies.",
            max_turns=50,
            cli_path="/home/framework/.nvm/versions/node/v23.11.0/bin/claude",
        )

        # Create prompt
        prompt = self.create_analysis_prompt(report_text)

        # Run agent
        print("\n" + "=" * 80)
        print("STARTING BAL ROOT CAUSE ANALYSIS AGENT")
        print("=" * 80)
        print()

        response_text = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text)
                            response_text.append(block.text)
                        elif isinstance(block, ToolUseBlock):
                            print(f"\n[Using tool: {block.name}]")
                elif isinstance(message, ResultMessage):
                    print(f"\n\n{'=' * 80}")
                    print(f"Analysis complete!")
                    print(f"Cost: ${message.total_cost_usd:.4f}")
                    print(f"Turns: {message.num_turns}")
                    print(f"Duration: {message.duration_ms / 1000:.1f}s")
                    print("=" * 80)

        return "\n\n".join(response_text)


async def analyze_bal_report(
    report_text: str,
    client_rpc: str,
    besu_rpc: str,
    report_data: Dict[str, Any],
    block_entry: Dict[str, Any],
) -> str:
    """
    Analyze a BAL report using the Claude SDK agent.

    Args:
        report_text: The BAL report as formatted markdown
        client_rpc: Client RPC endpoint
        besu_rpc: Besu RPC endpoint
        report_data: Structured report data (with missing_accounts, etc.)
        block_entry: Block entry from debug_getBadBlocks

    Returns:
        Analysis report from the agent
    """
    analyzer = BALRootCauseAnalyzer(
        client_rpc=client_rpc,
        besu_rpc=besu_rpc,
        report_data=report_data,
        block_entry=block_entry,
    )

    return await analyzer.analyze(report_text)


if __name__ == "__main__":
    # Test with sample data
    print("BAL Root Cause Analyzer Agent")
    print("Use this module via the main baloor CLI with --analyze flag")
