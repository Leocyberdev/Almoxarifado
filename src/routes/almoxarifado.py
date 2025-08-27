from flask import Blueprint, render_template, request, jsonify, make_response, current_app
from src.models.user import db
from src.models.almoxarifado import (
    Produto, Categoria, Fornecedor,
    Movimentacao, Obra, Local, Funcionario, db
)
from src.routes.user import login_required
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from src.config import Config

almoxarifado_bp = Blueprint("almoxarifado", __name__)

# ===== FUNÇÃO AUXILIAR PARA FUNCIONÁRIO =====
def get_funcionario_id(user=None):
    """Retorna o ID do funcionário correspondente ao usuário ou o 'Sistema' como fallback."""
    funcionario_id = None

    if user:
        funcionario = Funcionario.query.filter_by(nome=user.username, ativo=True).first()
        if funcionario:
            return funcionario.id

    # Se não encontrou, usar/garantir o funcionário "Sistema"
    funcionario_sistema = Funcionario.query.filter_by(nome='Sistema', ativo=True).first()
    if not funcionario_sistema:
        funcionario_sistema = Funcionario(
            nome='Sistema',
            cargo='Sistema',
            ativo=True
        )
        db.session.add(funcionario_sistema)
        db.session.flush()  # pega o id sem commit

    return funcionario_sistema.id

# ===== ROTAS PARA PÁGINAS =====

@almoxarifado_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@almoxarifado_bp.route('/fornecedores')
def fornecedores():
    return render_template('fornecedores.html')

@almoxarifado_bp.route('/categorias')
def categorias():
    return render_template('categorias.html')

@almoxarifado_bp.route('/produtos/cadastro')
def cadastro_produtos():
    return render_template('cadastro_produtos.html')

@almoxarifado_bp.route("/estoque")
def estoque():
    return render_template('estoque.html')

@almoxarifado_bp.route('/produtos/alocar')
def alocar_produtos():
    return render_template('alocar_produtos.html')

@almoxarifado_bp.route("/gerenciamento")
def gerenciamento_obras():
    return render_template("gerenciamento_obras.html")

@almoxarifado_bp.route('/historico')
def historico():
    return render_template('historico.html')

@almoxarifado_bp.route('/estatisticas')
def estatisticas():
    return render_template('estatisticas.html')

@almoxarifado_bp.route('/requisicoes')
@login_required
def requisicoes():
    return render_template('requisicoes.html')



# ===== API ENDPOINTS =====

# Dashboard APIs
@almoxarifado_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """Estatísticas para o dashboard"""
    try:
        # Últimas 10 movimentações
        ultimas_movimentacoes = db.session.query(Movimentacao).order_by(desc(Movimentacao.data_movimentacao)).limit(10).all()

        # Total economizado no mês atual
        inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        economia_mes = db.session.query(func.sum(Movimentacao.valor_total)).filter(
            and_(Movimentacao.data_movimentacao >= inicio_mes,
                 Movimentacao.tipo_movimentacao == 'ALOCACAO')
        ).scalar() or 0

        # Produtos mais movimentados (últimos 30 dias)
        data_limite = datetime.now() - timedelta(days=30)
        produtos_movimentados = db.session.query(
            Produto.nome,
            Produto.unidade_medida,
            func.sum(Movimentacao.quantidade).label('total_quantidade')
        ).join(Movimentacao).filter(
            Movimentacao.data_movimentacao >= data_limite
        ).group_by(Produto.id).order_by(desc('total_quantidade')).limit(5).all()

        # Resumo por categoria
        resumo_categorias = db.session.query(
            Produto.categoria,
            func.count(Produto.id).label('total_produtos'),
            func.sum(Produto.quantidade_estoque).label('total_estoque')
        ).filter(Produto.ativo == True).group_by(Produto.categoria).all()

        # Processar movimentações para garantir dados corretos do funcionário
        movimentacoes_processadas = []
        for mov in ultimas_movimentacoes:
            mov_dict = mov.to_dict()
            # Se o funcionário for "Sistema", tentar buscar o usuário real baseado no ID da sessão
            if mov.funcionario and mov.funcionario.nome == 'Sistema':
                # Manter "Sistema" se realmente foi uma operação automática
                pass
            movimentacoes_processadas.append(mov_dict)

        return jsonify({
            'ultimas_movimentacoes': movimentacoes_processadas,
            'economia_mes': float(economia_mes),
            'produtos_movimentados': [{'nome': p[0], 'unidade_medida': p[1], 'quantidade': int(p[2])} for p in produtos_movimentados],
            'resumo_categorias': [{'categoria': r[0], 'produtos': int(r[1]), 'estoque': int(r[2])} for r in resumo_categorias]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Produtos APIs
@almoxarifado_bp.route('/api/produtos', methods=['GET'])
def listar_produtos():
    """Listar produtos com filtros"""
    try:
        categoria = request.args.get("categoria")
        fornecedor = request.args.get("fornecedor")
        busca = request.args.get("busca")
        status = request.args.get("status")
        para_alocacao = request.args.get("para_alocacao", "false").lower() == "true"

        # Base query - se status não especificado, mostra apenas ativos (comportamento padrão)
        if para_alocacao:
            query = Produto.query
        elif status == "inativo":
            query = Produto.query.filter(Produto.ativo == False)
        elif status == 'ativo':
            query = Produto.query.filter(Produto.ativo == True)
        elif status == '':
            # Quando status vazio, mostrar todos (ativo e inativo)
            query = Produto.query
        else:
            # Comportamento padrão - apenas ativos
            query = Produto.query.filter(Produto.ativo == True)

        if categoria:
            query = query.filter(Produto.categoria.ilike(f'%{categoria}%'))
        if fornecedor:
            query = query.filter(Produto.fornecedor.ilike(f'%{fornecedor}%'))
        if busca:
            query = query.filter(
                db.or_(
                    Produto.nome.ilike(f'%{busca}%'),
                    Produto.codigo.ilike(f'%{busca}%'),
                    Produto.descricao.ilike(f'%{busca}%')
                )
            )

        produtos = query.all()
        return jsonify([produto.to_dict() for produto in produtos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/produtos', methods=['POST'])
def criar_produto():
    """Criar novo produto"""
    try:
        data = request.get_json()

        # Verificar se código já existe
        if Produto.query.filter_by(codigo=data['codigo']).first():
            return jsonify({'error': 'Código já existe'}), 400

        # Buscar informações do local se ID foi fornecido
        local_texto = ''
        if data.get('local_produto_id'):
            local = Local.query.get(data['local_produto_id'])
            if local:
                local_texto = f"{local.nome_local} - {local.posicao}" if local.posicao else local.nome_local

        produto = Produto(
            codigo=data['codigo'],
            nome=data['nome'],
            descricao=data.get('descricao', ''),
            fornecedor=data.get('fornecedor', ''),
            categoria=data['categoria'],
            local_produto=local_texto,
            unidade_medida=data.get('unidade_medida', 'unidade'),
            preco=float(data.get('preco', 0)),
            quantidade_estoque=float(data.get('quantidade_estoque', 0))
        )

        db.session.add(produto)
        db.session.commit()

        return jsonify(produto.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/produtos/<int:produto_id>', methods=['PUT'])
def editar_produto(produto_id):
    """Editar produto (requer senha)"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get('senha') != ADMIN_PASSWORD:
            return jsonify({'error': 'Senha incorreta'}), 401

        produto = Produto.query.get_or_404(produto_id)

        produto.nome = data.get('nome', produto.nome)
        produto.descricao = data.get('descricao', produto.descricao)
        produto.fornecedor = data.get('fornecedor', produto.fornecedor)
        produto.categoria = data.get('categoria', produto.categoria)
        produto.local_produto = data.get('local_produto', produto.local_produto)
        produto.preco = float(data.get('preco', produto.preco))

        # Atualizar status ativo/inativo
        if 'ativo' in data:
            produto.ativo = bool(data.get('ativo'))

        db.session.commit()
        return jsonify(produto.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/produtos/<int:produto_id>', methods=['DELETE'])
def excluir_produto(produto_id):
    """Excluir produto (requer senha)"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get('senha') != ADMIN_PASSWORD:
            return jsonify({'error': 'Senha incorreta'}), 401

        produto = Produto.query.get_or_404(produto_id)

        # Verificar se o produto tem movimentações/alocações
        movimentacoes = Movimentacao.query.filter_by(produto_id=produto_id).count()
        if movimentacoes > 0:
            return jsonify({
                'error': f'Não é possível excluir este produto. Ele possui {movimentacoes} movimentação(ões) registrada(s). Produtos com histórico de movimentações não podem ser excluídos por segurança.'
            }), 400

        produto.ativo = False

        db.session.commit()
        return jsonify({'message': 'Produto excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/produtos/<int:produto_id>/saldo', methods=['POST'])
def gerenciar_saldo(produto_id):
    """Adicionar ou retirar saldo (requer senha)"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get('senha') != ADMIN_PASSWORD:
            return jsonify({'error': 'Senha incorreta'}), 401

        produto = Produto.query.get_or_404(produto_id)
        operacao = data.get('operacao')  # 'adicionar' ou 'retirar'
        quantidade = int(data.get('quantidade', 0))

        if operacao == 'adicionar':
            produto.quantidade_estoque += quantidade
        elif operacao == 'retirar':
            if produto.quantidade_estoque < quantidade:
                return jsonify({'error': 'Estoque insuficiente'}), 400
            produto.quantidade_estoque -= quantidade
        else:
            return jsonify({'error': 'Operação inválida'}), 400

        # Registrar movimentação - usar usuário logado
        from flask import session
        user_id = session.get('user_id')
        funcionario_id = 1  # padrão

        if user_id:
            from src.models.user import User
            user = User.query.get(user_id)
            if user:
                # Buscar funcionário com o mesmo nome do usuário (busca exata)
                funcionario = Funcionario.query.filter_by(nome=user.username, ativo=True).first()
                if not funcionario:
                    # Se não encontrar, criar funcionário automaticamente
                    funcionario = Funcionario(
                        nome=user.username,
                        cargo='Almoxarifado',
                        ativo=True
                    )
                    db.session.add(funcionario)
                    db.session.flush()  # Para obter o ID sem fazer commit

                funcionario_id = funcionario.id

        movimentacao = Movimentacao(
            produto_id=produto.id,
            funcionario_id=funcionario_id,
            tipo_movimentacao='ENTRADA' if operacao == 'adicionar' else 'SAIDA',
            quantidade=quantidade,
            valor_unitario=produto.preco,
            valor_total=produto.preco * quantidade,
            observacoes=f'Ajuste de estoque - {operacao}'
        )

        db.session.add(movimentacao)
        db.session.commit()

        return jsonify(produto.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Obras APIs
@almoxarifado_bp.route('/api/obras', methods=['GET'])
def listar_obras():
    """Listar obras com filtros e produtos alocados"""
    try:
        status = request.args.get("status")
        busca = request.args.get("busca")
        para_alocacao = request.args.get("para_alocacao", "false").lower() == "true"

        query = Obra.query.filter_by(ativa=True)

        # Se for para alocação, excluir obras entregues
        if para_alocacao:
            query = query.filter(Obra.status != 'Entregue')

        if busca:
            query = query.filter(
                db.or_(
                    Obra.nome_obra.ilike(f"%{busca}%"),
                    Obra.numero_obra.ilike(f"%{busca}%")
                )
            )
        elif status:
            query = query.filter_by(status=status)
        obras = query.order_by(desc(Obra.id)).all()

        obras_com_produtos = []
        for obra in obras:
            movimentacoes_obra = Movimentacao.query.filter_by(obra_id=obra.id).all()
            produtos_alocados = []
            for mov in movimentacoes_obra:
                produto_info = mov.produto.to_dict()
                produto_info["quantidade_alocada"] = mov.quantidade
                produtos_alocados.append(produto_info)

            obra_dict = obra.to_dict()
            obra_dict["produtos_alocados"] = produtos_alocados
            obras_com_produtos.append(obra_dict)

        return jsonify(obras_com_produtos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@almoxarifado_bp.route('/api/obras/sugestoes')
def sugestoes_obras():
    """Retorna sugestões de obras baseadas no termo de busca"""
    try:
        termo = request.args.get('termo', '')

        if len(termo) < 1:
            return jsonify([])

        # Buscar obras que não estão entregues
        obras = Obra.query.filter(
            db.and_(
                Obra.ativa == True,
                Obra.status != 'Entregue',
                db.or_(
                    Obra.numero_obra.ilike(f'%{termo}%'),
                    Obra.nome_obra.ilike(f'%{termo}%')
                )
            )
        ).limit(10).all()

        return jsonify([{
            'id': obra.id,
            'numero_obra': obra.numero_obra,
            'nome_obra': obra.nome_obra
        } for obra in obras])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Alocação APIs
# (Substitua a função alocar_produto() existente por esta versão mais segura)

@almoxarifado_bp.route('/api/alocar', methods=['POST'])
def alocar_produto():
    """Alocar produto em obra com validação estrita de funcionário."""
    try:
        data = request.get_json()

        produto = Produto.query.get_or_404(data['produto_id'])
        obra = Obra.query.get_or_404(data['obra_id'])
        quantidade = int(data['quantidade'])

        # 1. Verificar estoque antes de qualquer outra coisa
        if produto.quantidade_estoque < quantidade:
            return jsonify({
                'error': 'Estoque insuficiente',
                'disponivel': produto.quantidade_estoque
            }), 400

        # --- LÓGICA DE VALIDAÇÃO DE FUNCIONÁRIO (SEM CRIAÇÃO AUTOMÁTICA) ---
        from flask import session
        from src.models.user import User
        
        funcionario_id = None
        user_id = session.get('user_id')

        if user_id:
            user = User.query.get(user_id)
            if user:
                # 2. Busca um funcionário ATIVO que corresponda ao nome do usuário logado
                funcionario = Funcionario.query.filter_by(nome=user.username, ativo=True).first()
                
                # 3. VALIDAÇÃO: Se não encontrar um funcionário válido, interrompe a operação
                if not funcionario:
                    return jsonify({
                        'error': f'Operação não permitida. O usuário "{user.username}" não está vinculado a um funcionário ativo no sistema. Contate o administrador.'
                    }), 403  # 403 Forbidden é um código de status apropriado aqui

                funcionario_id = funcionario.id
            else:
                # Caso raro: user_id na sessão é inválido
                 return jsonify({'error': 'Sessão de usuário inválida. Por favor, faça login novamente.'}), 401
        
        # 4. Se não houver um ID de funcionário (ex: user_id não encontrado na sessão), a operação falha.
        if not funcionario_id:
            return jsonify({'error': 'Não foi possível identificar o funcionário responsável. Acesso negado.'}), 401

        # --- FIM DA LÓGICA DE VALIDAÇÃO ---

        # Atualizar estoque
        produto.quantidade_estoque -= quantidade

        # Registrar movimentação
        movimentacao = Movimentacao(
            produto_id=produto.id,
            obra_id=obra.id,
            funcionario_id=funcionario_id,  # ID garantido como válido e ativo
            tipo_movimentacao='ALOCACAO',
            quantidade=quantidade,
            valor_unitario=produto.preco,
            valor_total=produto.preco * quantidade,
            observacoes=data.get('observacoes', '')
        )

        db.session.add(movimentacao)
        db.session.commit()

        return jsonify({
            'message': 'Produto alocado com sucesso',
            'movimentacao': movimentacao.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        print(f"ERRO AO ALOCAR PRODUTO: {e}") 
        return jsonify({'error': str(e)}), 500


# Histórico APIs
@almoxarifado_bp.route('/api/historico')
def historico_movimentacoes():
    """Histórico de movimentações com filtros"""
    try:
        periodo = request.args.get('periodo', 'mes')  # dia, semana, mes
        funcionario = request.args.get('funcionario')
        produto = request.args.get('produto')
        obra = request.args.get('obra')

        # Calcular data limite baseada no período
        agora = datetime.now()
        if periodo == 'dia':
            data_limite = agora - timedelta(days=1)
        elif periodo == 'semana':
            data_limite = agora - timedelta(weeks=1)
        else:  # mes
            data_limite = agora - timedelta(days=30)

        query = Movimentacao.query.filter(Movimentacao.data_movimentacao >= data_limite)

        if funcionario:
            query = query.join(Funcionario).filter(Funcionario.nome.ilike(f'%{funcionario}%'))
        if produto:
            query = query.join(Produto).filter(Produto.codigo.ilike(f'%{produto}%'))
        if obra:
            query = query.join(Obra).filter(Obra.numero_obra.ilike(f'%{obra}%'))

        movimentacoes = query.order_by(desc(Movimentacao.data_movimentacao)).limit(50).all()

        # Incluir informações completas do produto incluindo unidade_medida
        resultado = []
        for mov in movimentacoes:
            mov_dict = mov.to_dict()
            # Garantir que as informações do produto incluam unidade_medida
            if mov.produto:
                mov_dict['produto']['unidade_medida'] = mov.produto.unidade_medida
            resultado.append(mov_dict)

        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Estatísticas APIs
@almoxarifado_bp.route('/api/estatisticas/geral')
def estatisticas_gerais():
    """Estatísticas gerais com filtros de período"""
    try:
        # Obter parâmetros
        periodo = request.args.get('periodo', 'mes')
        data_inicio_param = request.args.get('data_inicio')
        data_fim_param = request.args.get('data_fim')

        # Calcular datas baseadas no período
        agora = datetime.now()

        if data_inicio_param and data_fim_param:
            # Período customizado
            data_inicio = datetime.strptime(data_inicio_param, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim_param, '%Y-%m-%d') + timedelta(days=1)  # Incluir o dia inteiro
        else:
            # Períodos predefinidos
            if periodo == 'dia':
                data_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
            elif periodo == 'semana':
                data_inicio = agora - timedelta(weeks=1)
            elif periodo == 'mes':
                data_inicio = agora - timedelta(days=30)
            elif periodo == 'ano':
                data_inicio = agora - timedelta(days=365)
            else:  # total
                data_inicio = datetime(2020, 1, 1)  # Data muito antiga para pegar tudo

            data_fim = agora

        # Query base de movimentações de alocação no período
        query_base = Movimentacao.query.filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO',
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        )

        # Estatísticas básicas
        movimentacoes = query_base.all()
        total_alocacoes = len(movimentacoes)
        economia_total = sum(mov.valor_total for mov in movimentacoes)

        # Produtos mais usados
        produtos_mais_usados = db.session.query(
            Produto.codigo,
            Produto.nome,
            Produto.categoria,
            func.sum(Movimentacao.quantidade).label('quantidade'),
            func.sum(Movimentacao.valor_total).label('valor'),
            func.max(Movimentacao.data_movimentacao).label('ultima_alocacao')
        ).join(Movimentacao).filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO',
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        ).group_by(Produto.id).order_by(desc('quantidade')).limit(10).all()

        # Ranking de funcionários
        ranking_funcionarios = db.session.query(
            Funcionario.nome,
            func.count(Movimentacao.id).label('movimentacoes'),
            func.sum(Movimentacao.valor_total).label('valor')
        ).join(Movimentacao).filter(
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        ).group_by(Funcionario.id).order_by(desc('valor')).all()

        # Obras atendidas
        obras_atendidas = db.session.query(func.count(func.distinct(Movimentacao.obra_id))).filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO',
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        ).scalar() or 0

        # Produtos diferentes
        produtos_diferentes = db.session.query(func.count(func.distinct(Movimentacao.produto_id))).filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO',
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        ).scalar() or 0

        # Maior alocação e média
        maior_alocacao = db.session.query(func.max(Movimentacao.valor_total)).filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO',
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        ).scalar() or 0

        media_alocacao = economia_total / total_alocacoes if total_alocacoes > 0 else 0

        # Primeira e última movimentação
        primeira_mov = db.session.query(func.min(Movimentacao.data_movimentacao)).filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO',
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        ).scalar()

        ultima_mov = db.session.query(func.max(Movimentacao.data_movimentacao)).filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO',
            Movimentacao.data_movimentacao >= data_inicio,
            Movimentacao.data_movimentacao <= data_fim
        ).scalar()

        # Economia temporal (para gráfico)
        economia_temporal = []
        if periodo == 'dia':
            # Agrupar por hora
            for i in range(24):
                hora_inicio = data_inicio.replace(hour=i, minute=0, second=0, microsecond=0)
                hora_fim = hora_inicio + timedelta(hours=1)
                valor = db.session.query(func.sum(Movimentacao.valor_total)).filter(
                    Movimentacao.tipo_movimentacao == 'ALOCACAO',
                    Movimentacao.data_movimentacao >= hora_inicio,
                    Movimentacao.data_movimentacao < hora_fim
                ).scalar() or 0
                economia_temporal.append({
                    'periodo': f"{i:02d}:00",
                    'valor': float(valor)
                })
        elif periodo == 'semana':
            # Agrupar por dia
            for i in range(7):
                dia = data_inicio + timedelta(days=i)
                dia_inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
                dia_fim = dia_inicio + timedelta(days=1)
                valor = db.session.query(func.sum(Movimentacao.valor_total)).filter(
                    Movimentacao.tipo_movimentacao == 'ALOCACAO',
                    Movimentacao.data_movimentacao >= dia_inicio,
                    Movimentacao.data_movimentacao < dia_fim
                ).scalar() or 0
                economia_temporal.append({
                    'periodo': dia.strftime('%d/%m'),
                    'valor': float(valor)
                })
        else:
            # Agrupar por mês (últimos 12 meses)
            for i in range(12):
                mes_inicio = (agora.replace(day=1) - timedelta(days=30*i)).replace(day=1)
                mes_fim = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)

                valor = db.session.query(func.sum(Movimentacao.valor_total)).filter(
                    Movimentacao.tipo_movimentacao == 'ALOCACAO',
                    Movimentacao.data_movimentacao >= mes_inicio,
                    Movimentacao.data_movimentacao <= mes_fim
                ).scalar() or 0

                economia_temporal.append({
                    'periodo': mes_inicio.strftime('%m/%Y'),
                    'valor': float(valor)
                })

        # Reverter para ordem cronológica
        economia_temporal.reverse()

        return jsonify({
            'economia_total': float(economia_total),
            'total_alocacoes': total_alocacoes,
            'media_alocacao': float(media_alocacao),
            'maior_alocacao': float(maior_alocacao),
            'produtos_diferentes': produtos_diferentes,
            'obras_atendidas': obras_atendidas,
            'primeira_movimentacao': primeira_mov.isoformat() if primeira_mov else None,
            'ultima_movimentacao': ultima_mov.isoformat() if ultima_mov else None,
            'produtos_mais_usados': [{
                'codigo': p[0],
                'nome': p[1],
                'categoria': p[2],
                'quantidade': int(p[3]),
                'valor': float(p[4]),
                'ultima_alocacao': p[5].isoformat() if p[5] else None
            } for p in produtos_mais_usados],
            'ranking_funcionarios': [{
                'nome': f[0],
                'movimentacoes': int(f[1]),
                'valor': float(f[2]) if f[2] else 0
            } for f in ranking_funcionarios],
            'economia_temporal': economia_temporal
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/estatisticas/produtos-mais-usados')
def produtos_mais_usados():
    """Produtos mais utilizados"""
    try:
        data_limite = datetime.now() - timedelta(days=30)

        produtos = db.session.query(
            Produto.nome,
            Produto.codigo,
            func.sum(Movimentacao.quantidade).label('total_quantidade'),
            func.sum(Movimentacao.valor_total).label('total_valor')
        ).join(Movimentacao).filter(
            Movimentacao.data_movimentacao >= data_limite,
            Movimentacao.tipo_movimentacao == 'ALOCACAO'
        ).group_by(Produto.id).order_by(desc('total_quantidade')).limit(10).all()

        return jsonify([{
            'nome': p[0],
            'codigo': p[1],
            'quantidade': int(p[2]),
            'valor': float(p[3])
        } for p in produtos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/estatisticas/funcionarios')
def estatisticas_funcionarios():
    """Estatísticas por funcionário"""
    try:
        data_limite = datetime.now() - timedelta(days=30)

        funcionarios = db.session.query(
            Funcionario.nome,
            func.count(Movimentacao.id).label('total_movimentacoes'),
            func.sum(Movimentacao.valor_total).label('total_valor')
        ).join(Movimentacao).filter(
            Movimentacao.data_movimentacao >= data_limite
        ).group_by(Funcionario.id).order_by(desc('total_movimentacoes')).all()

        return jsonify([{
            'nome': f[0],
            'movimentacoes': int(f[1]),
            'valor': float(f[2]) if f[2] else 0
        } for f in funcionarios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/estatisticas/economia-total')
def economia_total():
    """Cálculo da economia total"""
    try:
        # Economia total (todas as alocações)
        economia_total = db.session.query(func.sum(Movimentacao.valor_total)).filter(
            Movimentacao.tipo_movimentacao == 'ALOCACAO'
        ).scalar() or 0

        # Economia por mês (últimos 12 meses)
        economia_mensal = []
        for i in range(12):
            data_inicio = (datetime.now().replace(day=1) - timedelta(days=30*i)).replace(day=1)
            data_fim = (data_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            valor = db.session.query(func.sum(Movimentacao.valor_total)).filter(
                and_(
                    Movimentacao.data_movimentacao >= data_inicio,
                    Movimentacao.data_movimentacao <= data_fim,
                    Movimentacao.tipo_movimentacao == 'ALOCACAO'
                )
            ).scalar() or 0

            economia_mensal.append({
                'mes': data_inicio.strftime('%Y-%m'),
                'valor': float(valor)
            })

        return jsonify({
            'economia_total': float(economia_total),
            'economia_mensal': list(reversed(economia_mensal))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# APIs para busca de locais
@almoxarifado_bp.route('/api/locais/busca')
def busca_locais():
    """Busca locais por termo"""
    try:
        termo = request.args.get('q', '').strip()
        if len(termo) < 1:
            return jsonify([])

        from src.models.almoxarifado import Local
        locais = Local.query.filter(
            db.or_(
                Local.nome_local.ilike(f'%{termo}%'),
                Local.posicao.ilike(f'%{termo}%')
            )
        ).limit(10).all()

        return jsonify([{
            'id': local.id,
            'nome_local': local.nome_local,
            'posicao': local.posicao,
            'descricao': local.descricao,
            'texto_completo': f"{local.nome_local} - {local.posicao}"
        } for local in locais])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/fornecedores/busca')
def busca_fornecedores():
    """Busca fornecedores por termo"""
    try:
        termo = request.args.get('q', '').strip()
        if len(termo) < 2:
            return jsonify([])

        fornecedores = Fornecedor.query.filter(
            and_(
                Fornecedor.ativo == True,
                Fornecedor.nome.ilike(f'%{termo}%')
            )
        ).limit(10).all()

        return jsonify([{
            'id': fornecedor.id,
            'nome': fornecedor.nome,
            'cnpj': fornecedor.cnpj,
            'contato': fornecedor.contato
        } for fornecedor in fornecedores])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Busca inteligente
@almoxarifado_bp.route('/api/busca/produtos')
def buscar_produtos():
    """Busca inteligente de produtos"""
    termo = request.args.get('q', '').strip()

    if len(termo) < 1:  # Reduzir para 1 caractere para melhor experiência
        return jsonify([])

    try:
        # Busca mais inteligente - priorizar busca por código exato primeiro
        produtos = Produto.query.filter(
            db.or_(
                Produto.codigo.ilike(f'{termo}%'),  # Código que começa com o termo
                Produto.codigo.ilike(f'%{termo}%'),  # Código que contém o termo
                Produto.nome.ilike(f'%{termo}%'),    # Nome que contém o termo
                Produto.descricao.ilike(f'%{termo}%')  # Descrição que contém o termo
            )
        ).order_by(
            # Priorizar: código exato, depois código que começa, depois nome
            db.case(
                (Produto.codigo.ilike(f'{termo}'), 1),
                (Produto.codigo.ilike(f'{termo}%'), 2),
                (Produto.nome.ilike(f'{termo}%'), 3),
                else_=4
            ),
            Produto.codigo
        ).limit(15).all()  # Aumentar limite para mais opções

        return jsonify([{
            'id': p.id,
            'codigo': p.codigo,
            'nome': p.nome,
            'categoria': p.categoria,
            'local_produto': p.local_produto,
            'estoque': p.quantidade_estoque,
            'preco': float(p.preco) if p.preco else 0.0,
            'quantidade_estoque': p.quantidade_estoque,
            'unidade_medida': p.unidade_medida,
            'ativo': p.ativo,
            'descricao': p.descricao
        } for p in produtos])

    except Exception as e:
        print(f"Erro na busca de produtos: {e}")
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/funcionarios')
def listar_funcionarios():
    """Listar funcionários ativos"""
    try:
        funcionarios = Funcionario.query.filter_by(ativo=True).all()
        return jsonify([func.to_dict() for func in funcionarios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/usuario-logado')
@login_required
def usuario_logado():
    """Obter informações do usuário logado"""
    try:
        from flask import session
        from src.models.user import User

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Usuário não logado'}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        # Buscar funcionário correspondente
        funcionario = Funcionario.query.filter(
            db.and_(
                Funcionario.ativo == True,
                db.or_(
                    Funcionario.nome == user.username,
                    Funcionario.nome.ilike(f'%{user.username}%')
                )
            )
        ).first()

        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'tipo_usuario': user.tipo_usuario,
            'funcionario_id': funcionario.id if funcionario else None,
            'funcionario_nome': funcionario.nome if funcionario else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/debug/funcionarios')
def debug_funcionarios():
    """Debug: Listar todos os funcionários para verificação"""
    try:
        funcionarios = Funcionario.query.all()
        return jsonify([{
            'id': f.id,
            'nome': f.nome,
            'cargo': f.cargo,
            'ativo': f.ativo
        } for f in funcionarios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Categorias APIs
@almoxarifado_bp.route('/api/categorias', methods=['GET'])
def listar_categorias():
    """Listar todas as categorias"""
    try:
        categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.nome).all()
        return jsonify([categoria.to_dict() for categoria in categorias])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/categorias', methods=['POST'])
def criar_categoria():
    """Criar nova categoria"""
    try:
        data = request.get_json()

        # Validar dados
        nome = data.get('nome', '').strip()
        if not nome:
            return jsonify({'error': 'Nome da categoria é obrigatório'}), 400

        # Verificar se categoria já existe (case insensitive)
        categoria_existente = Categoria.query.filter(
            func.lower(Categoria.nome) == func.lower(nome)
        ).first()

        if categoria_existente:
            return jsonify({'error': 'Categoria já existe'}), 400

        # Criar nova categoria
        categoria = Categoria(
            nome=nome,
            descricao=data.get('descricao', '').strip()
        )

        db.session.add(categoria)
        db.session.commit()

        return jsonify(categoria.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/categorias/<int:categoria_id>', methods=['PUT'])
def editar_categoria(categoria_id):
    """Editar categoria existente"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get('senha') != ADMIN_PASSWORD:
            return jsonify({'error': 'Senha incorreta'}), 401

        categoria = Categoria.query.get_or_404(categoria_id)

        # Validar nome
        nome = data.get('nome', '').strip()
        if not nome:
            return jsonify({'error': 'Nome da categoria é obrigatório'}), 400

        # Verificar se outro categoria já tem esse nome
        categoria_existente = Categoria.query.filter(
            and_(
                func.lower(Categoria.nome) == func.lower(nome),
                Categoria.id != categoria_id
            )
        ).first()

        if categoria_existente:
            return jsonify({'error': 'Já existe uma categoria com esse nome'}), 400

        # Atualizar categoria
        categoria.nome = nome
        categoria.descricao = data.get('descricao', '').strip()

        db.session.commit()
        return jsonify(categoria.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/categorias/<int:categoria_id>', methods=['DELETE'])
def excluir_categoria(categoria_id):
    """Excluir categoria (desativar)"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get('senha') != ADMIN_PASSWORD:
            return jsonify({'error': 'Senha incorreta'}), 401

        categoria = Categoria.query.get_or_404(categoria_id)

        # Verificar se há produtos usando esta categoria
        produtos_usando = Produto.query.filter_by(categoria=categoria.nome, ativo=True).count()
        if produtos_usando > 0:
            return jsonify({
                'error': f'Não é possível excluir. Existem {produtos_usando} produtos usando esta categoria.'
            }), 400

        # Desativar categoria
        categoria.ativa = False
        db.session.commit()

        return jsonify({'message': 'Categoria excluída com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/categorias/validar-nome')
def validar_nome_categoria():
    """Validar se nome da categoria já existe"""
    try:
        nome = request.args.get('nome', '').strip()
        categoria_id = request.args.get('id', type=int)

        if not nome:
            return jsonify({'valido': True})

        query = Categoria.query.filter(func.lower(Categoria.nome) == func.lower(nome))

        if categoria_id:
            query = query.filter(Categoria.id != categoria_id)

        categoria_existente = query.first()

        return jsonify({
            'valido': categoria_existente is None,
            'mensagem': 'Nome já existe' if categoria_existente else 'Nome disponível'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Fornecedores APIs
@almoxarifado_bp.route('/api/fornecedores', methods=['GET'])
def listar_fornecedores():
    """Listar todos os fornecedores"""
    try:
        fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
        return jsonify([fornecedor.to_dict() for fornecedor in fornecedores])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/fornecedores', methods=['POST'])
def criar_fornecedor():
    """Criar novo fornecedor"""
    try:
        data = request.get_json()

        # Validar dados
        nome = data.get('nome', '').strip()
        if not nome:
            return jsonify({'error': 'Nome do fornecedor é obrigatório'}), 400

        # Verificar se fornecedor já existe (case insensitive)
        fornecedor_existente = Fornecedor.query.filter(
            func.lower(Fornecedor.nome) == func.lower(nome)
        ).first()

        if fornecedor_existente:
            return jsonify({'error': 'Fornecedor já existe'}), 400

        # Criar novo fornecedor
        fornecedor = Fornecedor(nome=nome)

        db.session.add(fornecedor)
        db.session.commit()

        return jsonify(fornecedor.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/fornecedores/<int:fornecedor_id>', methods=['PUT'])
def editar_fornecedor(fornecedor_id):
    """Editar fornecedor existente"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get('senha') != ADMIN_PASSWORD:
            return jsonify({'error': 'Senha incorreta'}), 401

        fornecedor = Fornecedor.query.get_or_404(fornecedor_id)

        # Validar nome
        nome = data.get('nome', '').strip()
        if not nome:
            return jsonify({'error': 'Nome do fornecedor é obrigatório'}), 400

        # Verificar se outro fornecedor já tem esse nome
        fornecedor_existente = Fornecedor.query.filter(
            and_(
                func.lower(Fornecedor.nome) == func.lower(nome),
                Fornecedor.id != fornecedor_id
            )
        ).first()

        if fornecedor_existente:
            return jsonify({'error': 'Já existe um fornecedor com esse nome'}), 400

        # Atualizar fornecedor
        fornecedor.nome = nome

        db.session.commit()
        return jsonify(fornecedor.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/fornecedores/<int:fornecedor_id>', methods=['DELETE'])
def excluir_fornecedor(fornecedor_id):
    """Excluir fornecedor (desativar)"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get('senha') != ADMIN_PASSWORD:
            return jsonify({'error': 'Senha incorreta'}), 401

        fornecedor = Fornecedor.query.get_or_404(fornecedor_id)

        # Verificar se há produtos usando este fornecedor
        produtos_usando = Produto.query.filter_by(fornecedor=fornecedor.nome, ativo=True).count()
        if produtos_usando > 0:
            return jsonify({
                'error': f'Não é possível excluir. Existem {produtos_usando} produtos usando este fornecedor.'
            }), 400

        # Desativar fornecedor
        fornecedor.ativo = False
        db.session.commit()

        return jsonify({'message': 'Fornecedor excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/fornecedores/validar-nome')
def validar_nome_fornecedor():
    """Validar se nome do fornecedor já existe"""
    try:
        nome = request.args.get('nome', '').strip()
        fornecedor_id = request.args.get('id', type=int)

        if not nome:
            return jsonify({'valido': True})

        query = Fornecedor.query.filter(func.lower(Fornecedor.nome) == func.lower(nome))

        if fornecedor_id:
            query = query.filter(Fornecedor.id != fornecedor_id)

        fornecedor_existente = query.first()

        return jsonify({
            'valido': fornecedor_existente is None,
            'mensagem': 'Nome já existe' if fornecedor_existente else 'Nome disponível'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== APIs PARA PRODUÇÃO =====

@almoxarifado_bp.route('/api/producao/dashboard/stats')
def producao_dashboard_stats():
    """Estatísticas para o dashboard da produção"""
    try:
        from flask import session
        from src.models.almoxarifado import Requisicao

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Usuário não logado'}), 401

        # Total de produtos ativos
        total_produtos = Produto.query.filter_by(ativo=True).count()

        # Minhas requisições
        minhas_requisicoes = Requisicao.query.filter_by(usuario_id=user_id).count()

        # Requisições pendentes (minhas)
        requisicoes_pendentes = Requisicao.query.filter_by(
            usuario_id=user_id,
            status='PENDENTE'
        ).count()

        # Valor total em estoque
        valor_estoque = db.session.query(
            func.sum(Produto.preco * Produto.quantidade_estoque)
        ).filter(Produto.ativo == True).scalar() or 0

        return jsonify({
            'total_produtos': total_produtos,
            'minhas_requisicoes': minhas_requisicoes,
            'requisicoes_pendentes': requisicoes_pendentes,
            'valor_estoque': float(valor_estoque)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/producao/requisicoes', methods=['POST'])
def criar_requisicao():
    """Criar nova requisição da produção"""
    try:
        from flask import session
        from src.models.almoxarifado import Requisicao

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Usuário não logado'}), 401

        data = request.get_json()

        produto = Produto.query.get_or_404(data['produto_id'])
        obra = Obra.query.get_or_404(data['obra_id'])
        quantidade = float(data['quantidade'])

        # Verificar se há estoque suficiente
        if produto.quantidade_estoque < quantidade:
            return jsonify({
                'error': f'Estoque insuficiente. Disponível: {produto.quantidade_estoque}'
            }), 400

        # Criar requisição
        requisicao = Requisicao(
            produto_id=produto.id,
            obra_id=obra.id,
            usuario_id=user_id,
            quantidade_solicitada=quantidade,
            observacoes=data.get('observacoes', '')
        )

        db.session.add(requisicao)
        db.session.commit()

        return jsonify({
            'message': 'Requisição criada com sucesso',
            'requisicao': requisicao.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/producao/minhas-requisicoes')
def minhas_requisicoes():
    """Listar requisições do usuário logado"""
    try:
        from flask import session
        from src.models.almoxarifado import Requisicao

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Usuário não logado'}), 401

        status = request.args.get('status')

        query = Requisicao.query.filter_by(usuario_id=user_id)

        if status:
            query = query.filter_by(status=status)

        requisicoes = query.order_by(desc(Requisicao.data_requisicao)).all()

        return jsonify([req.to_dict() for req in requisicoes])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/almoxarifado/requisicoes')
def listar_requisicoes_almoxarifado():
    """Listar requisições para o almoxarifado atender"""
    try:
        from src.models.almoxarifado import Requisicao
        from src.models.user import User

        status = request.args.get('status')
        produto = request.args.get('produto')
        obra = request.args.get('obra')

        query = Requisicao.query

        if status:
            query = query.filter_by(status=status)
        elif not status and not produto and not obra:
            # Se nenhum filtro específico, mostrar apenas pendentes por padrão
            query = query.filter_by(status='PENDENTE')

        # Filtro por produto
        if produto:
            query = query.join(Produto).filter(
                db.or_(
                    Produto.nome.ilike(f'%{produto}%'),
                    Produto.codigo.ilike(f'%{produto}%')
                )
            )

        # Filtro por obra
        if obra:
            query = query.join(Obra).filter(
                db.or_(
                    Obra.nome_obra.ilike(f'%{obra}%'),
                    Obra.numero_obra.ilike(f'%{obra}%')
                )
            )

        requisicoes = query.order_by(desc(Requisicao.data_requisicao)).all()

        # Adicionar informações do usuário que fez a requisição
        resultado = []
        for req in requisicoes:
            req_dict = req.to_dict()
            usuario = User.query.get(req.usuario_id)
            req_dict['usuario_nome'] = usuario.username if usuario else 'Usuário não encontrado'
            resultado.append(req_dict)

        return jsonify(resultado)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/almoxarifado/requisicoes/<int:requisicao_id>/atender', methods=['POST'])
def atender_requisicao(requisicao_id):
    """Atender uma requisição (total ou parcial)"""
    try:
        from src.models.almoxarifado import Requisicao

        data = request.get_json()
        requisicao = Requisicao.query.get_or_404(requisicao_id)

        if requisicao.status != 'PENDENTE':
            return jsonify({'error': 'Requisição já foi atendida'}), 400

        quantidade_atendida = float(data.get('quantidade_atendida', requisicao.quantidade_solicitada))
        observacoes_atendimento = data.get('observacoes_atendimento', '')

        # Verificar estoque
        if requisicao.produto.quantidade_estoque < quantidade_atendida:
            return jsonify({'error': 'Estoque insuficiente'}), 400

        # Buscar funcionário do almoxarifado baseado no usuário logado
        from flask import session
        user_id = session.get('user_id')
        funcionario_id = 1  # padrão

        if user_id:
            from src.models.user import User
            user = User.query.get(user_id)
            if user:
                # Buscar funcionário com o mesmo nome do usuário (busca exata)
                funcionario = Funcionario.query.filter_by(nome=user.username, ativo=True).first()
                if not funcionario:
                    # Se não existe, criar funcionário automaticamente
                    funcionario = Funcionario(
                        nome=user.username,
                        cargo='Almoxarifado',
                        ativo=True
                    )
                    db.session.add(funcionario)
                    db.session.flush()  # Para obter o ID sem fazer commit

                funcionario_id = funcionario.id

        # Atualizar estoque
        requisicao.produto.quantidade_estoque -= quantidade_atendida

        # Atualizar requisição
        requisicao.quantidade_atendida = quantidade_atendida
        requisicao.data_atendimento = datetime.now(SAO_PAULO_TZ)
        requisicao.observacoes_atendimento = observacoes_atendimento
        requisicao.atendido_por = funcionario_id

        # Definir status
        if quantidade_atendida >= requisicao.quantidade_solicitada:
            requisicao.status = 'ATENDIDA'
        else:
            requisicao.status = 'PARCIAL'

        # Registrar movimentação
        movimentacao = Movimentacao(
            produto_id=requisicao.produto_id,
            obra_id=requisicao.obra_id,
            funcionario_id=funcionario_id,
            tipo_movimentacao='ALOCACAO',
            quantidade=quantidade_atendida,
            valor_unitario=requisicao.produto.preco,
            valor_total=requisicao.produto.preco * quantidade_atendida,
            observacoes=f'Atendimento de requisição #{requisicao.id} - {observacoes_atendimento}'
        )

        db.session.add(movimentacao)
        db.session.commit()

        return jsonify({
            'message': 'Requisição atendida com sucesso',
            'requisicao': requisicao.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/almoxarifado/requisicoes/<int:requisicao_id>/cancelar', methods=['POST'])
def cancelar_requisicao(requisicao_id):
    """Cancelar uma requisição"""
    try:
        from src.models.almoxarifado import Requisicao

        data = request.get_json()
        requisicao = Requisicao.query.get_or_404(requisicao_id)

        if requisicao.status != 'PENDENTE':
            return jsonify({'error': 'Apenas requisições pendentes podem ser canceladas'}), 400

        requisicao.status = 'CANCELADA'
        requisicao.observacoes_atendimento = data.get('motivo_cancelamento', 'Cancelada pelo almoxarifado')

        db.session.commit()

        return jsonify({
            'message': 'Requisição cancelada com sucesso',
            'requisicao': requisicao.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== ROTA PARA EXPORTAÇÃO =====

@almoxarifado_bp.route('/api/estoque/exportar')
def exportar_estoque():
    """Exportar dados do estoque em formato CSV"""
    try:
        # Buscar todos os produtos ativos
        produtos = Produto.query.filter_by(ativo=True).order_by(Produto.codigo).all()

        # Criar conteúdo CSV
        csv_content = "Código,Nome,Categoria,Fornecedor,Local,Preço,Estoque,Valor Total,Data Cadastro\n"

        for produto in produtos:
            valor_total = produto.preco * produto.quantidade_estoque
            data_cadastro = produto.data_cadastro.strftime('%d/%m/%Y %H:%M') if produto.data_cadastro else ''

            # Escapar vírgulas nos campos de texto
            nome = produto.nome.replace(',', ';') if produto.nome else ''
            fornecedor = produto.fornecedor.replace(',', ';') if produto.fornecedor else ''
            local = produto.local_produto.replace(',', ';') if produto.local_produto else ''

            csv_content += f"{produto.codigo},{nome},{produto.categoria},{fornecedor},{local},{produto.preco:.2f},{produto.quantidade_estoque},{valor_total:.2f},{data_cadastro}\n"

        # Criar resposta com arquivo CSV
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=estoque_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Obras APIs
@almoxarifado_bp.route("/api/obras", methods=["POST"])
def criar_obra():
    """Criar nova obra"""
    try:
        data = request.get_json()

        # Verificar se número da obra já existe
        if Obra.query.filter_by(numero_obra=data["numero_obra"]).first():
            return jsonify({"error": "Número da obra já existe"}), 400

        obra = Obra(
            numero_obra=data["numero_obra"],
            nome_obra=data["nome_obra"],
            descricao=data.get("descricao", ""),
            data_inicio=datetime.strptime(data["data_inicio"], "%Y-%m-%d").date() if "data_inicio" in data else None,
            data_fim=datetime.strptime(data["data_fim"], "%Y-%m-%d").date() if "data_fim" in data else None,
            status=data.get("status", "Prevista")
        )

        db.session.add(obra)
        db.session.commit()

        return jsonify(obra.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@almoxarifado_bp.route("/api/obras/<int:obra_id>", methods=["PUT"])
def editar_obra(obra_id):
    """Editar obra (requer senha)"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get("senha") != current_app.config["ADMIN_PASSWORD"]:
            return jsonify({"error": "Senha incorreta"}), 401

        obra = Obra.query.get_or_404(obra_id)

        obra.numero_obra = data.get("numero_obra", obra.numero_obra)
        obra.nome_obra = data.get("nome_obra", obra.nome_obra)
        obra.descricao = data.get("descricao", obra.descricao)
        obra.data_inicio = datetime.strptime(data["data_inicio"], "%Y-%m-%d").date() if "data_inicio" in data else obra.data_inicio
        obra.data_fim = datetime.strptime(data["data_fim"], "%Y-%m-%d").date() if "data_fim" in data else obra.data_fim
        obra.status = data.get("status", obra.status)

        if obra.status == "Entregue" and not obra.data_entrega:
            obra.data_entrega = datetime.now(SAO_PAULO_TZ)
        elif obra.status != "Entregue" and obra.data_entrega:
            obra.data_entrega = None

        db.session.commit()
        return jsonify(obra.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@almoxarifado_bp.route("/api/obras/<int:obra_id>", methods=["DELETE"])
def excluir_obra(obra_id):
    """Excluir obra (só pode ser excluída se for marcada como entregue e requer senha)"""
    try:
        data = request.get_json()

        # Verificar senha
        if data.get("senha") != current_app.config["ADMIN_PASSWORD"]:
            return jsonify({"error": "Senha incorreta"}), 401

        obra = Obra.query.get_or_404(obra_id)

        if obra.status != "Entregue":
            return jsonify({"error": "Obra só pode ser excluída se estiver com status 'Entregue'"}), 400

        db.session.delete(obra)
        db.session.commit()
        return jsonify({"message": "Obra excluída com sucesso"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Rotas para Locais
@almoxarifado_bp.route('/api/locais', methods=['GET'])
def get_locais():
    try:
        locais = Local.query.filter_by(ativo=True).order_by(Local.nome_local).all()
        return jsonify([local.to_dict() for local in locais])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/locais', methods=['POST'])
def create_local():
    try:
        data = request.get_json()

        # Validar dados obrigatórios
        if not data.get('nome_local'):
            return jsonify({'error': 'Nome do local é obrigatório'}), 400

        # Validar se posição contém apenas números, pontos e hífens
        posicao = data.get('posicao', '').strip()
        if posicao:
            import re
            if not re.match(r'^[0-9.\-]+$', posicao):
                return jsonify({'error': 'Posição deve conter apenas números, pontos (.) e hífens (-)'}), 400

        # Verificar se já existe local com mesmo nome
        local_existente = Local.query.filter_by(nome_local=data['nome_local'], ativo=True).first()
        if local_existente:
            return jsonify({'error': 'Já existe um local com este nome'}), 400

        novo_local = Local(
            nome_local=data['nome_local'],
            posicao=posicao if posicao else None,
            descricao=data.get('descricao', '')
        )

        db.session.add(novo_local)
        db.session.commit()

        return jsonify(novo_local.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/locais/<int:local_id>', methods=['PUT'])
def update_local(local_id):
    try:
        local = Local.query.get_or_404(local_id)
        data = request.get_json()

        # Validar dados obrigatórios
        if not data.get('nome_local'):
            return jsonify({'error': 'Nome do local é obrigatório'}), 400

        # Validar se posição contém apenas números, pontos e hífens
        posicao = data.get('posicao', '').strip()
        if posicao:
            import re
            if not re.match(r'^[0-9.\-]+$', posicao):
                return jsonify({'error': 'Posição deve conter apenas números, pontos (.) e hífens (-)'}), 400

        # Verificar se já existe outro local com mesmo nome
        local_existente = Local.query.filter(
            Local.nome_local == data['nome_local'],
            Local.id != local_id,
            Local.ativo == True
        ).first()
        if local_existente:
            return jsonify({'error': 'Já existe outro local com este nome'}), 400

        local.nome_local = data['nome_local']
        local.posicao = posicao if posicao else None
        local.descricao = data.get('descricao', '')

        db.session.commit()

        return jsonify(local.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@almoxarifado_bp.route('/api/locais/<int:local_id>', methods=['DELETE'])
def delete_local(local_id):
    try:
        local = Local.query.get_or_404(local_id)

        # Soft delete - marcar como inativo
        local.ativo = False
        db.session.commit()

        return jsonify({'message': 'Local excluído com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
