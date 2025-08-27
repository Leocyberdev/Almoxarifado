
#!/usr/bin/env python3
"""
Script de inicialização do banco para Render
Configura PostgreSQL e migra dados do SQLite se necessário
"""

import os
import sys

# Configura ambiente de produção
os.environ["FLASK_ENV"] = "production"

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(__file__))

def init_render_database():
    """Inicializa o banco de dados no Render"""
    print("🚀 Inicializando banco de dados no Render...")
    
    # Verifica se a variável DATABASE_URL está definida
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ Erro: Variável DATABASE_URL não está definida!")
        print("Configure a variável DATABASE_URL no Render com a string de conexão do PostgreSQL")
        sys.exit(1)
    
    print(f"📊 Conectando ao banco: {database_url[:50]}...")
    
    try:
        # Importa e cria a aplicação
        from src.main import create_app
        from src.models.user import db
        
        app = create_app("production")
        
        with app.app_context():
            print("📊 Entrando no contexto da aplicação...")
            
            # Testa a conexão primeiro
            try:
                db.engine.execute("SELECT 1")
                print("✅ Conexão com banco de dados estabelecida!")
            except Exception as conn_error:
                print(f"❌ Erro de conexão com banco: {conn_error}")
                raise
            
            print("📊 Criando todas as tabelas...")
            # db.create_all() # Comentar para evitar recriação em cada deploy
            # print("✅ Tabelas criadas (ou já existentes)!")
            
            # Verifica se existem dados
            from src.models.user import User
            user_count = User.query.count()
            print(f"Contagem inicial de usuários: {user_count}")
            
            if user_count == 0:
                print("📦 Banco vazio. Tentando migrar dados do SQLite ou criar dados padrão...")
                
                # Tenta migrar dados do SQLite
                try:
                    from src.migrate_to_postgres import migrate_data
                    print("Attempting data migration from SQLite...")
                    migrate_data()
                    print("Data migration completed.")
                except ImportError:
                    print("src.migrate_to_postgres not found, skipping migration.")
                except Exception as e:
                    print(f"⚠️ Erro na migração (criando dados padrão): {e}")
                    
                # Se a migração falhar ou não existir, cria dados padrão
                from src.main import init_default_data
                print("Chamando init_default_data()...")
                init_default_data()
                print("init_default_data() concluído.")
            else:
                print(f"✅ Banco já contém {user_count} usuários. Pulando inicialização de dados padrão.")
                
            print("🎉 Inicialização do banco concluída!")
            
    except Exception as e:
        print(f"❌ Erro fatal ao inicializar banco: {e}")
        print("Verifique se:")
        print("1. A variável DATABASE_URL está corretamente configurada")
        print("2. O banco PostgreSQL está acessível")
        print("3. As credenciais estão corretas")
        sys.exit(1)

if __name__ == "__main__":
    init_render_database()


