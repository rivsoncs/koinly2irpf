import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '')))

from koinly2irpf.processor import KoinlyProcessor

# Create a mock wallet detail
test_wallet_detail = {
    'wallet_name_raw': 'MetaMask - Binance Smart Chain - 0x1234abcd',
    'wallet_type': 'Wallet',
    'address': '0x1234abcd',
    'blockchain': 'None',  # Intentionally set to None to test detection
    'currency': 'BNB',
    'amount': 1.5,
    'price': 100,
    'value': 150,
    'cost_brl': 120
}

# Create a mock processor
class MockProcessor(KoinlyProcessor):
    def __init__(self):
        self.year = '2024'  # Only needed for description formatting

# Create instance and test
processor = MockProcessor()
result = processor.generate_irpf_description([test_wallet_detail])

# Print the results
print("\nTEST RESULTS:")
print("="*80)
print(f"Original wallet_name_raw: {test_wallet_detail['wallet_name_raw']}")
print(f"Original blockchain: {test_wallet_detail['blockchain']}")
print(f"Result description: {result[0]['irpf_description']}")
print("="*80)

# Verify if it's correctly identified as a blockchain and not an exchange
if 'NA EXCHANGE BINANCE' in result[0]['irpf_description']:
    print("❌ FAILED: Incorrectly identified as Binance Exchange")
elif 'REDE BINANCE SMART CHAIN' in result[0]['irpf_description']:
    print("✅ SUCCESS: Correctly identified as Binance Smart Chain blockchain")
else:
    print("⚠️ UNCLEAR: Neither exchange nor blockchain properly identified")
    print(f"Description: {result[0]['irpf_description']}") 