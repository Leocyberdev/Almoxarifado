
#!/usr/bin/env python3
"""
Script para migrar dados do SQLite (desenvolvimento) para PostgreSQL (produção)
"""

import os
import sys
import sqlite3
import json
from datetime import datetime

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def migrate_data():
    """Migra dados do SQLite para PostgreSQL"""
    print("🚀 Iniciando migração de dados SQLite -> PostgreSQL...")
    
    # Caminho do banco SQLite
    sqlite_db_path = os.path.join(os.path.dirname(__file__), 'database', 'app.db')
    
    if not os.path.exists(sqlite_db_path):
        print("⚠️ Banco SQLite não encontrado. Pulando migração.")
        return
    
    try:
        # Conecta ao SQLite
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_conn.row_factory = sqlite3.Row  # Para acessar por nome da coluna
        
        # Importa os modelos após configurar o ambiente
        from src.main import create_app
        from src.models.user import db, User
        from src.models.almoxarifado import (
            Produto, Obra, Funcionario, Movimentacao, 
            Categoria, Fornecedor
        )
        
        # Cria app em modo produção
        os.environ['FLASK_ENV'] = 'production'
        app = create_app('production')
        
        with app.app_context():
            print("📊 Verificando dados existentes no PostgreSQL...")
            
            # Verifica se já existe dados no PostgreSQL
            if User.query.count() > 0:
                print("✅ PostgreSQL já contém dados. Pulando migração.")
                return
            
            print("📦 Migrando dados das tabelas...")
            
            # Migra Usuários
            cursor = sqlite_conn.execute("SELECT * FROM users")
            users = cursor.fetchall()
            for user_data in users:
                user = User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    tipo_usuario=user_data['tipo_usuario'],
                    ativo=bool(user_data['ativo']),
                    data_criacao=datetime.fromisoformat(user_data['data_criacao']) if user_data['data_criacao'] else datetime.now()
                )
                db.session.add(user)
            print(f"   ✅ Usuários: {len(users)} registros")
            
            # Migra Categorias
            try:
                cursor = sqlite_conn.execute("SELECT * FROM categorias")
                categorias = cursor.fetchall()
                for cat_data in categorias:
                    categoria = Categoria(
                        id=cat_data['id'],
                        nome=cat_data['nome'],
                        descricao=cat_data.get('descricao'),
                        ativo=bool(cat_data.get('ativo', True))
                    )
                    db.session.add(categoria)
                print(f"   ✅ Categorias: {len(categorias)} registros")
            except sqlite3.OperationalError:
                print("   ⚠️ Tabela categorias não encontrada")
            
            # Migra Fornecedores
            try:
                cursor = sqlite_conn.execute("SELECT * FROM fornecedores")
                fornecedores = cursor.fetchall()
                for forn_data in fornecedores:
                    fornecedor = Fornecedor(
                        id=forn_data['id'],
                        nome=forn_data['nome'],
                        contato=forn_data.get('contato'),
                        telefone=forn_data.get('telefone'),
                        email=forn_data.get('email'),
                        endereco=forn_data.get('endereco'),
                        ativo=bool(forn_data.get('ativo', True))
                    )
                    db.session.add(fornecedor)
                print(f"   ✅ Fornecedores: {len(fornecedores)} registros")
            except sqlite3.OperationalError:
                print("   ⚠️ Tabela fornecedores não encontrada")
            
            # Migra Funcionários
            try:
                cursor = sqlite_conn.execute("SELECT * FROM funcionarios")
                funcionarios = cursor.fetchall()
                for func_data in funcionarios:
                    funcionario = Funcionario(
                        id=func_data['id'],
                        nome=func_data['nome'],
                        cargo=func_data.get('cargo'),
                        ativo=bool(func_data.get('ativo', True))
                    )
                    db.session.add(funcionario)
                print(f"   ✅ Funcionários: {len(funcionarios)} registros")
            except sqlite3.OperationalError:
                print("   ⚠️ Tabela funcionarios não encontrada")
            
            # Migra Obras
            try:
                cursor = sqlite_conn.execute("SELECT * FROM obras")
                obras = cursor.fetchall()
                for obra_data in obras:
                    obra = Obra(
                        id=obra_data['id'],
                        nome=obra_data['nome'],
                        endereco=obra_data.get('endereco'),
                        responsavel=obra_data.get('responsavel'),
                        ativa=bool(obra_data.get('ativa', True)),
                        data_inicio=datetime.fromisoformat(obra_data['data_inicio']) if obra_data.get('data_inicio') else None,
                        data_fim=datetime.fromisoformat(obra_data['data_fim']) if obra_data.get('data_fim') else None
                    )
                    db.session.add(obra)
                print(f"   ✅ Obras: {len(obras)} registros")
            except sqlite3.OperationalError:
                print("   ⚠️ Tabela obras não encontrada")
            
            # Migra Produtos
            try:
                cursor = sqlite_conn.execute("SELECT * FROM produtos")
                produtos = cursor.fetchall()
                for prod_data in produtos:
                    produto = Produto(
                        id=prod_data['id'],
                        codigo=prod_data['codigo'],
                        nome=prod_data['nome'],
                        descricao=prod_data.get('descricao'),
                        categoria_id=prod_data.get('categoria_id'),
                        fornecedor_id=prod_data.get('fornecedor_id'),
                        preco=float(prod_data['preco']) if prod_data.get('preco') else 0,
                        unidade_medida=prod_data.get('unidade_medida', 'unidade'),
                        estoque_minimo=int(prod_data.get('estoque_minimo', 0)),
                        quantidade_estoque=int(prod_data.get('quantidade_estoque', 0)),
                        local_produto=prod_data.get('local_produto'),
                        ativo=bool(prod_data.get('ativo', True)),
                        data_cadastro=datetime.fromisoformat(prod_data['data_cadastro']) if prod_data.get('data_cadastro') else datetime.now()
                    )
                    db.session.add(produto)
                print(f"   ✅ Produtos: {len(produtos)} registros")
            except sqlite3.OperationalError:
                print("   ⚠️ Tabela produtos não encontrada")
            
            # Migra Movimentações
            try:
                cursor = sqlite_conn.execute("SELECT * FROM movimentacoes")
                movimentacoes = cursor.fetchall()
                for mov_data in movimentacoes:
                    movimentacao = Movimentacao(
                        id=mov_data['id'],
                        produto_id=mov_data['produto_id'],
                        obra_id=mov_data.get('obra_id'),
                        funcionario_id=mov_data.get('funcionario_id'),
                        tipo_movimentacao=mov_data['tipo_movimentacao'],
                        quantidade=int(mov_data['quantidade']),
                        valor_unitario=float(mov_data.get('valor_unitario', 0)),
                        valor_total=float(mov_data.get('valor_total', 0)),
                        observacoes=mov_data.get('observacoes'),
                        data_movimentacao=datetime.fromisoformat(mov_data['data_movimentacao']) if mov_data.get('data_movimentacao') else datetime.now()
                    )
                    db.session.add(movimentacao)
                print(f"   ✅ Movimentações: {len(movimentacoes)} registros")
            except sqlite3.OperationalError:
                print("   ⚠️ Tabela movimentacoes não encontrada")
            
            # Commit de todos os dados
            db.session.commit()
            print("🎉 Migração concluída com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        if 'db' in locals():
            db.session.rollback()
        raise
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()

if __name__ == "__main__":
    migrate_data()
