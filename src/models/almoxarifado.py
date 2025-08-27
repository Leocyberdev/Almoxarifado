from src.models.user import db
from datetime import datetime

# Definir o fuso horário para São Paulo
# SAO_PAULO_TZ = timezone("America/Sao_Paulo")

class Fornecedor(db.Model):
    __tablename__ = 'fornecedores'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Fornecedor {self.nome}>'

    def to_dict(self):
        # Contar produtos usando este fornecedor
        total_produtos = Produto.query.filter_by(fornecedor=self.nome, ativo=True).count()

        return {
            'id': self.id,
            'nome': self.nome,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'total_produtos': total_produtos
        }

class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Categoria {self.nome}>'

    def to_dict(self):
        # Contar produtos usando esta categoria
        total_produtos = Produto.query.filter_by(categoria=self.nome, ativo=True).count()

        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ativa': self.ativo,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'total_produtos': total_produtos
        }

class Produto(db.Model):
    __tablename__ = 'produtos'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    fornecedor = db.Column(db.String(200))
    categoria = db.Column(db.String(20), nullable=False)  # Curva A, B, C
    local_produto = db.Column(db.String(100))
    unidade_medida = db.Column(db.String(20), default='unidade')
    preco = db.Column(db.Float, default=0.0)
    quantidade_estoque = db.Column(db.Float, default=0.0)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    # Relacionamentos
    movimentacoes = db.relationship('Movimentacao', backref='produto', lazy=True)

    def __repr__(self):
        return f'<Produto {self.codigo} - {self.nome}>'

    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nome': self.nome,
            'descricao': self.descricao,
            'fornecedor': self.fornecedor,
            'categoria': self.categoria,
            'local_produto': self.local_produto,
            'unidade_medida': self.unidade_medida,
            'preco': self.preco,
            'quantidade_estoque': self.quantidade_estoque,
            'data_cadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
            'ativo': self.ativo
        }

class Local(db.Model):
    __tablename__ = 'locais'

    id = db.Column(db.Integer, primary_key=True)
    nome_local = db.Column(db.String(100), unique=True, nullable=False)  # Ex: Rua 4
    posicao = db.Column(db.String(50), nullable=True)  # Ex: 1.5, 2-A, 3.2-B (números, pontos e hífens)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Local {self.nome_local}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome_local': self.nome_local,
            'posicao': self.posicao,
            'descricao': self.descricao,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None
        }


class Obra(db.Model):
    __tablename__ = 'obras'

    id = db.Column(db.Integer, primary_key=True)
    numero_obra = db.Column(db.String(50), unique=True, nullable=False)
    nome_obra = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    ativa = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(50), default='Prevista')  # Prevista, Em Andamento, Pausada, Entregue
    data_entrega = db.Column(db.DateTime, nullable=True)

    # Relacionamentos
    movimentacoes = db.relationship('Movimentacao', backref='obra', lazy=True)

    def __repr__(self):
        return f'<Obra {self.numero_obra} - {self.nome_obra}>'

    def to_dict(self):
        return {
            'id': self.id,
            'numero_obra': self.numero_obra,
            'nome_obra': self.nome_obra,
            'descricao': self.descricao,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'ativa': self.ativa,
            'status': self.status,
            'data_entrega': self.data_entrega.isoformat() if self.data_entrega else None
        }

class Funcionario(db.Model):
    __tablename__ = 'funcionarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cargo = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)

    # Relacionamentos
    movimentacoes = db.relationship('Movimentacao', backref='funcionario', lazy=True)

    def __repr__(self):
        return f'<Funcionario {self.nome}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'cargo': self.cargo,
            'ativo': self.ativo
        }

class Requisicao(db.Model):
    __tablename__ = 'requisicoes'

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'), nullable=False)
    usuario_id = db.Column(db.Integer, nullable=False)  # ID do usuário que fez a requisição
    quantidade_solicitada = db.Column(db.Float, nullable=False)
    quantidade_atendida = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, ATENDIDA, PARCIAL, CANCELADA
    data_requisicao = db.Column(db.DateTime, default=lambda: datetime.now(SAO_PAULO_TZ))
    data_atendimento = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text)
    observacoes_atendimento = db.Column(db.Text)
    atendido_por = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)

    # Relacionamentos
    produto = db.relationship('Produto', backref='requisicoes')
    obra = db.relationship('Obra', backref='requisicoes')
    funcionario_atendente = db.relationship('Funcionario', backref='requisicoes_atendidas')

    def __repr__(self):
        return f'<Requisicao {self.id} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'produto_id': self.produto_id,
            'obra_id': self.obra_id,
            'usuario_id': self.usuario_id,
            'quantidade_solicitada': self.quantidade_solicitada,
            'quantidade_atendida': self.quantidade_atendida,
            'status': self.status,
            'data_requisicao': self.data_requisicao.isoformat() if self.data_requisicao else None,
            'data_atendimento': self.data_atendimento.isoformat() if self.data_atendimento else None,
            'observacoes': self.observacoes,
            'observacoes_atendimento': self.observacoes_atendimento,
            'produto': self.produto.to_dict() if self.produto else None,
            'obra': self.obra.to_dict() if self.obra else None,
            'funcionario_atendente': self.funcionario_atendente.to_dict() if self.funcionario_atendente else None
        }

class Movimentacao(db.Model):
    __tablename__ = 'movimentacoes'

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'), nullable=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    tipo_movimentacao = db.Column(db.String(20), nullable=False)  # ENTRADA, SAIDA, ALOCACAO
    quantidade = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f'<Movimentacao {self.tipo_movimentacao} - {self.quantidade}>'

    def to_dict(self):
        produto_dict = None
        if self.produto:
            produto_dict = self.produto.to_dict()
            # Garantir que unidade_medida esteja sempre presente
            if 'unidade_medida' not in produto_dict or not produto_dict['unidade_medida']:
                produto_dict['unidade_medida'] = 'unidade'

        # Obter informações do funcionário ou usuário
        funcionario_dict = None
        if self.funcionario:
            funcionario_dict = self.funcionario.to_dict()
        else:
            # Se não há funcionário cadastrado, mostrar informação do usuário do sistema
            funcionario_dict = {
                'id': self.funcionario_id,
                'nome': 'Usuário do Sistema',
                'cargo': 'Operador',
                'ativo': True
            }

        return {
            'id': self.id,
            'produto_id': self.produto_id,
            'obra_id': self.obra_id,
            'funcionario_id': self.funcionario_id,
            'tipo_movimentacao': self.tipo_movimentacao,
            'quantidade': self.quantidade,
            'valor_unitario': self.valor_unitario,
            'valor_total': self.valor_total,
            'data_movimentacao': self.data_movimentacao.isoformat() if self.data_movimentacao else None,
            'observacoes': self.observacoes,
            'produto': produto_dict,
            'obra': self.obra.to_dict() if self.obra else None,
            'funcionario': funcionario_dict
        }
