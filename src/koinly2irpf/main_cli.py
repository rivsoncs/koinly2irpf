#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stand-alone CLI module for koinly2irpf.
This will serve as the direct entry point for the application.
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Adiciona o diretório src ao path para permitir importação de src.main
module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

def main():
    """Main entry point for the application."""
    try:
        # Get the main function from the original source
        # Try different import paths to ensure compatibility
        try:
            # Importar src/main.py diretamente
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from main import main as original_main
            logging.info("Using main module from src directory")
            return original_main()
        except ImportError:
            # Se falhar, tente importar do src.koinly_processor
            try:
                from koinly_processor import KoinlyProcessor
                logging.info("Using KoinlyProcessor directly")
                
                # Setup basic CLI
                parser = argparse.ArgumentParser(description="Conversor de relatórios Koinly para IRPF brasileiro")
                parser.add_argument("file", help="Arquivo PDF do Koinly para processar")
                args = parser.parse_args()
                
                file_path = Path(args.file)
                if not file_path.exists():
                    logging.error(f"Arquivo não encontrado: {file_path}")
                    return 1
                
                # Process the file
                processor = KoinlyProcessor(file_path)
                processor.process_report()
                processor.save_to_csv()
                logging.info(f"Arquivo processado: {file_path}")
                return 0
            except ImportError:
                # Se todo o resto falhar, forneça uma mensagem de erro útil
                logging.error("Não foi possível importar os módulos necessários.")
                print("ERRO: Estrutura de pacote inválida. Por favor, reinstale o pacote.")
                print("Comando: pip uninstall -y koinly2irpf && pip install git+https://github.com/rivsoncs/koinly2irpf.git")
                return 1
    except Exception as e:
        logging.error(f"Erro ao executar o programa: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
