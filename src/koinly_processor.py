import pdfplumber
import pandas as pd
from pathlib import Path
import re
from typing import List, Dict, Tuple
import locale
import traceback
import csv
import logging

# Import the BSC fix module with multiple fallback options
try:
    # Try to import directly from koinly2irpf
    from koinly2irpf.fix_binance_smart_chain import process_wallet_details_for_bsc
    BSC_MODULE_AVAILABLE = True
    print("BSC fix module successfully imported from koinly2irpf")
except ImportError:
    try:
        # Try to import from src.koinly2irpf
        from src.koinly2irpf.fix_binance_smart_chain import process_wallet_details_for_bsc
        BSC_MODULE_AVAILABLE = True
        print("BSC fix module successfully imported from src.koinly2irpf")
    except ImportError:
        # If both imports fail
        BSC_MODULE_AVAILABLE = False
        print("BSC fix module not found, BSC detection improvements will not be applied")

print("--- Módulo koinly_processor.py carregado ---")

# Constants for parsing and generation
KNOWN_EXCHANGES = [
    'binance', 'coinbase', 'kraken', 'bybit', 'okx', 'kucoin', 'gate.io',
    'mexc', 'bitget', 'bingx', 'bitfinex', 'huobi', 'crypto.com',
    'mercado bitcoin', 'bitso', 'foxbit', 'novaDAX', 'coinext', 'bitcointrade',
    'binance us', 'ftx', 'coinex', # Adding more known exchanges
]
KNOWN_WALLET_BRANDS = [
    'ledger', 'trezor', 'metamask', 'trust wallet', 'exodus', 'atomic wallet',
    'phantom', 'solflare', 'keplr', 'rabby', 'coinomi', 'myetherwallet', 'mew',
    'zengo', 'safe', 'safepal', 'argent', 'unstoppable', 'brave', # Adding more brands
]
KNOWN_BLOCKCHAINS = [
    'bitcoin', 'ethereum', 'solana', 'polygon', 'arbitrum', 'optimism', 'avalanche',
    'binance smart chain', 'bsc', 'base', 'cardano', 'polkadot', 'near protocol', 'near',
    'cosmos', 'atom', 'hedera', 'tron', 'litecoin', 'bitcoin cash', 'stellar', 'xlm',
    'algorand', 'tezos', 'fantom', 'cronos', 'celo', 'zksync', 'starknet', 'aptos',
    'sui', 'sei', 'injective', 'osmosis', 'thorchain', 'celestia', 'kava', 'secret network',
    'zcash', 'monero', 'dash', 'dogecoin', # Adding common blockchain names
]
KNOWN_BLOCKCHAINS_FOR_TYPE = {'bitcoin', 'ethereum', 'solana', 'polygon', 'arbitrum', 'optimism', 'base', 'bsc', 'fantom', 'avalanche', 'tron', 'cosmos', 'polkadot', 'cardano', 'near', 'celestia', 'sui', 'aptos', 'sei', 'injective'} # Blockchains que definem o 'tipo' como REDE

class KoinlyProcessor:
    def __init__(self, pdf_path: Path):
        print(f"--- KoinlyProcessor.__init__ INICIO para: {pdf_path.name} ---")
        self.pdf_path = pdf_path
        self.year = self._extract_year()
        self._setup_locale()
        print(f"\n--- Inicializando processador (pdfplumber) para: {pdf_path.name} (Ano: {self.year}) ---")
        # print(f"--- KoinlyProcessor.__init__ FIM para: {pdf_path.name} ---") # Comentado para teste

        # Common Patterns
        self.currency_header_pattern = re.compile(r"^\s*Currency\s+Amount\s+Price\s+Value\s*", re.IGNORECASE | re.DOTALL)
        self.address_pattern = re.compile(r"^[0-9a-zA-Z]{7,}")  # Padrão genérico para endereços

        # Patterns for Wallet Details
        # ... existing code ...

    def _extract_year(self) -> str:
        try:
            # Tenta pegar o ano como o segundo elemento separado por _
            parts = self.pdf_path.stem.split('_')
            if len(parts) > 1 and parts[1].isdigit() and len(parts[1]) == 4:
                return parts[1]
            # Fallback: tenta encontrar 4 dígitos consecutivos no nome do arquivo
            match = re.search(r'(\d{4})', self.pdf_path.stem)
            if match:
                return match.group(1)
        except Exception as e:
            print(f"Erro ao extrair ano de {self.pdf_path.name}: {e}")
        
        print(f"Aviso: Não foi possível extrair o ano do nome do arquivo {self.pdf_path.name}. Usando padrão.")
        return "ANO_INVALIDO" # Retorna um valor padrão claro

    def _setup_locale(self):
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252') # Windows fallback
            except locale.Error:
                print("Aviso: Não foi possível configurar o locale pt_BR. A formatação de números pode não usar vírgula.")

    def _clean_numeric_str(self, num_str: str | None, remove_currency: bool = True) -> str:
        if num_str is None:
            return '0'
        num_str = str(num_str)
        if remove_currency:
            num_str = num_str.replace('R$', '')
        # Remove espaços
        num_str = num_str.replace(' ', '') 
        # Trata casos como '1.234,56' ou '1,234.56' para padrão US float '1234.56'
        if ',' in num_str and '.' in num_str:
            if num_str.rfind('.') > num_str.rfind(','): # Ponto é separador decimal (US)
                cleaned = num_str.replace(',', '')
            else: # Vírgula é separador decimal (BR/EU)
                cleaned = num_str.replace('.', '').replace(',', '.')
        elif ',' in num_str: # Apenas vírgula (assume ser decimal BR/EU)
             cleaned = num_str.replace(',', '.')
        else: # Apenas ponto ou nenhum separador (assume US ou inteiro)
             cleaned = num_str 
        
        # Remove caracteres não numéricos restantes (exceto ponto decimal e sinal negativo no início)
        cleaned = re.sub(r'[^0-9.-]', '', cleaned)
        # Garante que só haja um ponto decimal
        if cleaned.count('.') > 1:
             parts = cleaned.split('.')
             cleaned = parts[0] + '.' + ''.join(parts[1:])
        # Garante que o sinal negativo esteja apenas no início
        if '-' in cleaned[1:]:
            cleaned = cleaned.replace('-','') # Remove traços extras
            if num_str.strip().startswith('-'):
                 cleaned = '-' + cleaned
                 
        return cleaned if cleaned and cleaned != '-' else '0'

    def _parse_eoy_section(self, text: str) -> Dict[str, Dict]:
        print("--- _parse_eoy_section INICIO ---")
        balances = {}
        eoy_pattern = re.compile(
            r"^(?!Total\b)(.+?)\s+"                     # Asset Name (Grupo 1) - Non-greedy, not starting with Total (word boundary)
            r"([\d.,]+)\s+"                         # Quantity (Grupo 2)
            r"(?:R\$\s*)?(-?\(?\d[\d.,]*\)?)\s+" # Cost (BRL) (Grupo 3) - Handles negatives in () or with -, must start with digit
            r"(?:R\$\s*)?(-?\(?\d[\d.,]*\)?)\s*" # Value (BRL) (Grupo 4) - Handles negatives, must start with digit, espaço opcional no fim
            r"(.*)"                                  # Description (Grupo 5)
            , re.MULTILINE | re.IGNORECASE
        )

        # 1. Encontra o título da seção EOY
        eoy_title_match = re.search(r"End of Year Balances", text, re.IGNORECASE)
        if not eoy_title_match:
            print("Aviso: Seção 'End of Year Balances' não encontrada.")
            return {}
        eoy_title_end_index = eoy_title_match.end()

        # 2. Procura pelo CABEÇALHO *depois* do título
        header_pattern = r"Asset\s+Quantity\s+Cost\s*\(BRL\)\s+Value\s*\(BRL\)\s+Description"
        header_match = re.search(header_pattern, text[eoy_title_end_index:], re.IGNORECASE)
        if not header_match:
            print("Aviso: Cabeçalho EOY ('Asset Quantity Cost...') não encontrado após o título.")
            return {}
        # Índice do fim do header RELATIVO ao início da busca (eoy_title_end_index)
        header_end_rel_index = header_match.end()
        # Índice absoluto do fim do header no texto completo
        header_end_abs_index = eoy_title_end_index + header_end_rel_index
        print(f"Cabeçalho EOY encontrado: '{header_match.group(0)}'")

        # 3. Procura pela linha TOTAL *depois* do cabeçalho
        total_match = re.search(r"^\s*Total\b", text[header_end_abs_index:], re.MULTILINE | re.IGNORECASE)
        if not total_match:
            print("Aviso: Linha 'Total' não encontrada após o cabeçalho EOY. Usando fim do texto como limite.")
            # Usa o fim do texto como limite, ou o início da próxima seção se mais confiável
            details_start_match = re.search(r"Balances per Wallet|Transactions", text[header_end_abs_index:], re.IGNORECASE)
            total_start_abs_index = header_end_abs_index + details_start_match.start() if details_start_match else len(text)
        else:
            # Índice do início do Total RELATIVO ao início da busca (header_end_abs_index)
            total_start_rel_index = total_match.start()
            # Índice absoluto do início do Total no texto completo
            total_start_abs_index = header_end_abs_index + total_start_rel_index
            print(f"Linha Total EOY encontrada: '{total_match.group(0)}'")

        # 4. Extrai o texto da tabela EOY (entre o fim do header e o início do total)
        eoy_table_text = text[header_end_abs_index:total_start_abs_index].strip()

        print(f"--- DEBUG: Texto da Tabela EOY (Primeiras/Últimas 5 linhas) ---")
        eoy_lines_for_debug = eoy_table_text.split('\n')
        for line in eoy_lines_for_debug[:5]: print(line.strip())
        print("...")
        for line in eoy_lines_for_debug[-5:]: print(line.strip())
        print("--- FIM DEBUG EOY TABLE TEXT ---")

        lines = eoy_table_text.split('\n')
        processed_count = 0
        print(f"Analisando {len(lines)} linhas na tabela EOY potencial.")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Não precisa mais procurar header ou total aqui

            match = eoy_pattern.match(line)
            if match:
                try:
                    asset = match.group(1).strip()
                    if not asset or asset.lower() == 'asset': continue
                    asset = re.sub(r'\s*@\s*R\$.*$', '', asset).strip()
                    if not asset: continue

                    quantity_str = match.group(2)
                    cost_str = match.group(3).replace('(', '-').replace(')', '')
                    value_str = match.group(4).replace('(', '-').replace(')', '')
                    desc = match.group(5).strip()

                    quantity = float(self._clean_numeric_str(quantity_str, remove_currency=False))
                    cost = float(self._clean_numeric_str(cost_str))
                    value = float(self._clean_numeric_str(value_str))

                    if quantity < 0:
                         print(f"Pulando linha EOY suspeita (quantidade negativa): '{line}'")
                         continue

                    balances[asset] = {
                        'total_quantity': quantity,
                        'total_cost_brl': cost,
                        'total_value_brl': value,
                        'description': desc
                    }
                    processed_count += 1
                except (ValueError, TypeError, IndexError) as e:
                     print(f"Erro ao processar linha EOY (regex match): '{line}', Erro: {e}")
                     print(traceback.format_exc())
            else:
                if len(line) > 5 and any(c.isalpha() for c in line):
                     print(f"Linha EOY não reconhecida pela regex: '{line}'")

        print(f"EOY Balances processados (regex): {processed_count} itens")
        # Guarda o índice final da seção EOY processada para ajudar a próxima seção
        self._last_eoy_section_end_index = total_start_abs_index 
        print("--- _parse_eoy_section FIM ---")
        return balances

    def _extract_title_parts_from_match(self, match, line, is_koinly_pattern):
        """Extracts the wallet name, blockchain type, and address from a regex match object."""
        try:
            wallet_name_part = "Unknown Wallet"
            blockchain_part = "None"
            address_part = None
            is_bitcoin_wallet = False
            
            # Log what we're trying to extract
            logging.debug(f"Extracting title parts from match: {match}, Line: {line}, Is Koinly pattern: {is_koinly_pattern}")
            
            if is_koinly_pattern:
                # Processo para padrão koinly_title_pattern
                # Group 1: Bitcoin específico
                # Group 2: Nome geral de carteira/exchange
                # Group 3: zpub address (optional)
                # Groups 1 & 2 are mutually exclusive
                
                if match.group(1): # Bitcoin específico
                    wallet_name_part = match.group(1).strip()
                    blockchain_part = "Bitcoin"
                    is_bitcoin_wallet = True
                    logging.debug(f"Bitcoin title detected: {wallet_name_part}")
                elif match.group(2): # Nome geral de carteira/exchange
                    wallet_name_part = match.group(2).strip()
                    
                    # Check for zpub address in group 3
                    if match.group(3):
                        address_part = match.group(3).strip()
                        # If we have a zpub address under a title containing "Bitcoin", this is a Bitcoin wallet
                        if "Bitcoin" in wallet_name_part:
                            blockchain_part = "Bitcoin"
                            wallet_name_part = "Carteira Bitcoin"
                            is_bitcoin_wallet = True
                            logging.debug(f"Bitcoin wallet with zpub address detected: {address_part}")
                    
                    # Parse network name from wallet_name_part if in format "Wallet - Network"
                    wallet_network_parts = wallet_name_part.split(' - ')
                    if len(wallet_network_parts) > 1:
                        wallet_base_name = wallet_network_parts[0].strip()
                        potential_network = wallet_network_parts[1].strip()
                        
                        # Check if network part contains blockchain name
                        network_clean = re.sub(r'\s*\([^)]*\)', '', potential_network).strip()  # Remove parentheses
                        
                        # Check if it's a known blockchain
                        for blockchain in KNOWN_BLOCKCHAINS:
                            # Case insensitive comparison
                            if blockchain.lower() in network_clean.lower():
                                blockchain_part = network_clean
                                wallet_name_part = wallet_base_name
                                logging.debug(f"Network detected from title: {blockchain_part}")
                                break
                    
                    # Look for wallet address in the title (often in format "Wallet - Network - 0x1234...")
                    if len(wallet_network_parts) > 2:
                        potential_address = wallet_network_parts[-1].strip()
                        # Check for common address patterns
                        address_matches = [
                            # Ethereum and EVM addresses
                            re.search(r'(0x[a-fA-F0-9]{4,}(?:\.\.\.[a-fA-F0-9]{2,})?)', potential_address),
                            # Bitcoin addresses (includes xpub, ypub, zpub formats)
                            re.search(r'([xyzXYZ]pub[a-zA-Z0-9]{4,}(?:\.\.\.[a-zA-Z0-9]{2,})?)', potential_address),
                            # Generic shortened addresses with ellipsis
                            re.search(r'([a-zA-Z0-9]{4,}\.\.\.[a-zA-Z0-9]{2,})', potential_address)
                        ]
                        
                        for addr_match in address_matches:
                            if addr_match:
                                address_part = addr_match.group(1)
                                # If it's a Bitcoin-style address, set Bitcoin as blockchain
                                if address_part and any(prefix in address_part.lower() for prefix in ['xpub', 'ypub', 'zpub']):
                                    blockchain_part = "Bitcoin"
                                    is_bitcoin_wallet = True
                                    logging.debug(f"Bitcoin address format detected: {address_part}")
                                # If it's an Ethereum-style address, set Ethereum as blockchain
                                elif address_part and address_part.startswith('0x'):
                                    # If we don't already have a specific blockchain and this is an ETH address
                                    if blockchain_part == "None":
                                        blockchain_part = "Ethereum"
                                        logging.debug(f"Ethereum address format detected: {address_part}")
                                
                                # If shortened address (with ...), try to reconstruct full form
                                if '...' in address_part:
                                    prefix = address_part.split('...')[0]
                                    suffix = address_part.split('...')[-1]
                                    # Store both parts for later use
                                    address_part = f"{prefix}...{suffix}"
                                logging.debug(f"Address detected from title: {address_part}")
                                break

            # If we still don't have a blockchain identification, try one more heuristic check
            if blockchain_part == "None" and not is_bitcoin_wallet:
                # Check if wallet name contains a known blockchain name
                for blockchain in KNOWN_BLOCKCHAINS:
                    if blockchain.lower() in wallet_name_part.lower():
                        blockchain_part = blockchain
                        logging.debug(f"Blockchain detected from wallet name: {blockchain_part}")
                        break

            # Special handling for Binance Smart Chain wallets
            # If the name contains Binance Smart Chain, BSC, or BNB chain, 
            # it should be recognized as a blockchain not an exchange
            bsc_keywords = ['binance smart chain', 'bsc', 'bnb chain']
            is_bsc_wallet = False
            for keyword in bsc_keywords:
                if keyword.lower() in wallet_name_part.lower():
                    is_bsc_wallet = True
                    blockchain_part = "BSC"
                    logging.debug(f"BSC wallet detected from name: {wallet_name_part}")
                    break

            # Detect exchange based on name (simple heuristic), but only if not a BSC wallet
            # Using "Exchange" as blockchain helps later processing differentiate CEX from Wallets
            if not is_bsc_wallet:
                known_exchanges = ['Binance', 'CoinEx', 'BingX', 'Mercado Bitcoin', 'Gate.io', 'KuCoin', 'OKX'] 
                if any(ex.lower() in wallet_name_part.lower() for ex in known_exchanges):
                    # Double check it's not a BSC wallet before marking as exchange
                    if not any(bsc.lower() in wallet_name_part.lower() for bsc in bsc_keywords):
                        blockchain_part = "Exchange"
                        logging.debug(f"      >>> Detectado como Exchange: Nome='{wallet_name_part}'")

            logging.debug(f"    Valores extraídos do título: Nome='{wallet_name_part}', Blockchain='{blockchain_part}', AddrNaLinha='{address_part}', ÉBitcoin={is_bitcoin_wallet}")
            return wallet_name_part, blockchain_part, address_part, is_bitcoin_wallet
        except Exception as e:
            print(f"Erro ao extrair partes do título: {e}")
            traceback.print_exc()
            return wallet_name_part, blockchain_part, address_part, is_bitcoin_wallet

    def _parse_wallet_details_section(self, text_lines):
        """Parses the 'Balances per Wallet' section using a stateful line-by-line approach."""
        logging.info("--- _parse_wallet_details_section INICIO ---")
        wallet_details = []
        current_wallet_info = {
            "name": "Unknown Wallet",
            "type": "Unknown",
            "address": None
        }
        in_wallet_section = False
        header_found_for_current_wallet = False
        last_captured_address = None # Variável para guardar o último endereço capturado

        # Regex patterns
        # More robust Wallet/Exchange Title detection
        # Matches lines that likely start a new wallet/exchange section
        # Often Title Case, sometimes all caps, may include hyphens, numbers, spaces
        # Let's look for lines that don't look like currency data and have substantial capitalization
        # or end with a typical address format indicator or known wallet brand starter
        # Corrected title_pattern regex
        title_pattern = re.compile(r"^([A-Z][\\w\\s\\-\\(\\).]+?)(?:\\s+-+\\s+0x[a-fA-F0-9]+)?\\s*$")
        # Improved detection based on common Koinly patterns:
        # 1. Name only (e.g., Binance, ByBit, Gate.io)
        # 2. Name - Network (e.g., MetaMask - Arbitrum)
        # 3. Name - Network - Address (e.g., MetaMask (2) - Arbitrum - 0xcf...69)
        # 4. Bitcoin wallet ZPUB address line
        koinly_title_pattern = re.compile(
            r"^"                            # Start of line
            # Group 1: Captura 'Bitcoin' opcionalmente seguido por '(BTC)' e fim de linha
            r"(?:(Bitcoin(?:\\s*\\(BTC\\))?)\\s*$)"
            r"|"                             # OU
            # Group 2: Captura outros nomes de carteira/exchange
            # Group 3: Captura opcional zpub APÓS ' - ' na MESMA linha do nome
            # Corrected koinly_title_pattern regex character set
            r"([A-Za-z0-9][A-Za-z0-9\\s\\-\\(\\).]*?)(?:\\s+-\\s+(zpub[a-zA-Z0-9]+))?"
            r"\\s*$"                         # End of line
            , re.IGNORECASE
        )
        # Adding patterns for explicit addresses and Total Value lines
        address_pattern = re.compile(r"^Wallet address:\\s+(.+)$", re.IGNORECASE)
        total_value_pattern = re.compile(r"^Total wallet value at", re.IGNORECASE)
        # Use self.currency_header_pattern instead of defining a new one
        # Currency data pattern (adjust based on previous findings)
        # Original WALLET_DETAILS_REGEX: r"^(?P<currency>[A-Z0-9\-]+(?:\s\([A-Za-z ]+\))?)\s+(?P<amount>[\d,\.]+)\s+(?P<price>[\d,\.]+)\s+(?P<value>[\d,\.]+)$"
        # Let's use a more specific one based on observation:
        # CURRENCY_NAME AMOUNT PRICE VALUE
        currency_data_pattern = re.compile(
            r"^"                                      # Start of line
            r"(?P<currency>[A-Z0-9\/\#\.\-]+(?:\s*\(.+?\))?)" # Currency Ticker/Name (Group 'currency')
            r"\s+"
            r"(?P<amount>[\d,\.]+)"                   # Amount (Group 'amount')
            r"\s+"
            r"R\$(?P<price>[\d,\.]+)"                 # Price (Group 'price') - Capture number after R$
            r"\s+"
            r"R\$(?P<value>[\d,\.]+)"                  # Value (Group 'value') - Capture number after R$
            r"\s*$"                                     # End of line
        )

        # Find the start of the section
        start_index = -1
        try:
            # Prefer finding it after EOY Balances if possible, but search whole doc if needed
            # This part might need refinement based on how text_lines is generated (is it the whole doc?)
            start_index = next(i for i, line in enumerate(text_lines) if "Balances per Wallet" in line)
            logging.info(f"Seção 'Balances per Wallet' encontrada, iniciando análise a partir do índice {start_index}.")
            in_wallet_section = True
        except StopIteration:
            logging.error("'Balances per Wallet' section marker not found.")
            return pd.DataFrame() # Return empty DataFrame if section not found

        if start_index == -1:
             logging.error("'Balances per Wallet' section marker not found after search.")
             return pd.DataFrame()

        wallet_lines = text_lines[start_index + 1:]
        total_lines = len(wallet_lines)
        logging.info(f"Analisando {total_lines} linhas na seção Wallet Details.")

        for i, line in enumerate(wallet_lines): # Use wallet_lines here
            line = line.strip()
            current_line_num = start_index + i + 2 # +1 for 0-index, +1 for skipping marker
            logging.info(f"Processing line {current_line_num}/{total_lines}: '{line[:100]}'...") # Log line number and content

            if not line:
                logging.debug(f"  Skipping empty line {current_line_num}")
                continue # Skip empty lines

            # Check for header FIRST
            logging.debug(f"  [{current_line_num}] CHECKING HEADER MATCH for line: {repr(line)}") # Use repr()
            header_match = self.currency_header_pattern.match(line)
            if header_match:
                logging.info(f"  Line {current_line_num}: Cabeçalho de moeda encontrado.")
                header_found_for_current_wallet = True
                continue  # Move to the next line after finding the header
            else:
                logging.debug(f"  [{current_line_num}] HEADER MATCH FAILED for line: {repr(line)}") # Use repr()

            # If not header, check for potential title
            # Reset captured address here before checking for a new title or data

            # 2. Check for Wallet Address (separate line)
            address_match = address_pattern.match(line)
            if address_match:
                # Guarda o endereço capturado para ser usado no próximo título ou dados
                last_captured_address = address_match.group(1).strip()
                # Update address for the current context if it's new or not set
                # Avoid overwriting if address was already found on title line
                if not current_wallet_info.get('address'):
                     current_wallet_info['address'] = last_captured_address
                     logging.debug(f"  Line {current_line_num}: >>> Endereço CAPTURADO (linha separada): {last_captured_address}. Associado temporariamente.")
                else:
                     # Se já existe endereço, loga mas não sobrescreve AINDA.
                     # A associação final ocorre ao detectar um NOVO título.
                     logging.debug(f"  Line {current_line_num}: >>> Endereço CAPTURADO (linha separada): {last_captured_address}, MAS carteira '{current_wallet_info.get('name', '')}' já tem '{current_wallet_info.get('address')}'. Guardado para próximo título.")
                continue # Address line processed

            # 3. Check for Total Value Line (Resets header flag)
            if total_value_pattern.match(line):
                logging.debug(f"  Line {current_line_num}: Linha 'Total wallet value' encontrada, resetando header flag.")
                header_found_for_current_wallet = False # Ready for next wallet's header
                continue

            # 4. Check for a *potential* new Title (excluding Header line explicitly)
            # Avoid matching the header itself as a title
            if self.currency_header_pattern.match(line):
                logging.debug(f"  Line {current_line_num}: Linha de cabeçalho já tratada, pulando checagem de título.")
                continue # Should have been caught by step 1, but safety check

            title_match = koinly_title_pattern.match(line)
            is_potential_title_by_regex = title_match is not None
            # Refined fallback: Exclude lines starting with numbers/R$, specific phrases, and ensure some alpha chars
            # *** AND explicitly exclude the header string itself ***
            is_potential_title_by_fallback = (
                line and line.lower() != 'currency amount price value' and # Explicit header check
                line[0].isalpha() and len(line) > 3 and \
                not currency_data_pattern.match(line) and \
                not line.startswith(("R$","Wallet address:","Total wallet value")) and \
                " per " not in line and \
                not re.match(r"^[\d.,\s-]+R\$[\d.,\s]+R\$[\d.,\s]+$", line) # Exclude number-heavy lines
            )

            # Process ONLY if it's a potential title (either by regex or fallback)
            if is_potential_title_by_regex or is_potential_title_by_fallback:
                wallet_name_part = line # Default to the line itself for fallback
                blockchain_part = "None"
                address_part = None
                is_bitcoin_wallet = False

                # If matched by regex, extract parts using the helper
                if is_potential_title_by_regex:
                    if title_match: # Safety check
                        wallet_name_part, blockchain_part, address_part, is_bitcoin_wallet = self._extract_title_parts_from_match(title_match, line, is_koinly_pattern=True)
                    else:
                         logging.warning(f"  Line {current_line_num}: Inconsistência: is_potential_title_by_regex é True mas title_match é None.")
                         # Apply basic fallback logic here if needed
                # If only matched by fallback, apply basic heuristics
                elif is_potential_title_by_fallback:
                     logging.debug(f"  Line {current_line_num}: Potencial título identificado por fallback: '{line}'")
                     if 'Bitcoin' in line and 'Mercado Bitcoin' not in line:
                         is_bitcoin_wallet = True
                         blockchain_part = "Bitcoin"
                     elif any(ex in line for ex in ['Binance', 'CoinEx', 'BingX', 'Mercado Bitcoin']):
                         blockchain_part = "Exchange"

                # Update context *only* if title genuinely changed
                if wallet_name_part != current_wallet_info.get('name', ''):
                    # Associate the *last captured* address with this *new* title
                    final_address = address_part if address_part else last_captured_address
                    logging.info(f"  Line {current_line_num}: ---> NOVO TÍTULO DETECTADO: '{wallet_name_part}'")
                    logging.debug(f"      \-> Nome Anterior: '{current_wallet_info.get('name')}', Blockchain: '{blockchain_part}', TipoBTC: {is_bitcoin_wallet}, AddrTítulo: {address_part}, AddrCapturado: {last_captured_address}")

                    current_wallet_info = {
                        "name": wallet_name_part,
                        "type": "Exchange" if blockchain_part == "Exchange" else ("Bitcoin" if is_bitcoin_wallet else "Wallet"),
                        "address": final_address,
                        "blockchain": blockchain_part
                    }
                    # Clear last captured address *after* associating it
                    if final_address == last_captured_address:
                        last_captured_address = None

                    logging.debug(f"      \-> Novo Contexto: {current_wallet_info}")
                    header_found_for_current_wallet = False # Reset header flag for the new wallet
                    logging.debug(f"      \-> Flag header_found_for_current_wallet resetada para FALSE (novo título)")
                else:
                     logging.debug(f"  Line {current_line_num}: Linha '{line}' identificada como título, mas nome ('{wallet_name_part}') é igual ao atual ('{current_wallet_info.get('name')}'). Ignorando mudança de contexto.")
                     # Associate address if captured just before a *repeated* title line
                     if last_captured_address and not current_wallet_info.get('address'):
                          current_wallet_info['address'] = last_captured_address
                          logging.debug(f"      >>> Endereço '{last_captured_address}' associado à carteira existente '{current_wallet_info['name']}' via linha de título repetida.")
                          last_captured_address = None

                continue # Title line processed, move to next line

            # 5. Check for Currency Data Line (Only if a header was found for this wallet)
            if header_found_for_current_wallet:
                currency_match = currency_data_pattern.match(line)
                if currency_match:
                    data = currency_match.groupdict()
                    try:
                        current_address_for_detail = current_wallet_info.get("address")
                        current_blockchain_for_detail = current_wallet_info.get("blockchain")
                        logging.debug(f"  Line {current_line_num}:     >>> Dados de MOEDA ENCONTRADOS. Usando: Wallet='{current_wallet_info['name']}', Address='{current_address_for_detail}', Blockchain='{current_blockchain_for_detail}'")

                        detail = {
                            'wallet_name_raw': current_wallet_info["name"], # Usa o nome atual
                            'wallet_type': current_wallet_info["type"], # Usa o tipo atual
                            'address': current_address_for_detail,
                            'blockchain': current_blockchain_for_detail,
                            'currency': data['currency'].strip(),
                            'amount': float(self._clean_numeric_str(data['amount'], remove_currency=False)),
                            'price': float(self._clean_numeric_str(data['price'])),
                            'value': float(self._clean_numeric_str(data['value']))
                        }
                        wallet_details.append(detail)
                    except Exception as e:
                        logging.warning(f"  Line {current_line_num}: Erro ao processar linha de moeda: '{line}'. Erro: {e}")
                else:
                    # Line is after header but not currency data - could be end of wallet, artifact, etc.
                    # Don't reset header flag here, might be multi-line non-currency info
                    logging.debug(f"  Line {current_line_num}: Linha não reconhecida como moeda (APÓS cabeçalho): '{line}' (Carteira: {current_wallet_info['name']})")
            else:
                 # Line is before a header was found for the current wallet
                 logging.debug(f"  Line {current_line_num}: Linha ignorada (ANTES do cabeçalho): '{line}' (Carteira: {current_wallet_info['name']})")

        logging.info(f"Finalizou loop de {total_lines} linhas.") # Added log

        logging.info(f"Detalhes de carteira processados (linha a linha): {len(wallet_details)} itens")
        # LOGGING ADICIONAL 1: Verificar saída do parser
        if wallet_details:
            logging.info("--- Primeiros 5 detalhes processados ---")
            for item in wallet_details[:5]:
                logging.info(item)
            logging.info("-------------------------------------")
        else:
            logging.warning("Nenhum detalhe de carteira foi processado.")
            
        # ADDED PRINT: Check association at the end of parsing
        # print("--- DEBUG: Wallet association after parsing (_parse_wallet_details_section) ---")
        # for i, d in enumerate(wallet_details):
        #      print(f"  Item {i}: Currency='{d.get('currency')}', WalletRaw='{d.get('wallet_name_raw')}'")
        #      if i >= 9: # Print first 10 for brevity
        #          print("  ...")
        #          break
        # print("--- END DEBUG ---\n")

        logging.info("--- _parse_wallet_details_section FIM ---")
        return pd.DataFrame(wallet_details)

    def _extract_text_from_pdf(self) -> str:
        """Extrai texto de todas as páginas do PDF usando pdfplumber."""
        full_text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                print(f"Extraindo texto de {len(pdf.pages)} páginas...")
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                print("Extração de texto concluída.")
                
                # DEBUG: Imprimir as últimas linhas do texto extraído
                print("--- DEBUG: Últimas 50 linhas do texto extraído ---")
                lines = full_text.strip().split('\n')
                for line in lines[-50:]:
                    print(line)
                print("--- FIM DEBUG ---")
                
        except Exception as e:
            print(f"Erro crítico ao extrair texto do PDF {self.pdf_path.name}: {e}")
            print(traceback.format_exc()) # Imprime stack trace para depuração
            raise # Re-levanta a exceção para parar a execução se a leitura falhar
        return full_text

    def calculate_proportional_cost(self, wallet_details: List[Dict], end_of_year_balances: Dict[str, Dict]) -> List[Dict]:
        print("--- calculate_proportional_cost INICIO ---")
        if not end_of_year_balances:
            print("Aviso: Dicionário EndOfYearBalances está vazio. Custos proporcionais serão 0.")
            # Adiciona coluna 'cost_brl' zerada se EOY estiver vazio
            for detail in wallet_details:
                detail['cost_brl'] = 0.0
            return wallet_details
            
        calculated_details = []
        processed_eoy_keys = set() # Para rastrear chaves EOY já usadas em matches exatos

        # Cria um mapa simplificado de chaves EOY para busca aproximada
        simplified_eoy_map = {key.split(' (')[0].strip().lower(): key for key in end_of_year_balances}
        
        print(f"Dados EOY disponíveis para cálculo: {list(end_of_year_balances.keys())}")

        for detail in wallet_details:
            currency = detail['currency']
            cost_brl = 0.0 # Default
            eoy_match_key = None
            
            # 1. Tentativa de match exato (case-insensitive)
            exact_match_found = False
            for eoy_key in end_of_year_balances:
                 # Compara ignorando case E verificando se a chave EOY começa com a moeda do detalhe
                 # Ex: currency='BTC', eoy_key='BTC (Bitcoin)' -> match
                 if eoy_key.lower() == currency.lower() or eoy_key.lower().startswith(currency.lower() + ' ('):
                      eoy_match_key = eoy_key
                      exact_match_found = True
                      break
            
            if exact_match_found:
                 processed_eoy_keys.add(eoy_match_key) # Marca como usado para matches exatos
                 print(f"Match EOY exato para '{currency}' -> '{eoy_match_key}'")
            else:
                # 2. Tentativa de match ignorando parênteses (ex: BTC vs BTC (Bitcoin))
                simple_currency_detail = currency.split(' (')[0].strip().lower()
                if simple_currency_detail in simplified_eoy_map:
                    potential_key = simplified_eoy_map[simple_currency_detail]
                    # Usa só se não foi usado em match exato e se o nome base bate
                    if potential_key not in processed_eoy_keys:
                        eoy_match_key = potential_key
                        print(f"Match EOY aproximado (base) para '{currency}' -> '{eoy_match_key}'")
            
            # 3. Tentativa de match usando a descrição do EOY (ex: '@ R$x per BTC')
            # É menos confiável, usar como último recurso se NADA foi encontrado
            if not eoy_match_key:
                for eoy_key, eoy_data in end_of_year_balances.items():
                     # Usa só se não foi usado em match exato/aproximado
                     if eoy_key not in processed_eoy_keys and simplified_eoy_map.get(eoy_key.split(' (')[0].strip().lower()) != eoy_key:
                          desc = eoy_data.get('description', '')
                          # Procura por "per MOEDA" no final da descrição
                          if desc and re.search(f"per {re.escape(currency)}$", desc, re.IGNORECASE):
                              eoy_match_key = eoy_key
                              print(f"Match EOY pela descrição para '{currency}' -> '{eoy_match_key}'")
                              break # Pega o primeiro que encontrar

            # Cálculo do custo se um match foi encontrado
            if eoy_match_key:
                eoy_data = end_of_year_balances[eoy_match_key]
                total_quantity = eoy_data.get('total_quantity', 0.0)
                total_cost = eoy_data.get('total_cost_brl', 0.0)
                
                # Evita divisão por zero e calcula custo proporcional
                if total_quantity is not None and total_cost is not None and total_quantity > 1e-9: # Usa tolerância pequena
                    proportion = detail['amount'] / total_quantity
                    calculated_cost = total_cost * proportion
                    # Custo não pode ser negativo (mesmo se custo total for negativo por alguma razão)
                    cost_brl = round(max(0, calculated_cost), 2) 
                    # print(f"  Calculado: Qtd={detail['amount']}, TotalQtd={total_quantity}, TotalCusto={total_cost}, Prop={proportion}, CustoCalc={cost_brl}")
                else:
                     print(f"  Aviso: Quantidade total EOY zerada ou inválida para '{eoy_match_key}'. Custo proporcional será 0.")
                     cost_brl = 0.0
            else:
                 # Só avisa se EOY não estiver vazio E a moeda tiver valor significativo no wallet details
                 if end_of_year_balances and detail.get('value', 0) > 0.01: 
                      print(f"Aviso: Moeda '{currency}' (Valor: R${detail.get('value', 0):.2f}) dos detalhes não encontrada no resumo EndOfYear Balances. Custo será 0.")
                 cost_brl = 0.0 # Garante que custo é 0 se não houve match
            
            # Garante que todas as chaves originais, incluindo wallet_name_raw, são mantidas
            # e apenas cost_brl é adicionado/atualizado.
            detail['cost_brl'] = cost_brl
            calculated_details.append(detail) # detail já contém wallet_name_raw da entrada

        print(f"--- calculate_proportional_cost FIM: {len(calculated_details)} itens ---")
        return calculated_details

    def generate_irpf_description(self, wallet_details: List[Dict]) -> List[Dict]:
        print("--- generate_irpf_description INICIO ---")
        logging.info("--- generate_irpf_description INICIO ---") # Log INFO level

        # Debug for BSC module
        print(f"BSC Module Available: {BSC_MODULE_AVAILABLE}")
        
        # Print some sample wallet details to see if there might be BSC wallets
        print("Sample wallet details before BSC processing:")
        for i, detail in enumerate(wallet_details[:5]):  # Sample first 5 details
            wallet_name = detail.get('wallet_name_raw', '')
            blockchain = detail.get('blockchain', '')
            print(f"  Detail {i}: Wallet={wallet_name}, Blockchain={blockchain}")
        
        # Apply BSC fixes if the module is available
        if BSC_MODULE_AVAILABLE:
            print(f"Applying BSC fixes to {len(wallet_details)} wallet details...")
            try:
                fixed_wallet_details = process_wallet_details_for_bsc(wallet_details)
                print(f"BSC fixes applied successfully, returning {len(fixed_wallet_details)} items")
                
                # Print some sample fixed wallet details
                print("Sample wallet details after BSC processing:")
                for i, detail in enumerate(fixed_wallet_details[:5]):  # Sample first 5 details
                    wallet_name = detail.get('wallet_name_raw', '')
                    blockchain = detail.get('blockchain', '')
                    print(f"  Detail {i}: Wallet={wallet_name}, Blockchain={blockchain}")
                
                wallet_details = fixed_wallet_details
            except Exception as e:
                print(f"Error applying BSC fixes: {e}")
                traceback.print_exc()
        else:
            print("Skipping BSC fixes (module not available)")
        
        described_details = []
        
        for i, detail in enumerate(wallet_details): # Add index for logging
            # DEBUG LOG: Log received data for each detail
            received_address = detail.get('address')
            received_blockchain = detail.get('blockchain')
            logging.debug(f"  Item {i}: Recebido Address='{received_address}', Blockchain='{received_blockchain}', RawWallet='{detail.get('wallet_name_raw')}'")
                
            try:
                amount_float = float(detail.get('amount', 0.0))
                # Formatação da quantidade (mantida)
                formatted_amount = "{:.8f}".format(amount_float) 
                formatted_amount = re.sub(r'(\.\d*[1-9])0+$', r'\1', formatted_amount)
                formatted_amount = re.sub(r'\.0+$', '', formatted_amount) 
                formatted_amount = formatted_amount.replace('.',',')

                custodian_name_raw = str(detail.get('wallet_name_raw', 'DESCONHECIDA')).strip()
                wallet_address = detail.get('address') 
                blockchain_from_parser = detail.get('blockchain') # Renomeado para clareza
                logging.debug(f"    Infos do Parser: Address='{wallet_address}', Blockchain='{blockchain_from_parser}'")
                
                # Make sure wallet_address is a string for processing
                if wallet_address is not None and not isinstance(wallet_address, str):
                    wallet_address = str(wallet_address)
                
                # Extract address from wallet name if not already available
                if not wallet_address or wallet_address == 'None':
                    # Look for common address patterns in wallet name
                    address_patterns = [
                        # Bitcoin extended public keys
                        r'(?:[xyz]pub)([a-zA-Z0-9]{4,})',
                        # Ethereum addresses: 0x followed by hex digits
                        r'(?:0x)([a-fA-F0-9]{4,})',
                        # Bitcoin SegWit addresses: bc1 followed by alphanumeric
                        r'(bc1[a-zA-Z0-9]{4,})',
                        # General shortened addresses: prefix...suffix format
                        r'([a-fA-F0-9]{4,})\.\.\.([a-fA-F0-9]{2,})',
                        # Bitcoin/other addresses: alphanumeric strings that look like addresses
                        r'(?<!\w)([13][a-km-zA-HJ-NP-Z1-9]{25,34})(?!\w)'
                    ]
                    
                    for pattern in address_patterns:
                        address_match = re.search(pattern, custodian_name_raw)
                        if address_match:
                            if '...' in pattern:
                                # For prefix...suffix pattern
                                prefix = address_match.group(1)
                                suffix = address_match.group(2)
                                wallet_address = f"{prefix}...{suffix}"
                            else:
                                # For other patterns, use the entire match
                                wallet_address = address_match.group(0)
                            logging.debug(f"    Extraído endereço do nome: '{wallet_address}'")
                            break
                
                # Special case for Bitcoin addresses - now handles all common Bitcoin address formats
                is_bitcoin_address = False
                bitcoin_address = None
                
                # Check blockchain first - if it's Bitcoin, mark as Bitcoin address
                if blockchain_from_parser and blockchain_from_parser.lower() == 'bitcoin':
                    is_bitcoin_address = True
                    # Use the wallet_address if available
                    if wallet_address and wallet_address != 'None':
                        bitcoin_address = wallet_address
                    logging.debug(f"    Detected Bitcoin from blockchain identifier: {blockchain_from_parser}")
                    
                # Check wallet address patterns if not already identified as Bitcoin
                if not is_bitcoin_address and wallet_address and isinstance(wallet_address, str) and wallet_address != 'None':
                    # Extended public keys
                    if any(prefix in wallet_address.lower() for prefix in ['xpub', 'ypub', 'zpub']):
                        is_bitcoin_address = True
                        bitcoin_address = wallet_address
                        logging.debug(f"    Detected Bitcoin from extended public key: {wallet_address}")
                    # SegWit addresses
                    elif wallet_address.startswith('bc1'):
                        is_bitcoin_address = True
                        bitcoin_address = wallet_address
                        logging.debug(f"    Detected Bitcoin from SegWit address: {wallet_address}")
                    # Legacy and P2SH addresses (simple check - Bitcoin addresses start with 1 or 3)
                    elif (wallet_address.startswith(('1', '3')) and 
                          len(wallet_address) >= 26 and len(wallet_address) <= 35 and
                          all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in wallet_address)):
                        is_bitcoin_address = True
                        bitcoin_address = wallet_address
                        logging.debug(f"    Detected Bitcoin from legacy/P2SH address: {wallet_address}")
                
                # Check custodian_name_raw for Bitcoin patterns if not already found
                if not is_bitcoin_address and custodian_name_raw:
                    if 'bitcoin' in custodian_name_raw.lower() and 'mercado bitcoin' not in custodian_name_raw.lower():
                        is_bitcoin_address = True
                        logging.debug(f"    Detected Bitcoin from name: {custodian_name_raw}")
                        
                        # Look for extended public keys in the name
                        xpub_match = re.search(r'([xyz]pub[a-zA-Z0-9]+)', custodian_name_raw, re.IGNORECASE)
                        if xpub_match:
                            bitcoin_address = xpub_match.group(1)
                            logging.debug(f"    Extracted extended public key from name: {bitcoin_address}")
                        # Look for SegWit addresses in the name
                        elif 'bc1' in custodian_name_raw:
                            bc1_match = re.search(r'(bc1[a-zA-Z0-9]+)', custodian_name_raw)
                            if bc1_match:
                                bitcoin_address = bc1_match.group(1)
                                logging.debug(f"    Extracted SegWit address from name: {bitcoin_address}")
                        # Look for legacy/P2SH addresses in the name
                        elif re.search(r'(?<![a-zA-Z0-9])[13][a-km-zA-HJ-NP-Z1-9]{25,34}(?![a-zA-Z0-9])', custodian_name_raw):
                            addr_match = re.search(r'(?<![a-zA-Z0-9])([13][a-km-zA-HJ-NP-Z1-9]{25,34})(?![a-zA-Z0-9])', custodian_name_raw)
                            if addr_match:
                                bitcoin_address = addr_match.group(1)
                                logging.debug(f"    Extracted legacy/P2SH address from name: {bitcoin_address}")
                
                # Format bitcoin address for display (first 7 chars + ...)
                if is_bitcoin_address:
                    formatted_bitcoin_address = ""
                    if bitcoin_address and len(bitcoin_address) > 7:
                        formatted_bitcoin_address = f"{bitcoin_address[:7]}..."
                    elif bitcoin_address:
                        formatted_bitcoin_address = bitcoin_address
                    
                    logging.debug(f"    HANDLER ESPECIAL: Detectado endereço Bitcoin: {bitcoin_address}, formatado como: {formatted_bitcoin_address}")
                    custodian_type = "NA REDE"
                    custodian_name_final_for_desc = "BITCOIN"
                    
                    # Extract wallet name from custodian_name_raw
                    wallet_name = detail.get('wallet_name_raw', '').strip()
                    
                    # Clean wallet name by removing address parts and network info
                    clean_patterns = [
                        # Remove Bitcoin reference if at the end
                        (r'\s*-\s*Bitcoin\s*$', ''),
                        # Remove extended public keys
                        (r'\s*-?\s*(?:[xyz]pub)[a-zA-Z0-9]+.*$', ''),
                        # Remove bc1 addresses
                        (r'\s*-?\s*bc1[a-zA-Z0-9]+.*$', ''),
                        # Remove legacy/P2SH addresses
                        (r'\s*-?\s*[13][a-km-zA-HJ-NP-Z1-9]{25,34}.*$', ''),
                        # Remove trailing hyphen if present
                        (r'\s*-\s*$', '')
                    ]
                    
                    for pattern, replacement in clean_patterns:
                        wallet_name = re.sub(pattern, replacement, wallet_name, flags=re.IGNORECASE).strip()
                    
                    if not wallet_name or wallet_name.lower() == 'bitcoin':
                        wallet_name = "CARTEIRA BITCOIN"
                    
                    # Format the complete description
                    formatted_custodian_info = f"NA CARTEIRA {wallet_name.upper()} {custodian_type} {custodian_name_final_for_desc}"
                    address_part = f" {formatted_bitcoin_address}" if formatted_bitcoin_address else ""
                    
                    # Get currency
                    currency_name = detail.get('currency', '?').split(' ')[0].split('(')[0]
                    
                    # Build final description
                    detail['irpf_description'] = (
                        f"SALDO DE {formatted_amount} {currency_name} "
                        f"CUSTODIADO {formatted_custodian_info}{address_part} EM 31/12/{self.year}."
                    )
                    described_details.append(detail)
                    continue
                
                # Limpeza inicial leve para verificação de marca/exchange
                custodian_name_lower = custodian_name_raw.lower()
                
                # Limpeza mais agressiva para o nome final na descrição - REFINADA
                # 1. Remover prefixos comuns
                custodian_name_cleaned = re.sub(r'^(WALLET ADDRESS:|EXCHANGE:|METAMASK(?: \d+)? - |LEDGER - |TREZOR - |PHANTOM(?: \(PRINCIPAL\))? - |KEPLR WALLET - |TRUST WALLET - |Rabby -)\s*', '', custodian_name_raw, flags=re.IGNORECASE) 
                # 2. Remover sufixos de endereço comuns (APÓS hífen ou no final absoluto)
                custodian_name_cleaned = re.sub(r'\s*-\s*([0-9a-zA-Z]{4}\.\.\.[0-9a-zA-Z]{2})$', '', custodian_name_cleaned).strip()
                custodian_name_cleaned = re.sub(r'\s*-\s*([a-fA-F0-9xX]{10,})$', '', custodian_name_cleaned).strip() # Hex mais longo
                custodian_name_cleaned = re.sub(r'\s*-\s*((?:xpub|zpub)[a-zA-Z0-9]+)$', '', custodian_name_cleaned).strip() # Endereços xpub/zpub
                custodian_name_cleaned = re.sub(r'\s*-\s*(bc1[a-zA-Z0-9]+)$', '', custodian_name_cleaned).strip() # Endereços bc1
                custodian_name_cleaned = re.sub(r'\s*-\s*([13][a-km-zA-HJ-NP-Z1-9]{25,34})$', '', custodian_name_cleaned).strip() # Endereços legacy/P2SH
                # 3. Remover parênteses com ticker ou rede no final (se houver algo antes)
                custodian_name_cleaned = re.sub(r'(?<=\w)\s*\(.*?\)$', '', custodian_name_cleaned).strip()
                # 4. Remover hífens restantes no final
                custodian_name_cleaned = custodian_name_cleaned.rstrip(' -').strip()
                
                if not custodian_name_cleaned: custodian_name_cleaned = custodian_name_raw.upper() if custodian_name_raw else "DESCONHECIDA"
                
                # --- Lógica de Identificação Refinada ---
                custodian_type = "NA REDE" # Default
                entity_name = None       
                final_cleaned_name = custodian_name_cleaned.upper() 
                network_part = ""         
                address_part = ""         
                
                # Extract blockchain from wallet name if not already available
                if blockchain_from_parser == "None" or not blockchain_from_parser:
                    # Check if the wallet name contains a known blockchain
                    for blockchain in KNOWN_BLOCKCHAINS:
                        # Case insensitive search in the raw wallet name
                        if blockchain.lower() in custodian_name_raw.lower() and "mercado bitcoin" not in custodian_name_raw.lower():
                            blockchain_from_parser = blockchain.capitalize()
                            logging.debug(f"    Detected blockchain from wallet name: {blockchain_from_parser}")
                            break
                    
                    # Also check for network part in the format "Wallet - Network"
                    if not blockchain_from_parser or blockchain_from_parser == "None":
                        parts = custodian_name_raw.split(' - ')
                        if len(parts) > 1:
                            network_part = parts[1].strip()
                            # Remove parentheses content for cleaner match
                            network_clean = re.sub(r'\s*\([^)]*\)', '', network_part).strip()
                            for blockchain in KNOWN_BLOCKCHAINS:
                                if blockchain.lower() in network_clean.lower():
                                    blockchain_from_parser = network_clean
                                    logging.debug(f"    Detected blockchain from network part: {blockchain_from_parser}")
                                    break

                # 1. Verifica Exchanges
                is_exchange = False
                
                # Check for BSC in the name or in the blockchain
                is_bsc = False
                bsc_keywords = ['binance smart chain', 'bsc', 'bnb chain']
                
                if blockchain_from_parser and blockchain_from_parser.lower() in ['bsc', 'binance smart chain']:
                    is_bsc = True
                    logging.debug(f"    BSC detected from blockchain type: {blockchain_from_parser}")
                
                if not is_bsc:
                    for bsc_term in bsc_keywords:
                        if bsc_term.lower() in custodian_name_raw.lower():
                            is_bsc = True
                            blockchain_from_parser = "BSC"
                            logging.debug(f"    BSC detected from name: {custodian_name_raw}")
                            break
                
                # Only check for exchanges if not already identified as BSC
                if not is_bsc:
                    for ex in KNOWN_EXCHANGES:
                        if ex.lower() in custodian_name_lower:
                            # Skip Binance if it might be BSC
                            if ex.lower() == 'binance' and ('smart chain' in custodian_name_lower or 'bsc' in custodian_name_lower):
                                continue
                            
                            custodian_type = "NA EXCHANGE"
                            entity_name = ex.upper()
                            is_exchange = True
                            break
                
                # 2. Se não for exchange, verifica Marcas de Carteira
                if not is_exchange:
                    is_brand = False
                    for brand in KNOWN_WALLET_BRANDS:
                        if brand.lower() in custodian_name_lower:
                            custodian_type = "NA CARTEIRA"
                            entity_name = brand.upper()
                            is_brand = True
                            
                            # Add network part if blockchain was detected
                            if blockchain_from_parser and blockchain_from_parser.upper() != "NONE" and blockchain_from_parser.upper() != entity_name:
                                if blockchain_from_parser.lower() not in ["none", "unknown"]:
                                    # Special formatting for BSC
                                    if is_bsc:
                                        network_part = " NA REDE BSC"
                                    else:
                                        network_part = f" NA REDE {blockchain_from_parser.upper()}"
                            break
                    
                    # 3. Se não for exchange/marca, define custódia como Rede
                    if not is_brand:
                        custodian_type = "NA REDE"
                        # Special handling for BSC
                        if is_bsc:
                            entity_name = "BSC"
                        # Prioritize blockchain from parser
                        elif blockchain_from_parser and blockchain_from_parser.upper() != "NONE":
                            entity_name = blockchain_from_parser.upper()
                        else:
                            # Try to detect blockchain from cleaned name parts
                            name_parts = re.split(r'\s+-\s+|\s+', custodian_name_cleaned.lower())
                            for part in name_parts:
                                if part.lower() in [blockchain.lower() for blockchain in KNOWN_BLOCKCHAINS]:
                                    entity_name = part.upper()
                                    break

                # Define o nome principal da descrição
                # Se entity_name foi definido (exchange, marca, ou blockchain do parser/nome), usa ele.
                # Senão, usa o nome limpo.
                custodian_name_final_for_desc = entity_name if entity_name else final_cleaned_name

                # Format wallet address for output (if not exchange)
                if not is_exchange:
                    if wallet_address and isinstance(wallet_address, str) and wallet_address != "None":
                        # Format address to show first 7 chars + ...
                        if len(wallet_address) > 7:
                            # Handle addresses with ... already in them
                            if '...' in wallet_address:
                                # Try to extract the prefix before ...
                                parts = wallet_address.split('...')
                                if parts[0] and len(parts[0]) <= 7:
                                    address_part = f" {wallet_address}"
                                else:
                                    # If prefix too long, truncate it
                                    address_part = f" {parts[0][:7]}..."
                            else:
                                # Just take first 7 characters and add ...
                                address_part = f" {wallet_address[:7]}..."
                        else:
                            # Short addresses just use as-is
                            address_part = f" {wallet_address}"
                    
                    # If still no address, check if there's an address pattern in the wallet name
                    if not address_part:
                        # Various address patterns to check
                        address_patterns = [
                            # 0x... Ethereum style addresses
                            (r'0x([a-fA-F0-9]{4,})(?:\.\.\.)?([a-fA-F0-9]{0,4})?', 
                             lambda m: f" 0x{m.group(1)[:6]}..." if m.group(1) else ""),
                            # bc1... Bitcoin SegWit addresses
                            (r'bc1([a-zA-Z0-9]{4,})(?:\.\.\.)?([a-zA-Z0-9]{0,4})?',
                             lambda m: f" bc1{m.group(1)[:5]}..." if m.group(1) else ""),
                            # Extended public keys
                            (r'([xyz]pub[a-zA-Z0-9]{4,})(?:\.\.\.)?([a-zA-Z0-9]{0,4})?',
                             lambda m: f" {m.group(1)[:7]}..." if m.group(1) else ""),
                            # General shortened addresses with ...
                            (r'([a-fA-F0-9]{4,})\.\.\.([a-fA-F0-9]{2,})',
                             lambda m: f" {m.group(1)[:7]}..." if len(m.group(1)) > 7 else f" {m.group(1)}...")
                        ]
                        
                        for pattern, formatter in address_patterns:
                            address_match = re.search(pattern, custodian_name_raw)
                            if address_match:
                                address_part = formatter(address_match)
                                logging.debug(f"    Extracted address from wallet name: {address_part}")
                                break

                # DEBUG LOG: Log parts before final assembly
                logging.debug(f"    Item {i}: Parts-> Type='{custodian_type}', Name='{custodian_name_final_for_desc}', Network='{network_part}', Address='{address_part}'")

                # --- Montagem Final da Descrição ---
                formatted_custodian_info = f"{custodian_type} {custodian_name_final_for_desc}{network_part}{address_part}"
                
                # Pega só a sigla principal (antes do primeiro espaço ou parêntese)
                currency_name = detail.get('currency', '?').split(' ')[0].split('(')[0]

                detail['irpf_description'] = (
                    f"SALDO DE {formatted_amount} {currency_name} "
                    f"CUSTODIADO {formatted_custodian_info} EM 31/12/{self.year}."
                )
            except Exception as e:
                print(f"Erro ao gerar descrição IRPF para: {detail}, Erro: {e}")
                traceback.print_exc()
                detail['irpf_description'] = f"ERRO NA GERAÇÃO DA DESCRIÇÃO ({e})"
            described_details.append(detail)
        print(f"--- generate_irpf_description FIM: {len(described_details)} itens ---")
        logging.info(f"--- generate_irpf_description FIM: {len(described_details)} itens ---") # Log INFO level
        return described_details

    def process_report(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        print(f"--- process_report INICIO para: {self.pdf_path.name} ---")
        full_text = ""
        eoy_balances = {}
        wallet_details = []

        try:
            # Tenta extrair com layout=True pode ajudar em tabelas complexas
            with pdfplumber.open(self.pdf_path) as pdf:
                print(f"Extraindo texto de {len(pdf.pages)} páginas...")
                all_texts = []
                for i, page in enumerate(pdf.pages):
                    # Revertendo para extração sem layout=True
                    page_text = page.extract_text(x_tolerance=2, y_tolerance=2) 
                    # if not page_text: # Fallback sem layout se falhar
                    #      page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if page_text:
                        all_texts.append(page_text)
                full_text = "\n".join(all_texts) # Junta páginas com newline
                print("Extração de texto concluída.")

                # DEBUG: Verifica se os marcadores existem no texto extraído
                print(f"--- DEBUG: Verificando marcadores em full_text ---")
                eoy_found_debug = "End of Year Balances" in full_text
                wallet_found_debug = "Balances per Wallet" in full_text
                print(f"  'End of Year Balances' encontrado: {eoy_found_debug}")
                print(f"  'Balances per Wallet' encontrado: {wallet_found_debug}")
                # Verifica case-insensitive também
                eoy_found_debug_ci = re.search(r"End of Year Balances", full_text, re.IGNORECASE) is not None
                wallet_found_debug_ci = re.search(r"Balances per Wallet", full_text, re.IGNORECASE) is not None
                print(f"  'End of Year Balances' (CI) encontrado: {eoy_found_debug_ci}")
                print(f"  'Balances per Wallet' (CI) encontrado: {wallet_found_debug_ci}")
                print(f"--- FIM DEBUG MARCADORES ---")

        except Exception as e:
            print(f"Erro crítico ao extrair texto do PDF {self.pdf_path.name}: {e}")

        if not full_text:
            print(f"Aviso: Nenhum texto extraído do PDF {self.pdf_path.name}. Pulando processamento.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Parse sections
        try:
            eoy_balances = self._parse_eoy_section(full_text)
        except Exception as e:
            print(f"Erro ao parsear EOY section: {e}")
            print(traceback.format_exc())

        try:
            # Divide o texto completo em linhas ANTES de passar para a função
            text_lines = full_text.split('\n')
            wallet_details_df = self._parse_wallet_details_section(text_lines)
        except Exception as e:
            print(f"Erro ao parsear Wallet Details section: {e}")
            print(traceback.format_exc())
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        if wallet_details_df.empty:
            print(f"Aviso: Nenhum detalhe de carteira encontrado em {self.pdf_path.name}.")
            # Mesmo sem detalhes, EOY pode ter dados, então retorna EOY e DFs vazios
            df_eoy = pd.DataFrame.from_dict(eoy_balances, orient='index')
            return df_eoy, pd.DataFrame(), pd.DataFrame()

        # Calculate proportional cost and generate description
        try:
            # Converte DataFrame para lista de dicionários para processamento
            wallet_details = wallet_details_df.to_dict('records')
            # Passa cópia para evitar modificar a lista original durante iteração (embora não deva ocorrer aqui)
            wallet_details_costed = self.calculate_proportional_cost(list(wallet_details), eoy_balances)
        except Exception as e:
            print(f"Erro ao calcular custo proporcional: {e}")
            print(traceback.format_exc())
            wallet_details_costed = wallet_details # Continua com custos zerados se falhar

        try:
            wallet_details_final = self.generate_irpf_description(wallet_details_costed)
        except Exception as e:
            print(f"Erro ao gerar descrição IRPF: {e}")
            print(traceback.format_exc())
            wallet_details_final = wallet_details_costed # Continua com descrições padrão/erro

        print("--- Convertendo para DataFrames ---")
        # Cria DataFrames
        df_eoy = pd.DataFrame.from_dict(eoy_balances, orient='index')
        # Renomeia colunas do EOY para clareza se não estiver vazio
        if not df_eoy.empty:
             df_eoy = df_eoy.reset_index().rename(columns={'index': 'asset'})
        print(f"DataFrame EOY criado com shape: {df_eoy.shape}")

        df_wallet_details = pd.DataFrame(wallet_details_final) # Usa a lista final com custos e descrições
        print(f"DataFrame Wallet Details criado com shape: {df_wallet_details.shape}")

        # Cria DataFrame Final para IRPF
        df_final = pd.DataFrame()
        if not df_wallet_details.empty:
             # Verifica se as colunas esperadas existem antes de acessá-las
             required_cols = ['currency', 'amount', 'cost_brl', 'irpf_description']
             if all(col in df_wallet_details.columns for col in required_cols):
                  df_final['Ticker'] = df_wallet_details['currency']
                  df_final['Qtd'] = df_wallet_details['amount']
                  # Formata valor do CUSTO para string com 2 casas decimais usando locale
                  df_final[f'Valor R$ 31/12/{self.year}'] = df_wallet_details['cost_brl'].apply(
                      lambda x: locale.format_string("%.2f", x, grouping=False) if pd.notna(x) else '0.00'
                  )
                  df_final['Discriminação'] = df_wallet_details['irpf_description']
                  df_final['Cnpj'] = '' # Adiciona coluna CNPJ vazia
             else:
                  missing = [col for col in required_cols if col not in df_wallet_details.columns]
                  print(f"Aviso: Colunas faltando em df_wallet_details para criar df_final: {missing}")
                  # Cria df_final vazio ou com colunas disponíveis
                  df_final['Ticker'] = df_wallet_details.get('currency', pd.Series(dtype='str')) 
                  df_final['Qtd'] = df_wallet_details.get('amount', pd.Series(dtype='float'))
                  df_final[f'Valor R$ 31/12/{self.year}'] = 'ERRO'
                  df_final['Discriminação'] = df_wallet_details.get('irpf_description', pd.Series(dtype='str'))
                  df_final['Cnpj'] = ''

        print(f"DataFrame Final criado com shape: {df_final.shape}")

        print(f"--- process_report FIM para: {self.pdf_path.name} ---")
        return df_eoy, df_wallet_details, df_final

    def save_to_csv(self, output_path_base: Path):
        print(f"--- save_to_csv INICIO para: {output_path_base.stem} ---")
        
        # Lista de arquivos temporários para deletar no final
        temp_files = []
        
        try:
            eoy_df, wallet_details_df, final_df = self.process_report()

            # Define o separador como ponto e vírgula e quoting para não numéricos
            save_config = {
                "index": False, 
                "encoding": 'utf-8-sig', 
                "sep": ";", 
                "quoting": csv.QUOTE_NONNUMERIC # Adiciona aspas em campos não numéricos
            } 
            
            if not eoy_df.empty:
                file_path = output_path_base.with_name(f"{output_path_base.stem}_end_of_year.csv")
                print(f"Salvando EOY temporário ({eoy_df.shape}) em: {file_path}")
                eoy_df.to_csv(file_path, **save_config)
                temp_files.append(file_path)
            else:
                print("DataFrame EOY vazio, não será salvo.")

            if not wallet_details_df.empty:
                file_path = output_path_base.with_name(f"{output_path_base.stem}_wallet_details.csv")
                print(f"Salvando Wallet Details temporário ({wallet_details_df.shape}) em: {file_path}")
                wallet_details_df.to_csv(file_path, **save_config)
                temp_files.append(file_path)
            else:
                print("DataFrame Wallet Details vazio, não será salvo.")

            if not final_df.empty:
                # Certifica que a coluna de valor (que contém vírgula) está como string
                valor_col_name = f'Valor R$ 31/12/{self.year}'
                if valor_col_name in final_df.columns:
                    final_df[valor_col_name] = final_df[valor_col_name].astype(str)
                
                # Salva apenas o arquivo com sufixo _final.csv
                file_path = output_path_base.with_name(f"{output_path_base.stem}_final.csv")
                print(f"Salvando arquivo final ({final_df.shape}) em: {file_path}")
                final_df.to_csv(file_path, **save_config)
            else:
                print("DataFrame Final vazio, não será salvo.")
                
            # Remove arquivos temporários
            for temp_file in temp_files:
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                        print(f"Arquivo temporário removido: {temp_file}")
                    except Exception as e:
                        print(f"Não foi possível remover arquivo temporário {temp_file}: {e}")
                        
        except Exception as e:
            print(f"Erro GERAL durante o processamento/salvamento de {self.pdf_path.name}: {e}")
            traceback.print_exc()
            
        print(f"--- save_to_csv FIM para: {output_path_base.stem} ---") 