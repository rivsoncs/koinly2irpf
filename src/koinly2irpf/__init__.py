"""
Koinly2IRPF - Conversor de relatórios Koinly para IRPF brasileiro.

Este pacote processa relatórios do Koinly e os converte para um formato
compatível com a declaração de Imposto de Renda de Pessoa Física (IRPF) no Brasil.
"""

# Import the BSC fix module to make it available
try:
    from .fix_binance_smart_chain import process_wallet_details_for_bsc
    print("BSC fix module successfully imported in __init__")
except ImportError:
    print("BSC fix module not found in __init__, BSC detection improvements will not be available")

__version__ = "0.1.0" 