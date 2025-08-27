import os
from urllib.parse import quote_plus

class Config:
    """Configuração base"""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "asdf#FGSgvasgf$5$WGT"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or "admin_default_password" # Senha padrão para operações administrativas
    
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento - usa SQLite"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or \
        f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"


class ProductionConfig(Config):
    """Configuração para produção - usa PostgreSQL"""
    DEBUG = False

    raw_url = os.environ.get("DATABASE_URL")

    if raw_url:
        # Render geralmente fornece 'postgres://', mas o SQLAlchemy precisa de 'postgresql+psycopg2://'
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif raw_url.startswith("postgresql://"):
            raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

        SQLALCHEMY_DATABASE_URI = raw_url
    else:
        # Se não tiver DATABASE_URL, interrompe a inicialização
        raise RuntimeError(
            "❌ A variável de ambiente DATABASE_URL não está configurada no ambiente de produção!"
        )


class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Dicionário de configurações
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
