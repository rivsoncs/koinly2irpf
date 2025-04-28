"""
Module for fixing Binance Smart Chain (BSC) wallet detection.

This module provides functions to properly identify BSC wallets and prevent them
from being incorrectly classified as Binance Exchange wallets.
"""

import re
import logging
from typing import List, Dict

def process_wallet_details_for_bsc(wallet_details: List[Dict]) -> List[Dict]:
    """
    Process wallet details to correctly identify BSC wallets.
    
    This function fixes the issue where BSC wallets are incorrectly categorized
    as Binance Exchange wallets.
    
    Args:
        wallet_details: List of wallet detail dictionaries
        
    Returns:
        List of wallet details with corrected BSC identification
    """
    logging.info("Processing BSC wallet details - fixing Binance Smart Chain detection")
    
    # BSC name variations to detect
    bsc_names = [
        'binance smart chain',
        'bsc',
        'bnb chain',
        'bnb smart chain'
    ]
    
    fixed_details = []
    
    for detail in wallet_details:
        wallet_name_raw = detail.get('wallet_name_raw', '').lower()
        blockchain = detail.get('blockchain', '')
        
        # Check if this is incorrectly classified as a Binance Exchange wallet
        # but actually contains BSC references
        is_bsc = False
        
        # Check if wallet name contains any BSC variations
        for bsc_name in bsc_names:
            if bsc_name in wallet_name_raw:
                is_bsc = True
                break
        
        # Check for "- 0x" pattern which indicates an address on a blockchain, not an exchange
        if ('0x' in wallet_name_raw and ' - ' in wallet_name_raw):
            parts = wallet_name_raw.split(' - ')
            for part in parts:
                if part.strip().startswith('0x'):
                    is_bsc = True
                    break
        
        # If wallet contains "Smart Chain" or "BSC" and has blockchain "Exchange", fix it
        if is_bsc and blockchain == 'Exchange':
            logging.info(f"Fixing BSC wallet: {wallet_name_raw}")
            # Change blockchain to BSC
            detail['blockchain'] = 'BSC'
            logging.debug(f"Changed blockchain from 'Exchange' to 'BSC' for: {wallet_name_raw}")
        
        fixed_details.append(detail)
    
    logging.info(f"BSC fixes applied to {len(fixed_details)} wallet details")
    return fixed_details 