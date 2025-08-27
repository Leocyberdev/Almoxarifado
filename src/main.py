import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template, session, redirect
from flask_cors import CORS
from flask.cli import with_appcontext

from src.models.user import db, User
from src.models.almoxarifado import Produto, Obra, Funcionario, Movimentacao, Categoria, Fornecedor
from src.routes.user import user_bp, login_required
from src.routes.almoxarifado import almoxarifado_bp
from src.config import config


def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))

    # Carrega configuração baseada no ambiente
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Ajustes para conexões de banco mais confiáveis (Postgres / Render)
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
    app.config["SQLALCHEMY_ENGINE_OPTIONS"].update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30
    })

    # Configuração CORS
    CORS(app)

    # Registra blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(almoxarifado_bp)

    # Inicializa banco de dados
    db.init_app(app)

    # Flag para garantir que as inicializações ocorram apenas uma vez
    db_initialized = {"done": False}

    @app.before_request
    def initialize_database():
        # Usa um lock (dicionário) para garantir que o código rode apenas uma vez
        if not db_initialized["done"]:
            with app.app_context():
                # 🚨 Reset temporário do banco (dropar e recriar)
                print("Iniciando reset do banco de dados...")
                # db.drop_all() # Comentar para evitar reset do banco em cada inicialização
                # print("✅ Tabelas antigas removidas.")
                
                # db.create_all() # Comentar para evitar recriação em cada inicialização
                # print("✅ Novas tabelas criadas.")
                
                init_default_data()
                print("✅ Banco resetado e recriado com sucesso.")
            
            db_initialized["done"] = True

    # Rotas específicas (devem vir ANTES da rota catch-all)
    @app.route("/gerenciamento")
    @login_required
    def gerenciamento():
        return render_template("gerenciamento_obras.html")

    @app.route("/locais")
    @login_required
    def locais():
        try:
            return render_template("gerenciamento_locais.html")
        except Exception as e:
            print(f"Erro ao renderizar template gerenciamento_locais.html: {e}")
            return """
            <html>
            <head><title>Gerenciamento de Locais</title></head>
            <body>
            <h1>Gerenciamento de Locais</h1>
            <p>Página em desenvolvimento...</p>
            <a href="/">Voltar ao Dashboard</a>
            </body>
            </html>
            """, 200

    # Rota catch-all (vem por último)
    @app.route("/")
    @app.route("/<path:path>")
    @login_required
    def serve(path=None):
        user = User.query.get(session["user_id"])
        if user.tipo_usuario == "producao":
            return redirect("/producao")

        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)

        index_path = os.path.join(static_folder_path, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, "index.html")

        return "index.html not found", 404

    # Registra comandos customizados
    register_commands(app)

    return app


def register_commands(app):
    """Registra comandos customizados no flask CLI"""
    @app.cli.command("init-db")
    @with_appcontext
    def init_db():
        """Cria usuário admin master e funcionário padrão"""
        init_default_data()


def init_default_data():
    """Inicializa dados padrão no banco de dados"""
    try:
        # Usuário admin
        admin_user = User.query.filter_by(username="Monter").first()
        if not admin_user:
            admin_user = User(
                username="Monter",
                email="admin@sistema.com",
                tipo_usuario="almoxarifado",
                ativo=True
            )
            admin_user.set_password("almox")
            db.session.add(admin_user)
            print("✅ Usuário admin master criado: Monter / almox")





        db.session.commit()
        print("✅ Dados padrão inicializados com sucesso")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao inicializar dados padrão: {e}")
        raise


# Cria a aplicação
app = create_app()

# Inicialização do servidor
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") != "production"
    app.run(debug=debug, host="0.0.0.0", port=port)
    
