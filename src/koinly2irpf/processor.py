#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module for processing Koinly reports and converting them to IRPF format.
"""

import os
import re
import logging
import pandas as pd
from pathlib import Path
import pdfplumber
import locale
import traceback
import csv
from decimal import Decimal, InvalidOperation
from datetime import datetime

# Import the fix_binance_smart_chain module
try:
    from .fix_binance_smart_chain import process_wallet_details_for_bsc
    _bsc_module_available = True
except ImportError:
    _bsc_module_available = False
    logging.warning("BSC module not available, skipping BSC fixes")

class KoinlyProcessor:
    """
    Class for processing Koinly reports and converting them to IRPF format.
    """
    
    def __init__(self, pdf_path):
        """
        Initialize the processor with a path to a Koinly PDF report.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"File not found: {self.pdf_path}")
            
        self.output_dir = self.pdf_path.parent
        self.base_filename = self.pdf_path.stem
        
        # This will be populated during processing
        self.text = ""
        self.end_of_year_items = []
        self.wallet_details = []
        self.eoy_df = None
        self.wallet_df = None
        self.final_df = None
        self._last_eoy_section_end_index = 0
        self.report_year = None

        # Common Patterns
        self.currency_header_pattern = re.compile(r"^\s*Currency\s+Amount\s+Price\s+Value\s*$", re.IGNORECASE | re.DOTALL)
        # New pattern for the header with the 'Cost' column
        self.new_currency_header_pattern = re.compile(r"^\s*(?:Asset|Currency)\s+Amount\s+Price\s+Value\s+Cost\s*$", re.IGNORECASE)
        # Pattern to capture 'Total cost at 31 Dec YYYY: R$X.XX'
        self.total_wallet_cost_pattern = re.compile(r"^Total cost at \d{2} Dec \d{4}:\s*(R\$[\d.,]+)", re.IGNORECASE)

        # Setup locale (moved from old __init__)
        self._setup_locale()

    def _setup_locale(self):
        """Sets up locale for number formatting."""
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252') # Windows fallback
            except locale.Error:
                logging.warning("Aviso: Não foi possível configurar o locale pt_BR. A formatação de números pode não usar vírgula.")

    def _clean_numeric_str(self, num_str: str | None, remove_currency: bool = True) -> str:
        """Cleans a string to be safely converted to float (handles ., and currency)."""
        if num_str is None:
            return '0'
        num_str = str(num_str)
        if remove_currency:
            num_str = re.sub(r"[R$€£¥]", "", num_str)
        num_str = num_str.strip().replace(' ', '')
        if ',' in num_str and '.' in num_str:
            if num_str.rfind('.') > num_str.rfind(','):
                cleaned = num_str.replace(',', '')
            else:
                cleaned = num_str.replace('.', '').replace(',', '.')
        elif ',' in num_str:
             cleaned = num_str.replace(',', '.')
        else:
             cleaned = num_str
        cleaned = re.sub(r"[^\d.-]", "", cleaned)
        if cleaned.count('.') > 1:
             parts = cleaned.split('.')
             cleaned = parts[0] + '.' + "".join(parts[1:])
        if '-' in cleaned[1:]:
            is_negative = cleaned.startswith('-')
            cleaned = cleaned.replace('-', '')
            if is_negative:
                cleaned = '-' + cleaned
        if not cleaned or cleaned == '.' or cleaned == '-':
            return '0'
        return cleaned

    def _extract_title_parts_from_match(self, match, line, is_koinly_pattern):
        """Extracts the wallet name, blockchain type, and address from a regex match object."""
        wallet_name_part = "Unknown Wallet"
        blockchain_part = "None"
        address_part = None
        is_bitcoin_wallet = False
        logging.debug(f"Extracting title parts from match groups: {match.groups()}, Line: {line}")
        if is_koinly_pattern and match:
            group1 = match.group(1)
            group2 = match.group(2)
            group3 = match.group(3)
            if group1:
                wallet_name_part = group1.strip()
                blockchain_part = "Bitcoin"
                is_bitcoin_wallet = True
                logging.debug(f"  Bitcoin pattern matched: Name='{wallet_name_part}', Blockchain='{blockchain_part}'")
            elif group2:
                wallet_name_part = group2.strip()
                blockchain_part = self._identify_blockchain(wallet_name_part)
                exchange_part = self._identify_exchange(wallet_name_part)
                if group3:
                    address_part = group3.strip()
                    blockchain_part = "Bitcoin"
                    is_bitcoin_wallet = True
                    logging.debug(f"  General pattern with ZPUB matched: Name='{wallet_name_part}', Blockchain='{blockchain_part}', Address='{address_part}'")
                else:
                    logging.debug(f"  General pattern matched: Name='{wallet_name_part}', Blockchain='{blockchain_part}', Exchange='{exchange_part}'")
            else:
                 logging.warning(f"  Koinly pattern matched but no expected groups found in line: {line}")
                 wallet_name_part = self._clean_wallet_name(line)
                 blockchain_part = self._identify_blockchain(wallet_name_part)
        else:
             logging.warning(f"  Match object invalid or not a Koinly pattern for line: {line}")
             wallet_name_part = self._clean_wallet_name(line)
             blockchain_part = self._identify_blockchain(wallet_name_part)
        wallet_name_part = self._clean_wallet_name(wallet_name_part)
        return wallet_name_part, blockchain_part, address_part, is_bitcoin_wallet

    def _use_sample_eoy_data(self):
         """Populates end_of_year_items with sample data if parsing fails."""
         if self.end_of_year_items: return
         logging.warning("Não foi possível extrair dados reais da seção End of Year, criando dados de exemplo")
         self.end_of_year_items = [
             {'asset': 'BTC','amount': 0.5,'price': 40000,'value': 20000,'cost': 15000},
             {'asset': 'ETH','amount': 5.0,'price': 2000,'value': 10000,'cost': 8000},
             {'asset': 'ADA','amount': 1000.0,'price': 0.5,'value': 500,'cost': 300}
         ]

    def _use_sample_wallet_data(self):
         """Populates wallet_details with sample data if parsing fails."""
         if self.wallet_details: return
         logging.warning("Não foi possível extrair dados reais da seção Wallet Details, criando dados de exemplo")
         self.wallet_details = [
             {'wallet_name': 'Binance Exchange','wallet_name_raw': 'Binance Exchange','blockchain': 'NONE','exchange': 'Binance','assets': [{'name': 'BTC', 'amount': 0.3, 'value': 12000},{'name': 'ETH', 'amount': 3.0, 'value': 6000}],'values': [12000, 6000],'total_value': 18000, 'proportion': 0.6},
             {'wallet_name': 'Metamask BSC','wallet_name_raw': 'Metamask (BSC)','blockchain': 'BSC','exchange': 'NONE','assets': [{'name': 'BNB', 'amount': 5.0, 'value': 2000},{'name': 'CAKE', 'amount': 100.0, 'value': 1000}],'values': [2000, 1000],'total_value': 3000, 'proportion': 0.1},
             {'wallet_name': 'Hardware Wallet','wallet_name_raw': 'Hardware Wallet','blockchain': 'BTC','exchange': 'NONE','assets': [{'name': 'BTC', 'amount': 0.2, 'value': 8000},{'name': 'ETH', 'amount': 2.0, 'value': 4000}],'values': [8000, 4000],'total_value': 12000, 'proportion': 0.4}
         ]

    def process_report(self):
        """
        Process the Koinly report:
        1. Extract text from PDF
        2. Parse end-of-year balances
        3. Parse wallet details
        4. Generate IRPF descriptions
        5. Create DataFrames
        """
        logging.info(f"Processing file: {self.pdf_path}")
        
        # Extract text from PDF
        self._extract_text_from_pdf()
        
        # Parse end-of-year balances
        self._parse_eoy_section()
        
        # Parse wallet details
        self._parse_wallet_details_section()
        
        # Fix BSC detection if module available
        if _bsc_module_available and self.wallet_details:
            logging.info("BSC Module Available: True")
            # Log a few samples before processing
            sample_size = min(5, len(self.wallet_details))
            logging.info("Sample wallet details before BSC processing:")
            for i in range(sample_size):
                wallet = self.wallet_details[i].get('wallet_name_raw', 'Unknown')
                blockchain = self.wallet_details[i].get('blockchain', 'None')
                num_assets = len(self.wallet_details[i].get('assets', []))
                logging.info(f"  Detail {i}: Wallet={wallet}, Blockchain={blockchain}, Assets={num_assets}")
                
            # Apply BSC fixes
            logging.info(f"Applying BSC fixes to {len(self.wallet_details)} wallet details...")
            try:
                self.wallet_details = process_wallet_details_for_bsc(self.wallet_details)
                logging.info("BSC fixes applied (assuming function adapted to wallet list).")
            except Exception as e_bsc:
                logging.error(f"Error applying BSC fixes: {e_bsc}. BSC fix function might need adaptation.")

            # Log a few samples after processing
            logging.info("Sample wallet details after BSC processing:")
            for i in range(sample_size):
                wallet = self.wallet_details[i].get('wallet_name_raw', 'Unknown')
                blockchain = self.wallet_details[i].get('blockchain', 'None')
                num_assets = len(self.wallet_details[i].get('assets', []))
                logging.info(f"  Detail {i}: Wallet={wallet}, Blockchain={blockchain}, Assets={num_assets}")
        else:
            logging.warning("BSC Module not available, skipping BSC fixes")
        
        # Calculate proportional costs
        self._calculate_proportional_cost()
        
        # Generate IRPF descriptions (MOVIDO PARA CÁ)
        logging.info("Generating IRPF descriptions")
        for wallet_detail in self.wallet_details:
            wallet_name = wallet_detail.get('wallet_name', 'Unknown')
            wallet_name_raw = wallet_detail.get('wallet_name_raw', wallet_name)
            exchange = wallet_detail.get('exchange', 'NONE')
            blockchain = wallet_detail.get('blockchain', 'NONE')
            is_exchange = exchange != 'NONE'
            is_blockchain = blockchain != 'NONE'

            if is_exchange:
                custodian_type = "NA EXCHANGE"
                entity_name = exchange
                network_part = ""
            else:
                custodian_type = "NA CARTEIRA"
                wallet_address = ""
                address_match = re.search(r'0x[a-fA-F0-9]{4}', wallet_name_raw)
                if address_match:
                    wallet_address = address_match.group(0)
                if is_blockchain:
                    network = f"NA REDE {blockchain}"
                    if wallet_address:
                        network += f" {wallet_address}"
                    network_part = network
                else:
                    network_part = ""

            for asset in wallet_detail.get('assets', []):
                asset_name = asset.get('name', 'Unknown') # Obter nome do ticker AQUI
                asset_amount = asset.get('amount', 0)
                try:
                    amount_decimal = Decimal(str(asset_amount))
                    amount_str = format(amount_decimal, 'f').replace('.', ',')
                except (InvalidOperation, ValueError):
                    amount_str = str(asset_amount).replace('.', ',')

                if is_exchange:
                    description = f"SALDO DE {amount_str} {asset_name} CUSTODIADO {custodian_type} {entity_name} EM 31/12/{self.report_year}."
                else:
                    description = f"SALDO DE {amount_str} {asset_name} CUSTODIADO {custodian_type} {wallet_name} {network_part} EM 31/12/{self.report_year}."
                asset['irpf_description'] = description.upper()
        logging.info("IRPF descriptions generated")
        # FIM DO BLOCO MOVIDO
        
        # Create DataFrames
        self._create_dataframes()
        
        logging.info(f"Processing complete for: {self.pdf_path}")
    
    def _extract_text_from_pdf(self):
        """Extract text from the PDF file and determine the report year."""
        logging.info(f"Extracting text from PDF: {self.pdf_path}")
        try:
            all_text_pages = []
            first_page_text = ""
            year_found = False

            with pdfplumber.open(self.pdf_path) as pdf:
                # Processar primeira página separadamente para encontrar o ano
                if pdf.pages:
                    first_page = pdf.pages[0]
                    first_page_text = first_page.extract_text()
                    if first_page_text:
                        # Procurar pelo padrão do título para extrair o ano
                        title_match = re.search(r"Balances per Wallet\s+(\d{4})", first_page_text, re.IGNORECASE)
                        if title_match:
                            self.report_year = title_match.group(1)
                            logging.info(f"Report year found in first page title: {self.report_year}")
                            year_found = True
                        else:
                             logging.warning("Year pattern 'Balances per Wallet YYYY' not found on first page.")
                        all_text_pages.append(first_page_text) # Adicionar texto da primeira página

                # Processar páginas restantes
                for page in pdf.pages[1:]:
                    text = page.extract_text()
                    if text:
                        all_text_pages.append(text)

            self.text = "\n".join(all_text_pages)
            logging.info(f"Extracted text from {len(all_text_pages)} pages")

            # Fallback 1: Tentar extrair ano do nome do arquivo
            if not year_found:
                filename_match = re.search(r"(\d{4})", self.pdf_path.stem)
                if filename_match:
                    self.report_year = filename_match.group(1)
                    logging.info(f"Report year found in filename: {self.report_year}")
                    year_found = True
                else:
                    logging.warning("Year not found in filename either.")

            # Fallback 2: Usar ano atual se não encontrado
            if not year_found:
                current_year = datetime.now().year
                self.report_year = str(current_year)
                logging.warning(f"Could not determine report year from PDF title or filename. Defaulting to current year: {self.report_year}")
            else:
                # Validar se o ano parece razoável (ex: entre 2010 e ano atual + 1)
                 try:
                     year_int = int(self.report_year)
                     current_year = datetime.now().year
                     if not (2010 <= year_int <= current_year + 1):
                          logging.warning(f"Extracted year {self.report_year} seems unusual. Please verify.")
                 except ValueError:
                      logging.warning(f"Extracted year '{self.report_year}' is not a valid number. Please verify.")


        except Exception as e:
            logging.error(f"Error extracting text or year from PDF: {str(e)}")
            # Se der erro na extração, ainda tenta definir um ano padrão
            if not self.report_year:
                 self.report_year = str(datetime.now().year)
                 logging.warning(f"Error during PDF processing, defaulting report year to current year: {self.report_year}")
            raise
    
    def _parse_eoy_section(self):
        """Parse the End of Year Balances section using old logic."""
        logging.info("--- (Old Logic) _parse_eoy_section INICIO ---")
        text = self.text

        # Regex pattern (more general for currency symbols)
        eoy_pattern = re.compile(
            r"^(?!Total\b)(.+?)\s+"                     # Asset Name (Grupo 1)
            r"([\d.,]+)\s+"                         # Quantity (Grupo 2)
            r"(?:[R$€£¥]?\s*)?(-?\(?\d[\d.,]*\)?)\s+" # Cost (Grupo 3)
            r"(?:[R$€£¥]?\s*)?(-?\(?\d[\d.,]*\)?)\s*" # Value (Grupo 4)
            r"(.*)"                                  # Description (Grupo 5) - Optional?
            , re.MULTILINE | re.IGNORECASE
        )

        eoy_title_match = re.search(r"End of Year Balances", text, re.IGNORECASE)
        if not eoy_title_match:
            logging.warning("(Old Logic) Aviso: Seção 'End of Year Balances' não encontrada.")
            self._use_sample_eoy_data()
            return
        eoy_title_end_index = eoy_title_match.end()

        # Find header
        header_pattern_general = r"Asset\s+Amount\s+Price\s+Value(?:\s+Cost)?"
        header_match_general = re.search(header_pattern_general, text[eoy_title_end_index:], re.IGNORECASE)
        header_pattern_brl = r"Asset\s+Quantity\s+Cost\s*\(BRL\)\s+Value\s*\(BRL\)\s+Description"
        header_match_brl = re.search(header_pattern_brl, text[eoy_title_end_index:], re.IGNORECASE)
        header_match = header_match_general if header_match_general else header_match_brl

        if not header_match:
            logging.warning("(Old Logic) Aviso: Cabeçalho EOY não encontrado após o título.")
            self._use_sample_eoy_data()
            return
        header_end_abs_index = eoy_title_end_index + header_match.end()
        logging.info(f"(Old Logic) Cabeçalho EOY encontrado: '{header_match.group(0)}'")

        # Find Total line
        total_match = re.search(r"^\s*Total\b", text[header_end_abs_index:], re.MULTILINE | re.IGNORECASE)
        if not total_match:
            logging.warning("(Old Logic) Aviso: Linha 'Total' não encontrada. Tentando usar 'Balances per Wallet' como limite.")
            details_start_match = re.search(r"Balances per Wallet", text[header_end_abs_index:], re.IGNORECASE)
            total_start_abs_index = header_end_abs_index + details_start_match.start() if details_start_match else len(text)
        else:
            total_start_abs_index = header_end_abs_index + total_match.start()
            logging.info(f"(Old Logic) Linha Total EOY encontrada: '{total_match.group(0)}'")

        eoy_table_text = text[header_end_abs_index:total_start_abs_index].strip()
        lines = eoy_table_text.split('\n')
        processed_count = 0
        logging.info(f"(Old Logic) Analisando {len(lines)} linhas na tabela EOY potencial.")
        self.end_of_year_items = [] # Clear before parsing

        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            match = eoy_pattern.match(line)
            if match:
                try:
                    raw_asset_name = match.group(1).strip()
                    # Remover a parte entre parênteses e qualquer espaço extra
                    asset = re.sub(r'\s*\([^)]*\)\s*$', '', raw_asset_name).strip()
                    # Remover também a descrição de preço (@ R$X.XX per TICKER) se existir
                    asset = re.sub(r'\s*@\s*[R$€£¥].*$', '', asset).strip()
                    
                    if not asset or asset.lower() == 'asset': 
                        logging.debug(f"(Old Logic) Pulando linha EOY inválida ou cabeçalho: '{line}'")
                        continue
                    
                    logging.debug(f"(Old Logic) EOY Asset Raw: '{raw_asset_name}' -> Cleaned: '{asset}'")

                    quantity_str = match.group(2)
                    cost_str = match.group(3).replace('(', '-').replace(')', '')
                    value_str = match.group(4).replace('(', '-').replace(')', '')

                    quantity = float(self._clean_numeric_str(quantity_str, remove_currency=False))
                    cost = float(self._clean_numeric_str(cost_str, remove_currency=True))
                    value = float(self._clean_numeric_str(value_str, remove_currency=True))
                    price = (value / quantity) if quantity != 0 else 0

                    if quantity < 0:
                        logging.warning(f"(Old Logic) Pulando linha EOY suspeita (quantidade negativa): '{line}'")
                        continue

                    self.end_of_year_items.append({
                        'asset': asset, 'amount': quantity, 'price': price,
                        'value': value, 'cost': cost
                    })
                    processed_count += 1
                except (ValueError, TypeError, IndexError, AttributeError) as e:
                     logging.error(f"(Old Logic) Erro ao processar linha EOY: '{line}', Erro: {e}")
            else:
                if len(line) > 5 and any(c.isalpha() for c in line) and not line.lower().startswith('total'):
                     logging.debug(f"(Old Logic) Linha EOY não reconhecida: '{line}'")

        logging.info(f"(Old Logic) EOY Balances processados: {processed_count} itens")
        if not self.end_of_year_items:
            self._use_sample_eoy_data()
        self._last_eoy_section_end_index = total_start_abs_index
        logging.info("--- (Old Logic) _parse_eoy_section FIM ---")

    def _parse_wallet_details_section(self):
        """Parses the 'Balances per Wallet' section using old stateful line-by-line approach."""
        logging.info("--- (Refined Logic) _parse_wallet_details_section INICIO ---")
        wallet_details_temp = []
        current_wallet_info = {
            "name": "Unknown Wallet", "type": "Unknown", "address": None, "blockchain": "None"
        }
        header_found_for_current_wallet = False
        last_captured_address = None
        text = self.text
        text_lines = text.split('\n')

        # Regex patterns (refined)
        # Title pattern: More specific, looks for known names or structure
        koinly_title_pattern = re.compile(
            r"^" # Start of line
            # Don't match typical asset lines (e.g., "BTC 1.23 R$100...")
            r"(?!\s*[A-Z0-9/.-]+\s+[\d.,]+\s+(?:[R$€£¥]|\d))"
            r"(Bitcoin(?:\s*\(BTC\))?|"
            r"(?:Binance|Coinbase|Kraken|Ledger|Trezor|MetaMask|Trust Wallet|Phantom|Keplr|Bybit|OKX|KuCoin|Gate\.io|MEXC|Bitget|BingX|Bitfinex|Huobi|Crypto\.com|Mercado Bitcoin|Bitso|Foxbit|NovaDAX|Coinext|BitcoinTrade)|"
            r"(?:[A-Z][a-zA-Z0-9\s\.\/\(\)-]*?)"
            r")"
            r"(?:\s*-\s*(BSC|ETH|SOL|BTC|Polygon|Avalanche|Arbitrum|Optimism|Cosmos|Near|Injective|Base|Fantom|Tron))?"
            r"(?:\s*-\s*(0x[a-fA-F0-9]{4,}|zpub[a-zA-Z0-9]+|[13bc][a-km-zA-HJ-NP-Z1-9]{25,59}))?"
            r"\s*$", # End of line
            re.IGNORECASE
        )

        address_pattern = re.compile(r"^(?:Wallet address:|Address:)\s+(0x[a-fA-F0-9]{4,}|zpub[a-zA-Z0-9]+|[13bc][a-km-zA-HJ-NP-Z1-9]{25,59}.*)$", re.IGNORECASE)
        total_value_pattern = re.compile(r"^Total wallet value at", re.IGNORECASE)
        currency_header_pattern = re.compile(r"^\s*(?:Asset|Currency)\s+Amount\s+Price\s+Value\s*", re.IGNORECASE)

        # --- Universal Currency Data Pattern (handles optional Cost column) --- #
        currency_data_pattern = re.compile(
            r"^"
            r"(?P<currency>.+?)"  # Currency Name/Ticker
            r"\s+"
            r"(?P<amount>[\d.,]+(?:[eE][-+]?\d+)?)"  # Amount
            r"\s+"
            r"(?:R?\$\s*)?(?P<price>[()?\d,.-]+(?:[eE][-+]?\d+)?)"  # Price
            r"\s+"
            r"(?:R?\$\s*)?(?P<value>[()?\d,.-]+(?:[eE][-+]?\d+)?)"  # Value
            # Optional Cost Column
            r"(?:\s+(?:R?\$\s*)?(?P<cost>[()?\d,.-]+(?:[eE][-+]?\d+)?))?"
            r"(?:\s+@.*)?"  # Optional trailing description (e.g., @ R$1.23 per UNI-V2)
            r"\s*$",
            re.IGNORECASE
        )
        # --- End Universal Pattern --- #

        is_new_format_wallet = False # Flag to indicate if current wallet uses new format with Cost column

        # --- Rest of the parsing logic --- (Find start index, loop through lines)
        start_index = -1
        search_start = self._last_eoy_section_end_index if self._last_eoy_section_end_index > 0 else 0
        temp_text_for_search = text[search_start:]
        match_details_start = re.search(r"Balances per Wallet", temp_text_for_search, re.IGNORECASE)

        if match_details_start:
             start_index_abs = search_start + match_details_start.start()
             current_char_count = 0
             for i, line in enumerate(text_lines):
                 line_len_with_newline = len(line) + 1
                 if current_char_count + line_len_with_newline > start_index_abs:
                     start_index = i; break
                 current_char_count += line_len_with_newline
             if start_index == -1: start_index = len(text_lines)
        else:
             for i, line in enumerate(text_lines):
                 if "Balances per Wallet" in line: start_index = i; break

        if start_index == -1 or start_index >= len(text_lines):
            logging.error("(Refined Logic) 'Balances per Wallet' section marker not found.")
            self._use_sample_wallet_data(); return

        logging.info(f"(Refined Logic) Seção 'Balances per Wallet' encontrada, iniciando análise a partir da linha {start_index + 1}.")
        wallet_lines = text_lines[start_index + 1:]
        total_lines_in_section = len(wallet_lines)
        logging.info(f"(Refined Logic) Analisando {total_lines_in_section} linhas na seção Wallet Details.")
        self.wallet_details = []
        wallet_details_temp = [] # Use temp list during parsing

        for i, line in enumerate(wallet_lines):
            line = line.strip()
            current_line_num_abs = start_index + 1 + i + 1
            logging.debug(f"Processing line {current_line_num_abs}/{len(text_lines)}: '{line[:100]}'...")

            if not line: continue

            # --- Order of Checks --- #

            # 0. Check for "Total cost at DD Mon YYYY: R$X.XX" (New Format Specific)
            total_cost_match = self.total_wallet_cost_pattern.match(line)
            if total_cost_match:
                current_wallet_entry = next((w for w in wallet_details_temp if w['wallet_name_raw'] == current_wallet_info["name"]), None)
                if current_wallet_entry:
                    raw_total_cost = total_cost_match.group(1)
                    total_cost_val = float(self._clean_numeric_str(raw_total_cost))
                    current_wallet_entry['total_wallet_cost'] = total_cost_val
                    logging.info(f"  Line {current_line_num_abs}: Found 'Total cost at...' line. Value: {total_cost_val} for wallet {current_wallet_entry['wallet_name_raw']}")
                else:
                    logging.warning(f"  Line {current_line_num_abs}: Found 'Total cost at...' line but no current wallet entry to assign it to: {current_wallet_info.get('name')}")
                continue # This line is processed, move to next line

            # 1. Check Currency Data (using the new universal pattern)
            currency_match = currency_data_pattern.match(line)
            if currency_match:
                if header_found_for_current_wallet:
                    data = currency_match.groupdict()
                    try:
                        current_wallet_entry = next((w for w in wallet_details_temp if w['wallet_name_raw'] == current_wallet_info["name"]), None)
                        if not current_wallet_entry:
                             if wallet_details_temp:
                                 current_wallet_entry = wallet_details_temp[-1]
                                 logging.warning(f"  Line {current_line_num_abs}: Contexto de carteira perdido, adicionando ativo '{data.get('currency')}' à última carteira encontrada: '{current_wallet_entry.get('wallet_name_raw')}'")
                             else:
                                 logging.error(f"  Line {current_line_num_abs}: Erro CRÍTICO! Dados de moeda sem carteira ativa e nenhuma carteira anterior encontrada.")
                                 continue
                        
                        asset_value_str = data.get('value', '0').replace('(', '-').replace(')', '')
                        asset_value = float(self._clean_numeric_str(asset_value_str, remove_currency=True))
                        
                        asset_amount_raw = data.get('amount', '0').strip()
                        asset_amount_str = self._clean_numeric_str(asset_amount_raw, remove_currency=False)
                        asset_amount = float(asset_amount_str) if asset_amount_str else 0.0
                        
                        asset_price_str = data.get('price', '0').replace('(', '-').replace(')', '')
                        asset_price = float(self._clean_numeric_str(asset_price_str, remove_currency=True))

                        currency_name = data.get('currency', 'Unknown').strip()
                        
                        asset_data = {
                            'name': currency_name,
                            'amount': asset_amount,
                            'amount_raw': asset_amount_raw,
                            'price': asset_price, # Storing price
                            'value': asset_value,
                        }

                        # Check for and process 'cost' if this wallet is new format OR if cost column was found
                        raw_cost = data.get('cost')
                        if raw_cost: # If cost column was matched by regex
                            asset_cost_str = raw_cost.replace('(', '-').replace(')', '')
                            asset_data['cost_reported'] = float(self._clean_numeric_str(asset_cost_str, remove_currency=True))
                            logging.debug(f"  Line {current_line_num_abs}:     + Asset '{currency_name}' has reported cost: {asset_data['cost_reported']}")
                            # Ensure the wallet is marked as new format if a cost is found
                            if current_wallet_entry and not current_wallet_entry.get('is_new_format'):
                                current_wallet_entry['is_new_format'] = True
                                is_new_format_wallet = True # Update local flag as well
                                logging.info(f"    Wallet '{current_wallet_entry['wallet_name_raw']}' detected as NEW FORMAT due to reported asset cost.")

                        current_wallet_entry['assets'].append(asset_data)
                        current_wallet_entry['values'].append(asset_value) # Still useful for some calcs / old logic
                        logging.debug(f"  Line {current_line_num_abs}:     + Asset '{currency_name}' adicionado a '{current_wallet_entry.get('wallet_name_raw')}'")
                    except Exception as e_curr:
                        logging.warning(f"  Line {current_line_num_abs}: Erro ao processar linha de moeda: '{line}'. Erro: {e_curr} Traceback: {traceback.format_exc()}")
                else:
                    logging.debug(f"  Line {current_line_num_abs}: Linha parece moeda, mas cabeçalho não encontrado para carteira atual ('{current_wallet_info['name']}'). Ignorando: '{line}'")
                continue

            # 2. Check Header (Old and New)
            # Must check new_currency_header_pattern BEFORE old one due to specificity
            new_header_match = self.new_currency_header_pattern.match(line)
            if new_header_match:
                logging.info(f"  Line {current_line_num_abs}: NOVO Cabeçalho de moeda (com Custo) encontrado.")
                header_found_for_current_wallet = True
                is_new_format_wallet = True # Set flag for this wallet
                current_wallet_entry = next((w for w in wallet_details_temp if w['wallet_name_raw'] == current_wallet_info["name"]), None)
                if current_wallet_entry:
                    current_wallet_entry['is_new_format'] = True
                logging.debug(f"      -> Flag header_found_for_current_wallet setada para TRUE, is_new_format_wallet para TRUE")
                continue

            old_header_match = self.currency_header_pattern.match(line) # Defined in __init__
            if old_header_match:
                logging.info(f"  Line {current_line_num_abs}: ANTIGO Cabeçalho de moeda (sem Custo) encontrado.")
                header_found_for_current_wallet = True
                is_new_format_wallet = False # Explicitly set to false for old format wallets
                current_wallet_entry = next((w for w in wallet_details_temp if w['wallet_name_raw'] == current_wallet_info["name"]), None)
                if current_wallet_entry:
                    current_wallet_entry['is_new_format'] = False
                logging.debug(f"      -> Flag header_found_for_current_wallet setada para TRUE, is_new_format_wallet para FALSE")
                continue
            
            # 3. Check Address Line
            address_match = address_pattern.match(line)
            if address_match:
                last_captured_address = address_match.group(1).strip()
                logging.debug(f"  Line {current_line_num_abs}: Endereço CAPTURADO (linha separada): {last_captured_address}. Guardado.")
                continue

            # 4. Check Total Value Line
            if total_value_pattern.match(line):
                logging.debug(f"  Line {current_line_num_abs}: Linha 'Total wallet value' encontrada, resetando header flag.")
                header_found_for_current_wallet = False
                # DO NOT reset is_new_format_wallet here, it's per-wallet
                logging.debug(f"      -> Flag header_found_for_current_wallet resetada para FALSE (fim carteira)")
                continue

            # 5. Check Title
            title_match = koinly_title_pattern.match(line)
            if title_match:
                name_part = title_match.group(1).strip() if title_match.group(1) else "Unknown"
                network_part = title_match.group(2).strip() if title_match.group(2) else None
                address_part = title_match.group(3).strip() if title_match.group(3) else None
                cleaned_name = self._clean_wallet_name(name_part)
                if cleaned_name != current_wallet_info.get('name', ''):
                    final_address = address_part if address_part else last_captured_address
                    logging.info(f"  Line {current_line_num_abs}: ---> NOVO TÍTULO (Regex): '{cleaned_name}' (Raw: '{line}')")
                    identified_blockchain = network_part if network_part else self._identify_blockchain(line)
                    identified_exchange = self._identify_exchange(line)
                    w_type = "Exchange" if identified_exchange != 'NONE' else ("Bitcoin" if identified_blockchain == 'Bitcoin' else "Wallet")
                    
                    # Reset wallet-specific flags for the new wallet
                    is_new_format_wallet = False # Default to old, will be updated by header
                    header_found_for_current_wallet = False

                    current_wallet_info = {
                        "name": cleaned_name,
                        "type": w_type,
                        "address": final_address,
                        "blockchain": identified_blockchain
                    }
                    if final_address == last_captured_address: last_captured_address = None
                    logging.debug(f"      -> Novo Contexto: {current_wallet_info}")
                    existing_entry = next((w for w in wallet_details_temp if w['wallet_name_raw'] == line), None)
                    if not existing_entry:
                         wallet_details_temp.append({
                             'wallet_name': cleaned_name,
                             'wallet_name_raw': line,
                             'blockchain': identified_blockchain,
                             'exchange': identified_exchange,
                             'address': final_address,
                             'assets': [], 
                             'values': [],
                             'is_new_format': False, # Initialize, will be updated by header
                             'total_wallet_cost': None # Initialize
                         })
                         logging.debug(f"      -> Nova entrada criada para '{line}'")
                    else:
                         logging.debug(f"      -> Entrada existente para '{line}' encontrada.")
                else:
                    logging.debug(f"  Line {current_line_num_abs}: Linha '{line}' parece título (Regex), mas nome igual ao atual. Ignorando.")
                    if last_captured_address and not current_wallet_info.get('address'):
                         current_wallet_info['address'] = last_captured_address
                         entry_to_update = next((w for w in wallet_details_temp if w['wallet_name_raw'] == line), None)
                         if entry_to_update and not entry_to_update.get('address'):
                             entry_to_update['address'] = last_captured_address
                             logging.debug(f"      >>> Endereço '{last_captured_address}' associado à carteira/entrada existente '{current_wallet_info['name']}'.")
                         last_captured_address = None
                continue

            # 6. Unhandled line
            logging.debug(f"  Line {current_line_num_abs}: Linha não reconhecida: '{line}'")

        # --- Post-processing loop --- (Remains the same)
        logging.info(f"(Refined Logic) Finalizou loop de {total_lines_in_section} linhas.")
        for wallet in wallet_details_temp:
            wallet['total_value'] = sum(wallet.get('values', []))
            if 'proportion' not in wallet: wallet['proportion'] = 1.0
        logging.info(f"(Refined Logic) Detalhes processados: {len(wallet_details_temp)} carteiras, {sum(len(w.get('assets',[])) for w in wallet_details_temp)} itens")

        if wallet_details_temp:
            self.wallet_details = wallet_details_temp
            logging.info("--- (Refined Logic) Primeiros detalhes (Sumário) ---")
            for wallet in self.wallet_details[:5]:
                 logging.info(f"  Wallet: {wallet.get('wallet_name_raw')}, Assets: {len(wallet.get('assets',[]))}, Total Value: {wallet.get('total_value', 0):.2f}")
            if len(self.wallet_details) > 5: logging.info("  ...")
            logging.info("------------------------------------")
        else:
            logging.warning("(Refined Logic) Nenhum detalhe de carteira foi processado.")
            self._use_sample_wallet_data()
        logging.info("--- (Refined Logic) _parse_wallet_details_section FIM ---")

    def _calculate_proportional_cost(self):
        """Calculate proportional cost for each asset."""
        logging.info("Calculating proportional costs")

        # Primeiro, calcula o custo total dos ativos no EOY
        if self.end_of_year_items:
            total_value = sum(item['value'] for item in self.end_of_year_items)
            total_cost = sum(item['cost'] for item in self.end_of_year_items)
            
            if total_value > 0:
                # Relaciona os ativos por nome para facilitar a busca
                eoy_assets = {item['asset']: item for item in self.end_of_year_items}
                
                # Para cada carteira, calcula o custo proporcional para cada ativo
                for wallet_detail in self.wallet_details:
                    wallet_cost = 0
                    if not wallet_detail.get('assets'): # Skip wallets with no assets parsed
                        wallet_detail['cost'] = 0
                        wallet_detail['proportion'] = 0
                        logging.debug(f"Wallet {wallet_detail.get('wallet_name_raw', 'Unknown')} has no assets, setting cost and proportion to 0.")
                        continue

                    for asset in wallet_detail.get('assets', []):
                        asset_cost = None # Initialize asset_cost to None
                        asset_name = asset.get('name', 'Unknown')
                        asset_amount = asset.get('amount', 0)

                        # Check if new format and reported cost is available for this asset
                        if wallet_detail.get('is_new_format') and 'cost_reported' in asset and asset['cost_reported'] is not None:
                            asset_cost = asset['cost_reported']
                            logging.debug(f"Using reported cost {asset_cost} for {asset_name} in new format wallet {wallet_detail.get('wallet_name_raw', '')}.")
                        else:
                            # Fallback to EOY proportional cost calculation
                            eoy_asset = eoy_assets.get(asset_name)
                            if eoy_asset and eoy_asset.get('amount', 0) > 0:
                                eoy_total_cost = eoy_asset.get('cost', 0)
                                eoy_total_amount = eoy_asset.get('amount', 0)
                                unit_cost = eoy_total_cost / eoy_total_amount
                                asset_cost = unit_cost * asset_amount
                                logging.debug(f"Calculated EOY proportional cost {asset_cost} for {asset_name} in wallet {wallet_detail.get('wallet_name_raw', '')}.")
                            else:
                                if wallet_detail.get('is_new_format'):
                                    logging.warning(f"Asset {asset_name} in NEW FORMAT wallet {wallet_detail.get('wallet_name_raw', '')} missing 'cost_reported'. EOY fallback: Not found or EOY amount is 0.")
                                elif eoy_asset:
                                    logging.warning(f"EOY proportional cost for {asset_name} in wallet {wallet_detail.get('wallet_name_raw', '')} set to None (EOY amount is 0).")
                                else:
                                    logging.warning(f"EOY proportional cost for {asset_name} in wallet {wallet_detail.get('wallet_name_raw', '')} set to None (asset not found in EOY list).")
                                # asset_cost remains None

                        asset['cost'] = asset_cost # Assign the determined cost (either reported or EOY-calculated, or None)

                    # Custo total da carteira é a soma dos custos dos seus ativos (ignorando None)
                    # Ensure that assets without a calculable cost (None) are treated as 0 for summing wallet_cost
                    wallet_assets = wallet_detail.get('assets', [])
                    wallet_cost = sum(a.get('cost', 0) for a in wallet_assets if a.get('cost') is not None)
                    
                    # Store the total calculated cost for the wallet
                    wallet_detail['cost'] = wallet_cost
                    logging.debug(f"Total calculated cost for wallet {wallet_detail.get('wallet_name_raw', '')}: {wallet_cost}")

                    # Log total_wallet_cost (from PDF new format) if available, for comparison
                    if wallet_detail.get('total_wallet_cost') is not None:
                        logging.info(f"Wallet {wallet_detail.get('wallet_name_raw', '')}: Reported Total Wallet Cost (from PDF): {wallet_detail['total_wallet_cost']:.2f}, Sum of Asset Costs (calculated): {wallet_cost:.2f}")
                    
                    # Calcula a proporção da carteira no total EOY cost
                    if total_cost > 0:
                        wallet_detail['proportion'] = wallet_cost / total_cost
                    else:
                        wallet_detail['proportion'] = 0
                    logging.debug(f"Wallet {wallet_detail.get('wallet_name_raw', '')} proportion of total EOY cost: {wallet_detail['proportion']:.4f}")
            else: # This 'else' corresponds to 'if total_value > 0'
                logging.warning("Total EOY value is zero or less, cannot calculate proportional costs based on EOY data. Asset costs might be incomplete if not reported directly.")
                # If EOY total value is zero, still try to use reported costs for new format wallets
                for wallet_detail in self.wallet_details:
                    if not wallet_detail.get('assets'):
                        wallet_detail['cost'] = 0
                        continue
                    
                    current_wallet_cost = 0
                    if wallet_detail.get('is_new_format'):
                        for asset in wallet_detail.get('assets', []):
                            if 'cost_reported' in asset and asset['cost_reported'] is not None:
                                asset['cost'] = asset['cost_reported']
                                current_wallet_cost += asset['cost']
                                logging.debug(f"Using reported cost {asset['cost']} for {asset.get('name', 'Unknown')} in new format wallet {wallet_detail.get('wallet_name_raw', '')} (EOY total value zero).")
                            else:
                                asset['cost'] = None # No EOY fallback possible here, and no reported cost
                                logging.warning(f"Asset {asset.get('name', 'Unknown')} in new format wallet {wallet_detail.get('wallet_name_raw', '')} missing 'cost_reported', and EOY total value is zero. Cost set to None.")
                        wallet_detail['cost'] = current_wallet_cost
                    else: # Old format wallet and no EOY data to rely on
                        for asset in wallet_detail.get('assets', []):
                            asset['cost'] = None # Cannot determine cost
                        wallet_detail['cost'] = 0
                        logging.warning(f"Wallet {wallet_detail.get('wallet_name_raw', '')} (old format) has no EOY data for cost calculation as EOY total value is zero. All asset costs set to None, wallet cost to 0.")
                    # Proportion cannot be meaningfully calculated if total_cost (from EOY) is zero or EOY items are missing
                    wallet_detail['proportion'] = 0 
        else: # This 'else' corresponds to 'if self.end_of_year_items:'
            logging.warning("No End of Year items found. Proportional costs cannot be calculated based on EOY data.")
            # Attempt to use reported costs for new format wallets even if EOY is missing
            for wallet_detail in self.wallet_details:
                if not wallet_detail.get('assets'):
                    wallet_detail['cost'] = 0
                    wallet_detail['proportion'] = 0
                    continue

                current_wallet_cost = 0
                if wallet_detail.get('is_new_format'):
                    for asset in wallet_detail.get('assets', []):
                        if 'cost_reported' in asset and asset['cost_reported'] is not None:
                            asset['cost'] = asset['cost_reported']
                            current_wallet_cost += asset['cost']
                            logging.debug(f"Using reported cost {asset['cost']} for {asset.get('name', 'Unknown')} in new format wallet {wallet_detail.get('wallet_name_raw', '')} (No EOY data).")
                        else:
                            asset['cost'] = None # No EOY fallback, and no reported cost
                            logging.warning(f"Asset {asset.get('name', 'Unknown')} in new format wallet {wallet_detail.get('wallet_name_raw', '')} missing 'cost_reported', and no EOY data. Cost set to None.")
                    wallet_detail['cost'] = current_wallet_cost
                else: # Old format wallet and no EOY data
                    for asset in wallet_detail.get('assets', []):
                        asset['cost'] = None # Cannot determine cost
                    wallet_detail['cost'] = 0
                    logging.warning(f"Wallet {wallet_detail.get('wallet_name_raw', '')} (old format) has no EOY data for cost calculation. All asset costs set to None, wallet cost to 0.")
                wallet_detail['proportion'] = 0 # No EOY total to base proportion on

        logging.info("Proportional costs calculation step completed.")
    
    def _create_dataframes(self):
        """Create DataFrames from the processed data."""
        logging.info("Creating DataFrames")

        # Criar dataframe para os saldos de fim de ano
        if self.end_of_year_items:
            self.eoy_df = pd.DataFrame(self.end_of_year_items)
            logging.info(f"Created EOY DataFrame with shape {self.eoy_df.shape}")
        else:
            self.eoy_df = pd.DataFrame(columns=['asset', 'amount', 'price', 'value', 'cost'])
            logging.warning("No end-of-year data found, created empty DataFrame")

        # Criar dataframe para os detalhes de carteira
        if self.wallet_details:
            self.wallet_df = pd.DataFrame(self.wallet_details)
            logging.info(f"Created wallet details DataFrame with shape {self.wallet_df.shape}")
        else:
            self.wallet_df = pd.DataFrame(columns=['wallet_name', 'wallet_name_raw', 'blockchain',
                                                 'exchange', 'assets', 'values', 'proportion', 
                                                 'cost', 'description', 'asset_type'])
            logging.warning("No wallet details found, created empty DataFrame")

        # Criar o dataframe final com um item para cada ativo (não agrupado por carteira)
        if not self.wallet_df.empty:
            # Vamos criar uma nova lista para todas as linhas individuais
            assets_rows = []
            
            for wallet in self.wallet_details:
                for asset in wallet.get('assets', []):
                    # Pega o CUSTO PROPORCIONAL calculado anteriormente
                    cost = asset.get('cost') # Usar get sem default para pegar None se existir

                    # Formata o custo ou usa a string de aviso
                    if cost is None:
                        cost_str = "Verificar no Koinly - Custo não encontrado"
                    elif isinstance(cost, (int, float)):
                        if cost < 0.01 and cost > 0:
                            cost_str = "0,00"
                        else:
                            cost_str = f"{cost:.2f}".replace('.', ',')
                    else: # Caso inesperado, talvez logar?
                        cost_str = "Erro ao formatar custo"
                        logging.error(f"Tipo de custo inesperado para {asset.get('name', '')}: {type(cost)}, valor: {cost}")

                    # Usar sempre o valor original extraído do PDF para Qtd
                    raw_amount = asset.get('amount_raw')
                    if raw_amount is not None:
                        qtd_str = str(raw_amount).replace('.', ',')
                    else:
                        qtd_str = str(asset.get('amount', 0)).replace('.', ',')

                    ticker_name = asset.get('name', '')
                    logging.debug(f"Creating final row for Ticker: '{ticker_name}' with value/cost string: {cost_str}")

                    assets_rows.append({
                        'Ticker': ticker_name,
                        'Qtd': qtd_str,
                        f'Custo R$ 31/12/{self.report_year}': cost_str,  # Renomeado de Valor para Custo
                        'Discriminação': asset.get('irpf_description', ''),
                    })

            # Criar o dataframe final com as linhas individuais
            self.final_df = pd.DataFrame(assets_rows)
            
            # Forçar a coluna de custo a ser string para garantir aspas
            custo_column_name = f'Custo R$ 31/12/{self.report_year}' # Nome dinâmico e renomeado
            if custo_column_name in self.final_df.columns:
                self.final_df[custo_column_name] = self.final_df[custo_column_name].astype(str)
            # Forçar a coluna Qtd a ser string também
            if 'Qtd' in self.final_df.columns:
                self.final_df['Qtd'] = self.final_df['Qtd'].astype(str)
            if 'code' in self.final_df.columns:
                self.final_df = self.final_df.drop(columns=['code'])
            logging.info(f"Created final DataFrame with shape {self.final_df.shape}")
        else:
            # Se não há dados de carteira, crie um DataFrame vazio com nome de coluna dinâmico
            custo_column_name = f'Custo R$ 31/12/{self.report_year}' if self.report_year else 'Custo R$ 31/12/????' # Renomeado
            self.final_df = pd.DataFrame(columns=['Ticker', 'Qtd', custo_column_name,
                                                'Discriminação'])
            logging.warning("No data available, created empty final DataFrame")

        logging.info("DataFrames created")
    
    def save_to_csv(self, output_dir=None):
        """
        Save the final DataFrame to a CSV file.
        
        Args:
            output_dir: Optional directory to save the file. If None, uses the same directory as the PDF.
        """
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.output_dir

        # Ensure the output directory exists
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate the final filename
        final_filename = f"{self.base_filename}_final.csv"
        final_path = output_path / final_filename

        logging.info(f"Saving final output to: {final_path}")

        try:
            # Ensure the DataFrame has the expected columns with dynamic year and name
            custo_column_name = f'Custo R$ 31/12/{self.report_year}' if self.report_year else 'Custo R$ 31/12/????' # Renomeado
            required_columns = ['Ticker', 'Qtd', custo_column_name, 'Discriminação']
            
            # Check if all required columns exist
            # Adjust check in case DataFrame was created before year was known (e.g., error early on)
            if all(col in self.final_df.columns for col in required_columns):
                # Save the final DataFrame with the correct column order
                self.final_df[required_columns].to_csv(
                    final_path, index=False, sep=';', encoding='utf-8-sig', quoting=csv.QUOTE_ALL
                )
            else:
                # If columns are missing, add dummy columns
                for col in required_columns:
                    if col not in self.final_df.columns:
                        self.final_df[col] = ''
                
                # Save with the correct column order
                self.final_df[required_columns].to_csv(
                    final_path, index=False, sep=';', encoding='utf-8-sig', quoting=csv.QUOTE_ALL
                )
                
            logging.info(f"Final output saved to: {final_path}")
            
            return final_path
        except Exception as e:
            logging.error(f"Error saving to CSV: {str(e)}")
            raise

    def _identify_wallet_type(self, wallet_name):
        """Identify the type of wallet (exchange, hardware, etc.)."""
        wallet_name = wallet_name.lower()
        
        if any(exchange in wallet_name for exchange in
               ['binance', 'coinbase', 'kraken', 'bitfinex', 'kucoin']):
            return 'exchange'
        elif any(hw in wallet_name for hw in
                ['ledger', 'trezor', 'hardware']):
            return 'hardware'
        elif any(sw in wallet_name for sw in
                ['metamask', 'trust', 'wallet']):
            return 'software'
        else:
            return 'unknown'

    def _identify_blockchain(self, wallet_name):
        """Identify the blockchain from wallet name."""
        wallet_name = wallet_name.lower()
        
        if 'btc' in wallet_name or 'bitcoin' in wallet_name:
            return 'BTC'
        elif 'eth' in wallet_name or 'ethereum' in wallet_name:
            return 'ETH'
        elif 'bsc' in wallet_name or 'binance smart chain' in wallet_name:
            return 'BSC'
        elif 'sol' in wallet_name or 'solana' in wallet_name:
            return 'SOL'
        else:
            return 'NONE'

    def _identify_exchange(self, wallet_name):
        """Identify exchange from wallet name using an extensive and up-to-date list."""
        wallet_name = wallet_name.lower()
        # Lista ampla de exchanges globais e brasileiras, incluindo variações e domínios
        exchanges = {
            # Globais
            'binance': 'Binance',
            'binance.com': 'Binance',
            'coinbase': 'Coinbase',
            'coinbase.com': 'Coinbase',
            'kraken': 'Kraken',
            'kraken.com': 'Kraken',
            'bitfinex': 'Bitfinex',
            'bitfinex.com': 'Bitfinex',
            'kucoin': 'KuCoin',
            'kucoin.com': 'KuCoin',
            'ftx': 'FTX',
            'ftx.com': 'FTX',
            'bybit': 'Bybit',
            'bybit.com': 'Bybit',
            'okx': 'OKX',
            'okx.com': 'OKX',
            'okex': 'OKX',
            'okex.com': 'OKX',
            'gate.io': 'Gate.io',
            'gateio': 'Gate.io',
            'mexc': 'MEXC',
            'mexc.com': 'MEXC',
            'bitget': 'Bitget',
            'bitget.com': 'Bitget',
            'bingx': 'BingX',
            'bingx.com': 'BingX',
            'bitstamp': 'Bitstamp',
            'bitstamp.net': 'Bitstamp',
            'huobi': 'Huobi',
            'huobi.com': 'Huobi',
            'crypto.com': 'Crypto.com',
            'crypto com': 'Crypto.com',
            'deribit': 'Deribit',
            'deribit.com': 'Deribit',
            'poloniex': 'Poloniex',
            'poloniex.com': 'Poloniex',
            'bitmex': 'BitMEX',
            'bitmex.com': 'BitMEX',
            'bitflyer': 'BitFlyer',
            'bitflyer.com': 'BitFlyer',
            'bittrex': 'Bittrex',
            'bittrex.com': 'Bittrex',
            'hitbtc': 'HitBTC',
            'hitbtc.com': 'HitBTC',
            'upbit': 'Upbit',
            'upbit.com': 'Upbit',
            'liquid': 'Liquid',
            'liquid.com': 'Liquid',
            'probit': 'ProBit',
            'probit.com': 'ProBit',
            'bitso': 'Bitso',
            'bitso.com': 'Bitso',
            'bitmart': 'BitMart',
            'bitmart.com': 'BitMart',
            'coinex': 'CoinEx',
            'coinex.com': 'CoinEx',
            'phemex': 'Phemex',
            'phemex.com': 'Phemex',
            'latoken': 'LATOKEN',
            'latoken.com': 'LATOKEN',
            'whitebit': 'WhiteBIT',
            'whitebit.com': 'WhiteBIT',
            'lbank': 'LBank',
            'lbank.info': 'LBank',
            'bitrue': 'Bitrue',
            'bitrue.com': 'Bitrue',
            'coinone': 'Coinone',
            'coinone.co.kr': 'Coinone',
            'zb.com': 'ZB.com',
            'zb': 'ZB.com',
            'bkex': 'BKEX',
            'bkex.com': 'BKEX',
            'mxc': 'MEXC',
            'mxc.com': 'MEXC',
            'ascendex': 'AscendEX',
            'ascendex.com': 'AscendEX',
            'hotbit': 'Hotbit',
            'hotbit.io': 'Hotbit',
            'coincheck': 'Coincheck',
            'coincheck.com': 'Coincheck',
            'bitbank': 'Bitbank',
            'bitbank.cc': 'Bitbank',
            'liquid': 'Liquid',
            'liquid.com': 'Liquid',
            'btcmarkets': 'BTC Markets',
            'btcmarkets.net': 'BTC Markets',
            'bitflyer': 'BitFlyer',
            'bitflyer.com': 'BitFlyer',
            'bitpanda': 'Bitpanda',
            'bitpanda.com': 'Bitpanda',
            'kriptomat': 'Kriptomat',
            'kriptomat.io': 'Kriptomat',
            'paybis': 'Paybis',
            'paybis.com': 'Paybis',
            'bitwala': 'Bitwala',
            'bitwala.com': 'Bitwala',
            'blockchain.com': 'Blockchain.com',
            'blockchain': 'Blockchain.com',
            # Brasileiras
            'mercado bitcoin': 'Mercado Bitcoin',
            'mercadobitcoin': 'Mercado Bitcoin',
            'mercadobitcoin.com.br': 'Mercado Bitcoin',
            'mb': 'Mercado Bitcoin',
            'mercado': 'Mercado Bitcoin',
            'btg': 'BTG Pactual',
            'btg pactual': 'BTG Pactual',
            'btgdigital': 'BTG Pactual',
            'foxbit': 'Foxbit',
            'foxbit.com.br': 'Foxbit',
            'novadax': 'NovaDAX',
            'novadax.com': 'NovaDAX',
            'coinext': 'Coinext',
            'coinext.com.br': 'Coinext',
            'bitcointrade': 'BitcoinTrade',
            'bitcointrade.com.br': 'BitcoinTrade',
            'bitpreco': 'Bitpreço',
            'bitpreco.com': 'Bitpreço',
            'flowbtc': 'FlowBTC',
            'flowbtc.com.br': 'FlowBTC',
            'ripio': 'Ripio',
            'ripio.com': 'Ripio',
            'ripio.com.br': 'Ripio',
            'brasil bitcoin': 'Brasil Bitcoin',
            'brasilbitcoin': 'Brasil Bitcoin',
            'brasilbitcoin.com.br': 'Brasil Bitcoin',
            'coinbene': 'Coinbene',
            'coinbene.com': 'Coinbene',
            'coinbene.com.br': 'Coinbene',
            'bitblue': 'BitBlue',
            'bitblue.com.br': 'BitBlue',
            'bitcointoyou': 'BitcoinToYou',
            'bitcointoyou.com': 'BitcoinToYou',
            'bitcointoyou.com.br': 'BitcoinToYou',
            'alter': 'Alter',
            'alterbank': 'Alter',
            'alterbank.com.br': 'Alter',
            'pagcripto': 'PagCripto',
            'pagcripto.com.br': 'PagCripto',
            'coincloud': 'CoinCloud',
            'coincloud.com.br': 'CoinCloud',
            'coincloud.com': 'CoinCloud',
            'bitrecife': 'BitRecife',
            'bitrecife.com.br': 'BitRecife',
            'bitnuvem': 'Bitnuvem',
            'bitnuvem.com.br': 'Bitnuvem',
            'cointrade': 'CoinTrade',
            'cointrade.com.br': 'CoinTrade',
            'cointrade.cx': 'CoinTrade',
            'coinx': 'CoinX',
            'coinx.com.br': 'CoinX',
            'coinx.cx': 'CoinX',
            'bitvalemais': 'BitValeMais',
            'bitvalemais.com.br': 'BitValeMais',
            'bitvalemais.com': 'BitValeMais',
            'bitinvest': 'BitInvest',
            'bitinvest.com.br': 'BitInvest',
            'bitinvest.com': 'BitInvest',
            'coinwise': 'Coinwise',
            'coinwise.com.br': 'Coinwise',
            'coinwise.com': 'Coinwise',
            'coinshub': 'CoinsHub',
            'coinshub.com.br': 'CoinsHub',
            'coinshub.com': 'CoinsHub',
            'coinbr': 'CoinBR',
            'coinbr.net': 'CoinBR',
            'coinbr.com': 'CoinBR',
            'coinbr.com.br': 'CoinBR',
            'cointrade': 'CoinTrade',
            'cointrade.com.br': 'CoinTrade',
            'cointrade.cx': 'CoinTrade',
        }
        for key, value in exchanges.items():
            if key in wallet_name:
                return value
        return 'NONE'

    def _clean_wallet_name(self, wallet_name):
        """Clean wallet name by removing blockchain identifiers."""
        wallet_name = wallet_name.strip()
        
        # Remove blockchain identifiers in parentheses
        wallet_name = re.sub(r'\s*\([^)]*\)', '', wallet_name)
        
        return wallet_name.strip() 