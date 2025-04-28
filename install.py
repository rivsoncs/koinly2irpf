#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de instalação para o pacote koinly2irpf.
Este script desinstala qualquer versão existente e instala a versão atualizada.
"""

import os
import sys
import subprocess
import time

def run_command(cmd, description=None):
    """Executa um comando e exibe o resultado."""
    if description:
        print(f"\n{description}...")
    
    print(f"\nExecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(f"Saída:\n{result.stdout}")
    
    if result.stderr:
        print(f"Erro:\n{result.stderr}")
    
    print(f"Código de saída: {result.returncode}")
    return result.returncode == 0

def main():
    """Função principal para instalar o pacote."""
    print("=" * 80)
    print("INSTALADOR DO KOINLY2IRPF")
    print("=" * 80)
    print("\nEste script irá desinstalar qualquer versão existente do koinly2irpf")
    print("e instalar a versão mais recente diretamente do GitHub.")
    
    # Verifica se está executando como administrador no Windows
    if sys.platform.startswith('win'):
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        
        if not is_admin:
            print("\nATENÇÃO: Para melhor resultado, execute este script como administrador!")
            input("Pressione Enter para continuar mesmo assim, ou feche e execute como administrador...")
    
    # Desinstala qualquer versão anterior
    print("\nPasso 1: Desinstalar versões anteriores")
    run_command([sys.executable, "-m", "pip", "uninstall", "-y", "koinly2irpf"], 
               "Desinstalando koinly2irpf")
    
    # Limpa o cache do pip
    print("\nPasso 2: Limpar o cache do pip")
    run_command([sys.executable, "-m", "pip", "cache", "purge"], 
               "Limpando o cache do pip")
    
    # Instala a versão mais recente do GitHub
    print("\nPasso 3: Instalar a versão mais recente")
    success = run_command(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--force-reinstall", 
         "git+https://github.com/rivsoncs/koinly2irpf.git"], 
        "Instalando koinly2irpf do GitHub"
    )
    
    if success:
        print("\nInstalação concluída com sucesso!")
        print("\nAgora você pode usar o comando 'koinly2irpf' para processar seus relatórios.")
        print("Exemplo: koinly2irpf seu_relatorio.pdf")
    else:
        print("\nOcorreu um erro durante a instalação.")
        print("Tente instalar manualmente com o comando:")
        print("pip install --no-cache-dir --force-reinstall git+https://github.com/rivsoncs/koinly2irpf.git")
    
    # Pequena pausa para verificar se tudo está funcionando
    print("\nVerificando se o comando está disponível...")
    time.sleep(2)
    
    # Tenta executar o comando para verificar se está funcionando
    run_command(["koinly2irpf", "--help"], "Testando o comando koinly2irpf")
    
    print("\n" + "=" * 80)
    print("Instalação completa! Pressione Enter para sair...")
    input()
    return 0

if __name__ == "__main__":
    sys.exit(main()) 