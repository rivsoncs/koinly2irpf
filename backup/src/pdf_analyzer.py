import tabula
import pandas as pd
from pathlib import Path

def analyze_pdf(pdf_path: Path):
    """
    Analisa a estrutura de um PDF e retorna informações sobre suas tabelas.
    """
    print(f"\nAnalisando arquivo: {pdf_path.name}")
    
    # Tenta extrair todas as tabelas do PDF
    tables = tabula.read_pdf(str(pdf_path), pages='all', multiple_tables=True)
    
    print(f"\nNúmero de tabelas encontradas: {len(tables)}")
    
    for i, table in enumerate(tables, 1):
        print(f"\nTabela {i}:")
        print(f"Colunas: {table.columns.tolist()}")
        print(f"Formato: {table.shape}")
        print("\nPrimeiras linhas:")
        print(table.head())
        print("\n" + "="*50)

if __name__ == "__main__":
    # Analisa o primeiro PDF como exemplo
    pdf_path = Path("Exemplos-Reports/koinly_2024_balances_per_wallet_aVgUBXTvP5_0.pdf")
    analyze_pdf(pdf_path) 