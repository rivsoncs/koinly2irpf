import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '')))

from koinly2irpf.processor import KoinlyProcessor

# Create test data
test_wallets = [
    {
        'wallet_name_raw': 'MetaMask - Binance Smart Chain - 0x1234abcd',
        'wallet_type': 'Wallet',
        'address': '0x1234abcd',
        'blockchain': 'None',
        'currency': 'BNB',
        'amount': 1.5,
        'price': 100,
        'value': 150,
        'cost_brl': 120
    },
    {
        'wallet_name_raw': 'MetaMask - Ethereum',
        'wallet_type': 'Wallet',
        'address': '0xabcd1234',
        'blockchain': 'Ethereum',
        'currency': 'ETH',
        'amount': 2.5,
        'price': 200,
        'value': 500,
        'cost_brl': 450
    },
    {
        'wallet_name_raw': 'MetaMask - BSC',
        'wallet_type': 'Wallet',
        'address': '0xbsc123',
        'blockchain': 'None',
        'currency': 'CAKE',
        'amount': 10.0,
        'price': 10,
        'value': 100,
        'cost_brl': 90
    }
]

# Create a fully initialized processor instance
# Use the first test file available
test_path = None
for test_pdf in ["Exemplos-Reports/koinly_2024_balances_per_wallet_pqPHc5TLaq_0.pdf", "test.pdf"]:
    if os.path.exists(test_pdf):
        test_path = Path(test_pdf)
        break

if not test_path:
    # Create a dummy path as fallback
    test_path = Path("dummy_2024_test.pdf")
    print(f"Warning: Using dummy path {test_path}")

print(f"Creating processor with path: {test_path}")
try:
    processor = KoinlyProcessor(test_path)
except Exception as e:
    print(f"Warning: Could not fully initialize processor: {e}")
    # Partial initialization as fallback
    processor = KoinlyProcessor.__new__(KoinlyProcessor)
    processor.year = '2024'
    processor.pdf_path = test_path

# Apply our custom fix method
print(f"\n--- APPLYING BSC FIX TO {len(test_wallets)} WALLETS ---")
try:
    fixed_wallets = processor.generate_irpf_description(test_wallets)
    
    # Check the results
    for i, wallet in enumerate(fixed_wallets):
        print(f"\nWallet {i+1}: {wallet['wallet_name_raw']}")
        print(f"  Type: {wallet.get('wallet_type')}")
        print(f"  Blockchain: {wallet.get('blockchain')}")
        
        # Check for BSC-specific description
        desc = wallet.get('irpf_description', 'No description')
        if 'REDE BINANCE SMART CHAIN' in desc:
            print(f"  ✅ SUCCESS: Correctly identified as BSC")
            print(f"  Description: {desc}")
        elif 'BSC' in wallet['wallet_name_raw'] or 'Binance Smart Chain' in wallet['wallet_name_raw']:
            print(f"  ❌ FAILED: Contains BSC but not properly identified")
            print(f"  Description: {desc}")
        else:
            print(f"  ℹ️ INFO: Not a BSC wallet")
            
    print("\n--- TEST COMPLETE ---")
    
except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc() 