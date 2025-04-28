import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

# Try to import KoinlyProcessor with different approaches to support both
# direct execution and package installation
try:
    from src.koinly_processor import KoinlyProcessor
    print("Successfully imported KoinlyProcessor from src.koinly_processor")
    # Try to import the BSC fix module to verify it's available
    try:
        from src.koinly2irpf.fix_binance_smart_chain import process_wallet_details_for_bsc
        print("BSC fix module successfully imported from src.koinly2irpf")
    except ImportError as e:
        print(f"BSC fix module import failed: {e}")
except ImportError:
    try:
        from koinly_processor import KoinlyProcessor
        print("Successfully imported KoinlyProcessor from koinly_processor")
        # Try to import the BSC fix module to verify it's available
        try:
            from koinly2irpf.fix_binance_smart_chain import process_wallet_details_for_bsc
            print("BSC fix module successfully imported from koinly2irpf")
        except ImportError as e:
            print(f"BSC fix module import failed: {e}")
    except ImportError as e:
        print(f"Error: Could not import KoinlyProcessor module: {e}")
        sys.exit(1)

# <<< Adição: Configuração básica do logging >>>
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("Logging configurado para nível DEBUG.")
# <<< Fim Adição >>>

# Carrega as variáveis de ambiente
load_dotenv()

# Configuração dos diretórios
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
EXAMPLES_DIR = BASE_DIR / 'Exemplos-Reports'

def process_reports():
    """
    Função principal que processa os relatórios e gera o arquivo CSV final.
    """
    # Verifica se há argumento de ajuda
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Conversor de Relatórios Koinly para IRPF")
        print("\nUso:")
        print("  reports-to-irpf <caminho_para_arquivo.pdf>")
        print("\nExemplos:")
        print("  reports-to-irpf relatorio.pdf")
        print("  reports-to-irpf \"C:\\Meus Documentos\\relatorio.pdf\"")
        print("\nOpções:")
        print("  -h, --help    Exibe esta mensagem de ajuda")
        return
    
    print("Processando relatórios...")
    
    # Verifica se foi fornecido um arquivo específico como argumento
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        if pdf_path.exists() and pdf_path.is_file() and pdf_path.suffix.lower() == '.pdf':
            process_single_file(pdf_path)
        else:
            print(f"Arquivo não encontrado ou não é um PDF válido: {pdf_path}")
    else:
        print("Por favor, forneça o caminho para um arquivo PDF.")
        print("Uso: reports-to-irpf caminho/para/seu/arquivo.pdf")
        print("Para ajuda, digite: reports-to-irpf --help")
        sys.exit(1)
    
    print("Processamento concluído!")

def process_single_file(pdf_file):
    """
    Processa um único arquivo PDF.
    """
    print(f"\nProcessando arquivo: {pdf_file.name}")
    
    # Cria o processador para o arquivo atual
    processor = KoinlyProcessor(pdf_file)
    
    # Define o caminho de saída para o CSV no mesmo diretório do arquivo de entrada
    output_file = pdf_file.with_suffix('.csv')
    
    # Processa e salva o arquivo
    processor.save_to_csv(output_file)
    print(f"Arquivo processado e salvo em: {output_file}")

def main():
    """
    Função principal que executa o processamento dos relatórios.
    """
    # Cria os diretórios se não existirem
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    try:
        process_reports()
    except Exception as e:
        print(f"Erro durante o processamento: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 