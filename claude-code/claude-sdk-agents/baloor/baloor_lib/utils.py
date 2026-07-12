"""
Utility functions for Baloor

Common helper functions for hex normalization, formatting, and client detection.
"""

import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List


def normalize_hex(value: Optional[str]) -> Optional[str]:
    """Normalize hex string to lowercase with 0x prefix."""
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    value = value.lower()
    if not value.startswith('0x'):
        value = '0x' + value
    return value


def shorten_hex(value: str, prefix_len: int = 10, suffix_len: int = 6) -> str:
    """Shorten a hex value for display."""
    if not value or not isinstance(value, str):
        return str(value)
    if len(value) <= prefix_len + suffix_len + 3:
        return value
    return f"{value[:prefix_len]}...{value[-suffix_len:]}"


def decode_client_from_extra_data(extra_data: str) -> str:
    """Decode client information from block extraData field."""
    try:
        data = bytes.fromhex(extra_data[2:] if extra_data.startswith('0x') else extra_data)
        decoded = data.decode('utf-8', errors='ignore')
        client_patterns = {
            'geth': 'Geth', 'besu': 'Besu', 'nethermind': 'Nethermind',
            'erigon': 'Erigon', 'reth': 'Reth'
        }
        decoded_lower = decoded.lower()
        for pattern, name in client_patterns.items():
            if pattern in decoded_lower:
                return f"{name} ({decoded.strip()})"
        return f"Unknown ({decoded.strip()})" if decoded.strip() else "Unknown"
    except Exception as e:
        return f"Unknown (decode error: {e})"


def rpc_call(endpoint: str, method: str, params: List[Any] = None, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Make a JSON-RPC call to an Ethereum node.

    Args:
        endpoint: RPC endpoint URL (e.g., http://10.20.212.70:33133)
        method: JSON-RPC method name (e.g., "debug_getBadBlocks")
        params: List of parameters for the method
        timeout: Request timeout in seconds

    Returns:
        JSON-RPC response dict or None on error
    """
    if params is None:
        params = []

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }

    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            if 'error' in result:
                print(f"RPC error: {result['error']}")
                return None
            return result
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"Error calling {method} on {endpoint}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None


def fetch_bad_blocks_from_besu(endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Fetch bad blocks from Besu using debug_getBadBlocks.

    Args:
        endpoint: Besu RPC endpoint URL

    Returns:
        Response dict in the format expected by baloor (with 'result' key)
    """
    print(f"Fetching bad blocks from Besu at {endpoint}...")
    result = rpc_call(endpoint, "debug_getBadBlocks", [])
    if result:
        print(f"Successfully fetched {len(result.get('result', []))} bad block(s)")
    return result


def fetch_block_by_number(endpoint: str, block_number: str, include_txs: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch a block by number from an Ethereum node.

    Args:
        endpoint: RPC endpoint URL
        block_number: Block number in hex (with 0x prefix) or 'latest'
        include_txs: Whether to include full transaction objects

    Returns:
        Block data or None on error
    """
    result = rpc_call(endpoint, "eth_getBlockByNumber", [block_number, include_txs])
    return result.get('result') if result else None


def fetch_block_by_hash(endpoint: str, block_hash: str, include_txs: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch a block by hash from an Ethereum node.

    Args:
        endpoint: RPC endpoint URL
        block_hash: Block hash (with 0x prefix)
        include_txs: Whether to include full transaction objects

    Returns:
        Block data or None on error
    """
    result = rpc_call(endpoint, "eth_getBlockByHash", [block_hash, include_txs])
    return result.get('result') if result else None


def fetch_transaction_receipt(endpoint: str, tx_hash: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a transaction receipt from an Ethereum node.

    Args:
        endpoint: RPC endpoint URL
        tx_hash: Transaction hash (with 0x prefix)

    Returns:
        Receipt data or None on error
    """
    result = rpc_call(endpoint, "eth_getTransactionReceipt", [tx_hash])
    return result.get('result') if result else None


def debug_trace_transaction(endpoint: str, tx_hash: str, tracer: str = "prestateTracer") -> Optional[Dict[str, Any]]:
    """
    Debug trace a transaction.

    Args:
        endpoint: RPC endpoint URL
        tx_hash: Transaction hash (with 0x prefix)
        tracer: Tracer type (prestateTracer, callTracer, etc.)

    Returns:
        Trace data or None on error
    """
    result = rpc_call(endpoint, "debug_traceTransaction", [tx_hash, {"tracer": tracer}])
    return result.get('result') if result else None
