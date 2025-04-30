#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command-line interface for koinly2irpf.
"""

import sys
import argparse
import logging
from pathlib import Path
import traceback

# Configure logging (Initially set to a base level, will be updated by args)
logging.basicConfig(
    level=logging.INFO, # Default level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Get the root logger
logger = logging.getLogger()

def main():
    """Entry point for the application."""
    parser = argparse.ArgumentParser(description='Conversor de relatórios Koinly para IRPF')
    
    # Mutually exclusive group for file or directory
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('file', nargs='?', type=str, 
                       help='Caminho para o arquivo PDF do Koinly')
    group.add_argument('--dir', type=str, 
                       help='Diretório contendo arquivos PDF do Koinly para processamento em lote')
    
    # Add log level argument
    parser.add_argument(
        '--log-level',
        type=str.upper,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Define o nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL). Padrão: INFO.'
    )
    
    args = parser.parse_args()

    # Set the logger level based on the argument
    log_level = getattr(logging, args.log_level)
    logger.setLevel(log_level)
    
    try:
        # Importamos aqui para evitar circular imports
        from koinly2irpf.processor import KoinlyProcessor
        
        if args.file:
            # Process single file
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"Arquivo não encontrado: {file_path}")
                return 1
                
            if not file_path.name.lower().endswith('.pdf'):
                logger.error(f"Arquivo não é um PDF: {file_path}")
                return 1
                
            processor = KoinlyProcessor(file_path)
            processor.process_report()
            processor.save_to_csv()
            logger.info(f"Processamento concluído: {file_path}")
            
        elif args.dir:
            # Process directory
            dir_path = Path(args.dir)
            if not dir_path.exists() or not dir_path.is_dir():
                logger.error(f"Diretório não encontrado: {dir_path}")
                return 1
                
            pdf_files = list(dir_path.glob('*.pdf'))
            if not pdf_files:
                logger.error(f"Nenhum arquivo PDF encontrado em: {dir_path}")
                return 1
                
            for pdf_file in pdf_files:
                logger.info(f"Processando: {pdf_file}")
                try:
                    processor = KoinlyProcessor(pdf_file)
                    processor.process_report()
                    processor.save_to_csv()
                    logger.info(f"Arquivo processado: {pdf_file}")
                except Exception as e:
                    logger.error(f"Erro ao processar {pdf_file}: {str(e)}")
                    # Log traceback if debugging
                    if log_level == logging.DEBUG:
                        logger.debug(traceback.format_exc())
                    
            logger.info(f"Processamento em lote concluído. {len(pdf_files)} arquivos processados.")
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("Processamento interrompido pelo usuário")
        return 130
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        # Log traceback if debugging
        if log_level == logging.DEBUG:
            logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 