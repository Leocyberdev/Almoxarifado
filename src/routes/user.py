from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for
from src.models.user import User, db
from functools import wraps

user_bp = Blueprint("user", __name__)

# Decorator para verificar autenticação
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("user.login"))
        return f(*args, **kwargs)
    return decorated_function

# Decorator para verificar se é do almoxarifado
def almoxarifado_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("user.login"))
        
        user = User.query.get(session["user_id"])
        if not user or user.tipo_usuario != "almoxarifado":
            return jsonify({"error": "Acesso negado - Apenas usuários do almoxarifado"}), 403
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route("/login")
def login():
    """Página de login"""
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user and user.tipo_usuario == "almoxarifado":
            return redirect("/")
        elif user and user.tipo_usuario == "producao":
            return redirect("/producao")
    return render_template("login.html")

@user_bp.route("/api/login", methods=["POST"])
def login_post():
    """Processar login"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        print(f"Attempting login for username: {username}") # Log de depuração

        user = User.query.filter_by(username=username, ativo=True).first()
        
        if user:
            session["user_id"] = user.id
            session["username"] = user.username
            session["tipo_usuario"] = user.tipo_usuario
            
            redirect_url = "/" if user.tipo_usuario == "almoxarifado" else "/producao"
            
            print(f"Login successful for {username}. Redirecting to {redirect_url}") # Log de depuração
            return jsonify({
                "success": True,
                "message": "Login realizado com sucesso",
                "redirect": redirect_url,
                "user": user.to_dict()
            })
        else:
            print(f"Login failed for {username}. Invalid credentials.") # Log de depuração
            return jsonify({
                "success": False,
                "message": "Usuário ou senha incorretos"
            }), 401
            
    except Exception as e:
        print(f"Error during login: {e}") # Log de depuração
        return jsonify({"error": str(e)}), 500

@user_bp.route("/logout")
def logout():
    """Logout do usuário"""
    session.clear()
    return redirect(url_for("user.login"))

@user_bp.route("/producao")
@login_required
def producao_dashboard():
    """Dashboard da produção - acesso restrito apenas para usuários de produção"""
    user = User.query.get(session["user_id"])
    if user.tipo_usuario != "producao":
        return redirect("/login")
    return render_template("producao_dashboard.html")

@user_bp.route("/gerenciamento-usuarios")
def gerenciamento_usuarios():
    """Página de gerenciamento de usuários - apenas almoxarifado"""
    return render_template("gerenciamento_usuarios.html")

# APIs para usuários
@user_bp.route("/api/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route("/api/users", methods=["POST"])
def create_user():
    try:
        data = request.json
        
        # Verificar se usuário já existe
        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"error": "Usuário já existe"}), 400
        
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email já existe"}), 400
        
        user = User(
            username=data["username"],
            email=data["email"],
            tipo_usuario=data.get("tipo_usuario", "almoxarifado")
        )
        user.set_password(data["password"])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            "message": "Usuário criado com sucesso",
            "user": user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        user.username = data.get("username", user.username)
        user.email = data.get("email", user.email)
        user.tipo_usuario = data.get("tipo_usuario", user.tipo_usuario)
        user.ativo = data.get("ativo", user.ativo)
        
        if "password" in data and data["password"]:
            user.set_password(data["password"])
        
        db.session.commit()
        return jsonify(user.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        user.ativo = False
        db.session.commit()
        return jsonify({"message": "Usuário desativado com sucesso"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/users/<int:user_id>/delete", methods=["DELETE"])
def permanent_delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # Verificar se não é o próprio usuário logado
        if user.id == session["user_id"]:
            return jsonify({"error": "Não é possível excluir o próprio usuário"}), 403
        
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "Usuário excluído permanentemente"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/users/<int:user_id>/alterar-senha", methods=["POST"])
def admin_alterar_senha(user_id):
    """Alterar senha de qualquer usuário (apenas almoxarifado)"""
    try:
        data = request.get_json()
        nova_senha = data.get("nova_senha")
        
        if not nova_senha:
            return jsonify({"error": "Nova senha é obrigatória"}), 400
        
        if len(nova_senha) < 6:
            return jsonify({"error": "A senha deve ter pelo menos 6 caracteres"}), 400
        
        user = User.query.get_or_404(user_id)
        
        # Atualizar senha
        user.set_password(nova_senha)
        db.session.commit()
        
        return jsonify({"message": "Senha alterada com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/current")
@login_required
def get_current_user():
    """Retorna dados do usuário atual"""
    try:
        user = User.query.get(session["user_id"])
        if user:
            return jsonify(user.to_dict())
        else:
            return jsonify({"error": "Usuário não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/alterar-senha", methods=["POST"])
def alterar_senha():
    """Alterar senha do usuário atual"""
    try:
        data = request.get_json()
        senha_atual = data.get("senha_atual")
        nova_senha = data.get("nova_senha")
        
        if not senha_atual or not nova_senha:
            return jsonify({"error": "Senha atual e nova senha são obrigatórias"}), 400
        
        user = User.query.get(session["user_id"])
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        # Atualizar senha
        user.set_password(nova_senha)
        db.session.commit()
        
        return jsonify({"message": "Senha alterada com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


