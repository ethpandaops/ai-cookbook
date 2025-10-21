"""
Utility functions for Baloor

Common helper functions for hex normalization, formatting, and client detection.
"""

from typing import Optional


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
