#!/usr/bin/env python3
"""
Baloor - Block Access List Comparison and Analysis Tool

A comprehensive toolkit for comparing and analyzing Block Access Lists (BALs)
from Teku's debug endpoint, identifying differences between incoming blocks
and Besu generated BALs.

Based on EIP-7928: Block-Level Access Lists

This is the main entry point that imports from the refactored baloor_lib package.
"""

from baloor_lib import main

if __name__ == '__main__':
    main()
