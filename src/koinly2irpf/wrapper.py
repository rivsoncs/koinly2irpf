#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo wrapper para compatibilidade com diferentes estruturas de importação.

Este módulo fornece um ponto de entrada comum para a aplicação, facilitando
a execução tanto diretamente quanto como pacote instalado.
"""

import sys
import os

def run_main():
    """
    Ponto de entrada para a aplicação quando chamada como comando.
    Esta função tenta diversas abordagens para executar a função main().
    """
    try:
        # Abordagem 1: Usar o novo módulo main_entry
        from koinly2irpf.main_entry import main
        print("Usando o módulo main_entry para execução")
        return main()
    except ImportError:
        # Abordagem 2: Tentar importações alternativas
        try:
            # Tentando importar do módulo CLI
            from koinly2irpf.cli import main
            print("Usando o módulo CLI para execução")
            return main()
        except ImportError:
            # Abordagem 3: Tentar importar da estrutura legada
            try:
                # Adiciona o diretório src ao path para permitir importação
                import site
                site_packages = site.getsitepackages()
                for site_pkg in site_packages:
                    src_path = os.path.join(site_pkg, 'src')
                    if os.path.exists(src_path) and src_path not in sys.path:
                        sys.path.insert(0, src_path)
                
                # Agora tenta importar o módulo main
                try:
                    from main import main
                    print("Usando o módulo main legado")
                    return main()
                except ImportError:
                    print("ERRO: Não foi possível importar o módulo main.")
                    print("Isso pode ser devido a um problema na estrutura do pacote.")
                    print("Tente reinstalar o pacote: pip uninstall -y koinly2irpf && pip install --no-cache-dir git+https://github.com/rivsoncs/koinly2irpf.git")
                    return 1
            except Exception as e:
                print(f"ERRO: {str(e)}")
                return 1

if __name__ == "__main__":
    sys.exit(run_main()) 