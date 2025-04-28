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

def main():
    """Main entry point for the application."""
    try:
        # Try to import from processor module
        try:
            from koinly2irpf.processor import KoinlyProcessor
            logging.info("Using KoinlyProcessor from koinly2irpf.processor")
        except ImportError:
            try:
                from processor import KoinlyProcessor
                logging.info("Using KoinlyProcessor from processor")
            except ImportError:
                logging.error("Não foi possível importar os módulos necessários.")
                print("ERRO: Estrutura de pacote inválida. Por favor, reinstale o pacote.")
                print("Comando: pip uninstall -y koinly2irpf && pip install git+https://github.com/rivsoncs/koinly2irpf.git")
                return 1
                
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
    except Exception as e:
        logging.error(f"Erro ao executar o programa: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
