import re
import logging

class KoinlyProcessor:
    def _parse_eoy_section(self, text: str) -> dict:
        """
        Parses the 'End of Year Balances' section to extract total cost basis per currency.
        """
        eoy_data = {}
        start_marker = "End of Year Balances"
        end_marker = "Balances per Wallet" # Used as the end marker for the EOY section
        # Regex to find currency lines: Currency Symbol, Quantity, Cost (BRL), Value (BRL), Description
        # Example: BTC 1.00000000 50,000.00 200,000.00 @ R$200,000.00 per BTC
        # Adjusted regex to be more flexible with spacing and capture relevant groups
        eoy_pattern = re.compile(
            r"^([A-Z0-9\\-\\.\\#\\(\\)\\s]+?)\\s+" # Asset Name (allow spaces, dots, hashes, parenthesis) - Non-greedy
            r"([\\d,\\.\\-]+)\\s+"                 # Quantity (allow negative)
            r"([\\d,\\.\\-]+)\\s+"                 # Cost (BRL) (allow negative)
            r"([\\d,\\.\\-]+)\\s+"                 # Value (BRL) (allow negative)
            r"(@ R\\$[\\d,\\.\\s]+ per .+)$",     # Description (starts with @ R$)
            re.MULTILINE
        )

        try:
            start_index = text.index(start_marker)
        except ValueError:
            logging.warning(f"'{start_marker}' section not found in the report. Skipping EOY cost calculation.")
            return eoy_data # Return empty dict if start marker is not found

        # Find end index, default to end of text if end_marker is not found after start_marker
        try:
            end_index = text.index(end_marker, start_index)
        except ValueError:
            end_index = len(text)
            logging.debug(f"'{end_marker}' not found after '{start_marker}'. Parsing EOY until end of text.")

        # Extract the relevant section text
        eoy_text_section = text[start_index + len(start_marker):end_index].strip()
        logging.debug(f"--- Extracted EOY Section Text ---\n{eoy_text_section[:500]}...\n--- End EOY Section ---")


        matches = eoy_pattern.finditer(eoy_text_section)
        processed_count = 0
        for match in matches:
            asset = match.group(1).strip()
            # Clean up asset name if it contains descriptions in parenthesis
            asset = re.sub(r"\\s*\\(.*\\)$", "", asset).strip()
            cost_str = match.group(3)
            cost = self._parse_monetary_value(cost_str)

            if asset and cost is not None:
                # Sum costs if asset appears multiple times (unlikely in EOY summary, but safe)
                eoy_data[asset] = eoy_data.get(asset, 0) + cost
                processed_count += 1
                logging.debug(f"EOY Parsed: Asset={asset}, Cost={cost}")
            else:
                logging.warning(f"Could not parse EOY line: Asset='{asset}', Cost String='{cost_str}'")

        logging.info(f"EOY Balances processados (regex): {processed_count} itens")
        logging.debug(f"EOY Data Dictionary: {eoy_data}")
        return eoy_data 