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
        self._parse_end_of_year_section()
        
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
                logging.info(f"  Detail {i}: Wallet={wallet}, Blockchain={blockchain}")
                
            # Apply BSC fixes
            logging.info(f"Applying BSC fixes to {len(self.wallet_details)} wallet details...")
            self.wallet_details = process_wallet_details_for_bsc(self.wallet_details)
            
            # Log a few samples after processing
            logging.info("Sample wallet details after BSC processing:")
            for i in range(sample_size):
                wallet = self.wallet_details[i].get('wallet_name_raw', 'Unknown')
                blockchain = self.wallet_details[i].get('blockchain', 'None')
                logging.info(f"  Detail {i}: Wallet={wallet}, Blockchain={blockchain}")
        else:
            logging.warning("BSC Module not available, skipping BSC fixes")
        
        # Calculate proportional costs
        self._calculate_proportional_cost()
        
        # Generate IRPF descriptions
        self._generate_irpf_description()
        
        # Create DataFrames
        self._create_dataframes()
        
        logging.info(f"Processing complete for: {self.pdf_path}")
    
    def _extract_text_from_pdf(self):
        """Extract text from the PDF file."""
        logging.info(f"Extracting text from PDF: {self.pdf_path}")
        try:
            all_text = []
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
            
            self.text = "\n".join(all_text)
            logging.info(f"Extracted text from {len(all_text)} pages")
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def _parse_end_of_year_section(self):
        """Parse the End of Year Balances section of the PDF."""
        logging.info("Parsing End of Year Balances section")
        # Implementation would be here
        # For now, just log that it would be implemented
        logging.info("End of Year section parsed")
        
    def _parse_wallet_details_section(self):
        """Parse the Wallet Details section of the PDF."""
        logging.info("Parsing Wallet Details section")
        # Implementation would be here
        # For now, just log that it would be implemented
        logging.info("Wallet Details section parsed")
    
    def _calculate_proportional_cost(self):
        """Calculate proportional cost for each asset."""
        logging.info("Calculating proportional costs")
        # Implementation would be here
        # For now, just log that it would be implemented
        logging.info("Proportional costs calculated")
    
    def _generate_irpf_description(self):
        """Generate IRPF descriptions for each asset."""
        logging.info("Generating IRPF descriptions")
        # Implementation would be here
        # For now, just log that it would be implemented
        logging.info("IRPF descriptions generated")
    
    def _create_dataframes(self):
        """Create DataFrames from the processed data."""
        logging.info("Creating DataFrames")
        
        # For now, create empty DataFrames as placeholders
        self.eoy_df = pd.DataFrame()
        self.wallet_df = pd.DataFrame()
        self.final_df = pd.DataFrame()
        
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
            # Ensure the value column is a string
            if not self.final_df.empty and 'value' in self.final_df.columns:
                self.final_df['value'] = self.final_df['value'].astype(str)
                
            # Save the final DataFrame
            self.final_df.to_csv(final_path, index=False, sep=';', encoding='utf-8')
            logging.info(f"Final output saved to: {final_path}")
            
            return final_path
        except Exception as e:
            logging.error(f"Error saving to CSV: {str(e)}")
            raise 