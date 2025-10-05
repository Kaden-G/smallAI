#!/usr/bin/env python3
"""
Wrapper script for backward compatibility.
Delegates to src/hybrid_parser.py
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import and run the actual hybrid_parser
from hybrid_parser import main

if __name__ == "__main__":
    main()
