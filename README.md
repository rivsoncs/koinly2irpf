# Koinly2IRPF

Conversor de relatórios Koinly para IRPF brasileiro.

Este pacote processa relatórios do Koinly e os converte para um formato compatível com a declaração de Imposto de Renda de Pessoa Física (IRPF) no Brasil.

## Funcionalidades

- Processa relatórios PDF do Koinly ("Balances per Wallet")
- Extrai informações de criptomoedas, incluindo ticker, quantidade e valor
- Identifica automaticamente exchanges, carteiras e redes blockchain
- Extrai endereços de wallets e formata conforme exigido pela Receita Federal
- Gera um único arquivo CSV pronto para importação no programa da DIRPF

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## Instalação

### Método Recomendado (Usando o Script de Instalação)

A maneira mais fácil de instalar este pacote é usando o script de instalação fornecido:

1. Faça o download do script `install.py` deste repositório
2. Execute o script no terminal:

```bash
python install.py
```

Este script desinstalará qualquer versão anterior do pacote, limpará o cache do pip e instalará a versão mais recente diretamente do GitHub.

### Instalação Manual

Se preferir instalar manualmente, execute os seguintes comandos:

```bash
# Desinstala versões anteriores
pip uninstall -y koinly2irpf

# Limpa o cache do pip
pip cache purge

# Instala a versão mais recente
pip install --no-cache-dir --force-reinstall git+https://github.com/rivsoncs/koinly2irpf.git
```

## Uso

Após a instalação, você pode usar o comando `koinly2irpf` para processar seus relatórios:

```bash
# Processar um único arquivo
koinly2irpf caminho/para/seu/relatorio.pdf

# Processar todos os arquivos PDF em um diretório
koinly2irpf --dir caminho/para/diretorio
```

## Solução de Problemas

### Erro "No module named 'src'"

Se encontrar o erro `ModuleNotFoundError: No module named 'src'`, isso indica um problema com a instalação do pacote. Para resolver:

1. Execute o script `install.py` fornecido:
   ```bash
   python install.py
   ```

2. Ou reinstale manualmente:
   ```bash
   pip uninstall -y koinly2irpf
   pip cache purge
   pip install --no-cache-dir --force-reinstall git+https://github.com/rivsoncs/koinly2irpf.git
   ```

### Comando não encontrado

Se o comando `koinly2irpf` não estiver disponível após a instalação:

1. Verifique se o Python está no seu PATH
2. Reinstale o pacote usando uma das opções acima
3. Tente usar o Python diretamente:
   ```bash
   python -m koinly2irpf.main_entry seu_relatorio.pdf
   ```

## Contribuindo

Contribuições são bem-vindas! Se encontrar algum problema ou tiver sugestões de melhorias, sinta-se à vontade para abrir uma issue ou enviar um pull request.

## Licença

Este projeto está licenciado sob a Licença MIT. Consulte o arquivo `LICENSE` para obter mais detalhes.

## Estrutura do Projeto

- `koinly2irpf/`: Código fonte do projeto
  - `koinly2irpf/cli.py`: Ponto de entrada principal
  - `koinly2irpf/processor.py`: Lógica de processamento dos relatórios
- `setup.py`: Configuração para instalação via pip
- `requirements.txt`: Dependências do projeto

## Ajuda

Execute o comando com a flag `--help` para ver as opções disponíveis:

```bash
koinly2irpf --help
``` 