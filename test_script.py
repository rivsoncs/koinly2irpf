#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

def main():
    print("Test script running successfully")
    print(f"Python version: {sys.version}")
    
    # Try to import the koinly2irpf module to test if it's installed
    try:
        import koinly2irpf
        print(f"koinly2irpf module found, version: {koinly2irpf.__version__}")
    except ImportError as e:
        print(f"Could not import koinly2irpf: {e}")

if __name__ == "__main__":
    main()
