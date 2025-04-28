#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command-line interface for koinly2irpf.
"""

import sys
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    """Entry point for the application."""
    parser = argparse.ArgumentParser(description='Conversor de relatórios Koinly para IRPF')
    
    # Mutually exclusive group for file or directory
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('file', nargs='?', type=str, 
                       help='Caminho para o arquivo PDF do Koinly')
    group.add_argument('--dir', type=str, 
                       help='Diretório contendo arquivos PDF do Koinly para processamento em lote')
    
    args = parser.parse_args()
    
    try:
        # Importamos aqui para evitar circular imports
        from koinly2irpf.processor import KoinlyProcessor
        
        if args.file:
            # Process single file
            file_path = Path(args.file)
            if not file_path.exists():
                logging.error(f"Arquivo não encontrado: {file_path}")
                return 1
                
            if not file_path.name.lower().endswith('.pdf'):
                logging.error(f"Arquivo não é um PDF: {file_path}")
                return 1
                
            processor = KoinlyProcessor(file_path)
            processor.process_report()
            processor.save_to_csv()
            logging.info(f"Processamento concluído: {file_path}")
            
        elif args.dir:
            # Process directory
            dir_path = Path(args.dir)
            if not dir_path.exists() or not dir_path.is_dir():
                logging.error(f"Diretório não encontrado: {dir_path}")
                return 1
                
            pdf_files = list(dir_path.glob('*.pdf'))
            if not pdf_files:
                logging.error(f"Nenhum arquivo PDF encontrado em: {dir_path}")
                return 1
                
            for pdf_file in pdf_files:
                logging.info(f"Processando: {pdf_file}")
                try:
                    processor = KoinlyProcessor(pdf_file)
                    processor.process_report()
                    processor.save_to_csv()
                    logging.info(f"Arquivo processado: {pdf_file}")
                except Exception as e:
                    logging.error(f"Erro ao processar {pdf_file}: {str(e)}")
                    
            logging.info(f"Processamento em lote concluído. {len(pdf_files)} arquivos processados.")
            
        return 0
        
    except KeyboardInterrupt:
        logging.info("Processamento interrompido pelo usuário")
        return 130
    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 