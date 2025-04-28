#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ponto de entrada principal para o koinly2irpf.
Este módulo serve como um invólucro independente que funcionará
tanto para execução direta quanto para instalação como pacote.
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """
    Função principal que executa o processamento dos relatórios.
    """
    parser = argparse.ArgumentParser(description='Conversor de relatórios Koinly para IRPF')
    
    # Grupo mutuamente exclusivo para arquivo ou diretório
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('file', nargs='?', type=str, 
                       help='Caminho para o arquivo PDF do Koinly')
    group.add_argument('--dir', type=str, 
                       help='Diretório contendo arquivos PDF do Koinly para processamento em lote')
    
    args = parser.parse_args()
    
    try:
        # Importar o KoinlyProcessor
        try:
            from koinly2irpf.processor import KoinlyProcessor
            logger.info("Usando KoinlyProcessor do pacote koinly2irpf.processor")
        except ImportError:
            try:
                from processor import KoinlyProcessor
                logger.info("Usando KoinlyProcessor do módulo local processor")
            except ImportError:
                logger.error("Não foi possível importar o KoinlyProcessor. Verifique a instalação do pacote.")
                print("ERRO: Estrutura de pacote inválida. Por favor, reinstale o pacote.")
                print("Comando: pip uninstall -y koinly2irpf && pip install git+https://github.com/rivsoncs/koinly2irpf.git")
                return 1
        
        # Processamento do arquivo ou diretório
        if args.file:
            # Processa um único arquivo
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"Arquivo não encontrado: {file_path}")
                return 1
                
            if not file_path.name.lower().endswith('.pdf'):
                logger.error(f"Arquivo não é um PDF: {file_path}")
                return 1
                
            logger.info(f"Processando arquivo: {file_path}")
            processor = KoinlyProcessor(file_path)
            processor.process_report()
            processor.save_to_csv()
            logger.info(f"Processamento concluído: {file_path}")
            
        elif args.dir:
            # Processa diretório
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
                    
            logger.info(f"Processamento em lote concluído. {len(pdf_files)} arquivos processados.")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Processamento interrompido pelo usuário")
        return 130
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 