# Reports to IRPF

Conversor de relatórios financeiros do Koinly para formato compatível com a declaração do Imposto de Renda Pessoa Física (IRPF) brasileira.

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

### Método 1: Instalação via GitHub (Recomendado)

```bash
pip install git+https://github.com/rivsoncs/koinly2irpf.git
```

Após a instalação, o comando `koinly2irpf` estará disponível no terminal.

### Método 2: Execução direta (Sem instalação)

```bash
# Clone o repositório
git clone https://github.com/rivsoncs/koinly2irpf.git
cd koinly2irpf

# Execute o script diretamente
python -m koinly2irpf.cli caminho/para/seu/relatorio.pdf
```

### Método 3: Instalação para desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/rivsoncs/koinly2irpf.git
cd koinly2irpf

# Instale em modo de desenvolvimento
pip install -e .
```

## Uso

### Após instalação via pip (Método 1)

```bash
koinly2irpf caminho/para/seu/relatorio.pdf
```

### Execução direta (Método 2)

```bash
python -m koinly2irpf.cli caminho/para/seu/relatorio.pdf
```

### Exemplos

```bash
# Processar um relatório específico
koinly2irpf ~/Downloads/koinly_2024_balances_per_wallet.pdf

# Passar caminho absoluto com espaços (use aspas)
koinly2irpf "C:\Users\Usuario\Meus Documentos\koinly_2024_balances_per_wallet.pdf"

# Executar diretamente (sem instalação)
python -m koinly2irpf.cli Exemplos-Reports/koinly_2024_balances_per_wallet.pdf
```

## Saída

O programa gera um arquivo CSV no **mesmo diretório** do arquivo PDF processado, contendo:

- **Ticker:** Símbolo da criptomoeda (Ex: BTC, ETH, SOL)
- **Qtd:** Quantidade da criptomoeda
- **Valor R$ 31/12/YYYY:** Valor em Reais na data de 31/12 do ano do relatório
- **Discriminação:** Descrição detalhada no formato exigido pela Receita Federal
  - Inclui identificação de carteira/exchange
  - Especifica rede blockchain quando disponível
  - Mostra parte do endereço da wallet quando disponível
- **Cnpj:** Campo vazio para preenchimento manual se necessário

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

## Contribuição

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Crie um Pull Request 

## Atualização

### Atualização da versão instalada via pip

Se você já tem o software instalado via pip e deseja atualizar para a versão mais recente:

```bash
pip install --upgrade git+https://github.com/rivsoncs/koinly2irpf.git
```

### Atualização da versão de desenvolvimento

Se você instalou o software em modo de desenvolvimento:

```bash
# Navegue até o diretório do repositório
cd koinly2irpf

# Atualize o código fonte
git pull

# Não é necessário reinstalar se você usou pip install -e .
# As mudanças no código são automaticamente refletidas
```

## Desinstalação

### Desinstalar versão instalada via pip

```bash
pip uninstall koinly2irpf
```

### Remover completamente (incluindo repositório local)

Se você clonou o repositório:

```bash
# Desinstale o pacote primeiro (se instalado)
pip uninstall koinly2irpf

# Depois, remova o diretório do repositório
# No Windows:
rmdir /s /q koinly2irpf

# No Linux/macOS:
rm -rf koinly2irpf
``` 