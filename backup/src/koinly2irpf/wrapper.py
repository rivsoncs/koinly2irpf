#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo wrapper para compatibilidade com diferentes estruturas de importação.

Este módulo fornece um ponto de entrada comum para a aplicação, facilitando
a execução tanto diretamente quanto como pacote instalado.
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Try to add the parent directory to the path so we can import from src
# This is a fallback mechanism to ensure backwards compatibility
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def run_main():
    """
    Ponto de entrada para a aplicação quando chamada como comando.
    Esta função tenta diversas abordagens para executar a função main().
    """
    try:
        # Abordagem 1: Usar o novo módulo main_cli
        from koinly2irpf.main_cli import main
        logging.info("Usando o módulo main_cli para execução")
        return main()
    except ImportError:
        # Abordagem 2: Tentar o novo módulo main_entry
        try:
            from koinly2irpf.main_entry import main
            logging.info("Usando o módulo main_entry para execução")
            return main()
        except ImportError:
            # Abordagem 3: Tentar importar do módulo CLI
            try:
                from koinly2irpf.cli import main
                logging.info("Usando o módulo CLI para execução")
                return main()
            except ImportError:
                # Abordagem 4: Tentar importar da estrutura legada
                try:
                    # Fall back to legacy import paths
                    from src.main import main
                    logging.warning("Usando o path legado 'src.main'. Esta abordagem será removida em versões futuras.")
                    return main()
                except ImportError:
                    try:
                        # Adiciona o diretório src ao path para permitir importação
                        import site
                        site_packages = site.getsitepackages()
                        for site_pkg in site_packages:
                            src_path = os.path.join(site_pkg, 'src')
                            if os.path.exists(src_path) and src_path not in sys.path:
                                sys.path.insert(0, src_path)
                        
                        # Agora tenta importar o módulo main diretamente
                        try:
                            from main import main
                            logging.warning("Usando importação direta 'main'. Esta abordagem será removida em versões futuras.")
                            return main()
                        except ImportError:
                            logging.error("Todas as tentativas de importação falharam.")
                            print("ERRO: Não foi possível importar o módulo main.")
                            print("Isso pode ser devido a um problema na estrutura do pacote.")
                            print("Tente reinstalar o pacote: pip uninstall -y koinly2irpf && pip install --no-cache-dir git+https://github.com/rivsoncs/koinly2irpf.git")
                            return 1
                    except Exception as e:
                        logging.error(f"ERRO: {str(e)}")
                        return 1

if __name__ == "__main__":
    sys.exit(run_main())
