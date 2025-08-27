#!/usr/bin/env python3
"""
Ponto de entrada principal para a aplicação Flask Almoxarifado
Este arquivo resolve o problema de localização da aplicação Flask durante o deployment
"""

import os
import sys

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import app

if __name__ == "__main__":
    # Configuração para desenvolvimento
    app.run(debug=True, host="0.0.0.0", port=5000)

