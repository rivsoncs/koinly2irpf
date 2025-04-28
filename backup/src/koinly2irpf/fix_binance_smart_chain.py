#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo de correção para Binance Smart Chain (BSC).
Melhora a detecção de carteiras BSC no processador Koinly.
"""

import logging
import re

def process_wallet_details_for_bsc(wallet_details):
    """
    Processa detalhes de carteira para melhorar a identificação de Binance Smart Chain.
    
    Este módulo verifica carteiras que foram incorretamente detectadas como
    "Binance Exchange" mas que na verdade são carteiras BSC.
    
    Args:
        wallet_details: Lista de dicionários contendo detalhes de carteiras
        
    Returns:
        Lista atualizada dos detalhes de carteira com identificação BSC corrigida
    """
    logging.info("Processing BSC wallet details - fixing Binance Smart Chain detection")
    
    for wallet in wallet_details:
        wallet_name = wallet.get('wallet_name_raw', '').lower()
        
        # Verifica se é uma carteira BSC
        is_bsc = (
            'bsc' in wallet_name or 
            'binance smart chain' in wallet_name or
            'bnb chain' in wallet_name
        )
        
        # Se for BSC mas foi classificada como Binance Exchange, corrige
        if is_bsc and wallet.get('exchange') == 'Binance':
            wallet['blockchain'] = 'BSC'
            wallet['exchange'] = 'NONE'
            
            # Também corrige o nome da wallet se necessário
            if wallet.get('wallet_name') == 'Binance Exchange':
                wallet['wallet_name'] = 'BSC Wallet'
    
    logging.info("BSC fixes applied to %d wallet details", len(wallet_details))
    return wallet_details 