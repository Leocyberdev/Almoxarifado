#!/usr/bin/env python3
"""
Script para executar a aplicação em modo de desenvolvimento
"""

import os
import sys

# Garante que estamos no ambiente de desenvolvimento
os.environ['FLASK_ENV'] = 'development'

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(__file__))

from src.main import app

if __name__ == '__main__':
    print("=== Sistema de Almoxarifado - Modo Desenvolvimento ===")
    print("Ambiente: Desenvolvimento (SQLite)")
    print("URL: http://localhost:5000")
    print("Usuário padrão: Monter / Senha: almox")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

