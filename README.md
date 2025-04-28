# Koinly2IRPF

Conversor de relatórios Koinly para IRPF brasileiro.

Este pacote processa relatórios do Koinly e os converte para um formato compatível com a declaração de Imposto de Renda de Pessoa Física (IRPF) no Brasil.

---

## Funcionalidades

- Processa relatórios PDF do Koinly ("Balances per Wallet")
- Extrai informações de criptomoedas, incluindo ticker, quantidade e valor
- Identifica automaticamente exchanges (globais e brasileiras), carteiras e redes blockchain
- Extrai endereços de wallets e formata conforme exigido pela Receita Federal
- Gera um único arquivo CSV pronto para importação no programa da DIRPF
- Suporte a múltiplos relatórios em lote
- Correção automática para carteiras BSC

---

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

---

## Instalação

### Instalação via GitHub

```bash
pip install git+https://github.com/rivsoncs/koinly2irpf.git
```

### Instalação manual (desenvolvedores)

Clone o repositório e instale localmente:

```bash
git clone https://github.com/rivsoncs/koinly2irpf.git
cd koinly2irpf
pip install -e .
```

---

## Uso

### Processar um único arquivo PDF

```bash
koinly2irpf caminho/para/relatorio.pdf
```

### Processar todos os arquivos PDF em um diretório

```bash
koinly2irpf caminho/para/diretorio/
```

O resultado será salvo como um arquivo CSV na mesma pasta do PDF.

---

## Solução de Problemas

- **Comando não encontrado:** Certifique-se de que o Python e o pip estão no PATH do sistema.
- **Erro de importação:** Reinstale o pacote usando o comando de instalação acima.
- **Problemas com dependências:** Execute `pip install -r requirements.txt` se estiver desenvolvendo localmente.

---

## Estrutura do Projeto

- `src/` - Código fonte principal
  - `koinly2irpf/` - Módulo do pacote
    - `cli.py` - Interface de linha de comando
    - `processor.py` - Lógica de processamento dos relatórios
    - `fix_binance_smart_chain.py` - Correção para carteiras BSC
    - `wrapper.py` - Entry point para o CLI
- `backup/` - (ignorado) Backup local do código
- `Exemplos-Reports/` - (ignorado) Relatórios de exemplo

---

## Contribuindo

Contribuições são bem-vindas! Se encontrar algum problema ou tiver sugestões de melhorias, abra uma issue ou envie um pull request.

---

## Licença

MIT 