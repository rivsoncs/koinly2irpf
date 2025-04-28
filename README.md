# Koinly2IRPF

Conversor de relatórios Koinly para IRPF brasileiro.

## Instalação

Instale diretamente do GitHub:

```bash
pip install git+https://github.com/rivsoncs/koinly2irpf.git
```

## Uso

Processamento de um relatório PDF:

```bash
koinly2irpf caminho/para/relatorio.pdf
```

Ou para um diretório com vários arquivos:

```bash
koinly2irpf caminho/para/diretorio/
```

O resultado será salvo como um arquivo CSV na mesma pasta do PDF.

## Funcionalidades
- Identificação automática de exchanges (globais e brasileiras)
- Descrições detalhadas para IRPF
- Suporte a múltiplos relatórios
- Correção automática para carteiras BSC

## Estrutura do Projeto
- `src/` - Código fonte principal
- `src/koinly2irpf/` - Módulo do pacote
- `backup/` - (ignorado) Backup local do código
- `Exemplos-Reports/` - (ignorado) Relatórios de exemplo

## Contribuição
Pull requests são bem-vindos!

## Licença
MIT 