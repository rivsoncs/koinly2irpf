#!/usr/bin/env python3
"""
Script simples para processar relatórios do Koinly para IRPF.
Este script pode ser executado diretamente sem instalação.
"""

import sys
from pathlib import Path

# Adiciona o diretório src ao PYTHONPATH
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from src.main import main

if __name__ == "__main__":
    main() 