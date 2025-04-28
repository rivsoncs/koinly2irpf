"""
Pacote principal do projeto Koinly2IRPF.
Inclui o módulo principal e processadores para relatórios Koinly.
"""

# Tornar a função main() disponível diretamente do pacote
try:
    from .main import main
except ImportError:
    pass

# Versão do pacote
__version__ = "0.1.0"

# Reports to IRPF package
# This init file makes src a proper Python package 