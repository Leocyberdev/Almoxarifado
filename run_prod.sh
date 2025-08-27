#!/bin/bash

# Script para rodar a aplicação em produção
echo "Iniciando aplicação em produção..."

# Inicializa o banco de dados
python init_render_db.py

# Inicia a aplicação com Gunicorn
exec gunicorn src.main:app --bind 0.0.0.0:$PORT