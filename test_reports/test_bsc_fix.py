#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to demonstrate the BSC fix module working correctly.
"""

import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Direct import from the functional version
functional_module_path = Path(__file__).parent.parent / "koinly2irpf"
sys.path.insert(0, str(functional_module_path))

try:
    from koinly2irpf.fix_binance_smart_chain import process_wallet_details_for_bsc, is_bsc_address
    logging.info("BSC fix module imported successfully from functional version")
    BSC_MODULE_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import BSC module: {str(e)}")
    BSC_MODULE_AVAILABLE = False
    sys.exit(1)

def test_bsc_address_detection():
    """Test BSC address detection function."""
    
    # Test valid BSC addresses
    valid_addresses = [
        "0x123456789012345678901234567890123456789a",
        "0xabcdef0123456789abcdef0123456789abcdef01",
        "0x0000000000000000000000000000000000000000",
        "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    ]
    
    # Test invalid addresses
    invalid_addresses = [
        "",
        None,
        123,
        "0x123",  # Too short
        "0X123456789012345678901234567890123456789A",  # Wrong case format
        "1x1234567890123456789012345678901234567890",  # Doesn't start with 0x
        "0x123456789012345678901234567890123456789g",  # Invalid hex char
    ]
    
    print("\n=== Testing BSC Address Detection ===")
    
    # Test valid addresses
    for addr in valid_addresses:
        result = is_bsc_address(addr)
        print(f"Address: {addr} -> {'✅ Valid' if result else '❌ Invalid'}")
        assert result, f"Address {addr} should be valid"
    
    # Test invalid addresses
    for addr in invalid_addresses:
        result = is_bsc_address(addr)
        print(f"Address: {addr} -> {'❌ Valid (Should be invalid!)' if result else '✅ Invalid'}")
        assert not result, f"Address {addr} should be invalid"

def test_wallet_details_processing():
    """Test wallet details processing function."""
    
    # Test wallet details
    test_wallets = [
        {
            "wallet_name_raw": "Binance Exchange",
            "blockchain": "NONE",
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Bitcoin address
            "wallet_type": "exchange"
        },
        {
            "wallet_name_raw": "Metamask BSC",
            "blockchain": "ethereum",  # Incorrectly labeled as Ethereum
            "address": "0x123456789012345678901234567890123456789a",  # BSC address
            "wallet_type": "wallet"
        },
        {
            "wallet_name_raw": "Trust Wallet (BSC)",
            "blockchain": "NONE",
            "address": "0xabcdef0123456789abcdef0123456789abcdef01",  # BSC address
            "wallet_type": "wallet"
        },
        {
            "wallet_name_raw": "Binance Smart Chain Wallet",
            "blockchain": "NONE",
            "address": "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",  # BSC address
            "wallet_type": "wallet"
        },
        {
            "wallet_name_raw": "My BNB Wallet",
            "blockchain": "NONE",
            "address": "0x0000000000000000000000000000000000000000",  # BSC address
            "wallet_type": "wallet"
        }
    ]
    
    print("\n=== Testing Wallet Details Processing ===")
    print("\nBefore processing:")
    for i, wallet in enumerate(test_wallets):
        print(f"Wallet {i+1}: {wallet['wallet_name_raw']}, Blockchain: {wallet['blockchain']}")
    
    # Process wallet details
    processed_wallets = process_wallet_details_for_bsc(test_wallets)
    
    print("\nAfter processing:")
    for i, wallet in enumerate(processed_wallets):
        print(f"Wallet {i+1}: {wallet['wallet_name_raw']}, Blockchain: {wallet['blockchain']}")
        # Check if BSC wallets were properly detected
        if "BSC" in wallet['wallet_name_raw'] or "Binance Smart Chain" in wallet['wallet_name_raw'] or "BNB" in wallet['wallet_name_raw']:
            assert "BNB Smart Chain" in wallet['blockchain'], f"Wallet {wallet['wallet_name_raw']} should be detected as BSC"
        elif "Binance Exchange" in wallet['wallet_name_raw']:
            assert wallet['blockchain'] == "NONE", f"Wallet {wallet['wallet_name_raw']} should not be detected as BSC"

def main():
    """Run all tests."""
    if not BSC_MODULE_AVAILABLE:
        print("BSC fix module not available. Exiting.")
        return 1
    
    print("\n========================================")
    print("  TESTING BSC FIX MODULE FUNCTIONALITY")
    print("========================================")
    
    test_bsc_address_detection()
    test_wallet_details_processing()
    
    print("\n========================================")
    print("  ALL TESTS PASSED SUCCESSFULLY!")
    print("========================================")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 