# Sistema de Almoxarifado

Sistema de gerenciamento de almoxarifado desenvolvido em Flask, com suporte para múltiplos ambientes (desenvolvimento e produção).

## Características

- **Desenvolvimento**: Usa SQLite para facilidade de desenvolvimento
- **Produção**: Usa PostgreSQL para melhor performance e escalabilidade
- **Configuração automática**: Detecta o ambiente automaticamente
- **Pronto para deploy**: Inclui configuração do Gunicorn

## Estrutura do Projeto

```
Almoxarifado/
├── src/
│   ├── config.py          # Configurações por ambiente
│   ├── main.py            # Aplicação principal
│   ├── init_db.py         # Script de inicialização do banco
│   ├── models/            # Modelos do banco de dados
│   ├── routes/            # Rotas da aplicação
│   ├── templates/         # Templates HTML
│   ├── static/            # Arquivos estáticos
│   └── database/          # Banco SQLite (desenvolvimento)
├── requirements.txt       # Dependências Python
├── gunicorn.conf.py      # Configuração do Gunicorn
├── .env.example          # Exemplo de variáveis de ambiente
└── README.md             # Este arquivo
```

## Instalação

### 1. Clone ou extraia o projeto

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente (opcional)

Copie o arquivo `.env.example` para `.env` e ajuste conforme necessário:

```bash
cp .env.example .env
```

## Uso

### Desenvolvimento (SQLite)

1. **Inicialize o banco de dados:**
```bash
cd src
python init_db.py
```

2. **Execute a aplicação:**
```bash
cd src
python main.py
```

A aplicação estará disponível em `http://localhost:5000`

**Credenciais padrão:**
- Usuário: `Monter`
- Senha: `almox`

### Produção (PostgreSQL)

1. **Configure as variáveis de ambiente:**
```bash
export FLASK_ENV=production
export DB_HOST=seu_host_postgresql
export DB_PORT=5432
export DB_NAME=almoxarifado
export DB_USER=seu_usuario
export DB_PASSWORD=sua_senha
export SECRET_KEY=sua_chave_secreta_segura
```

2. **Certifique-se de que o PostgreSQL está rodando e o banco existe:**
```sql
CREATE DATABASE almoxarifado;
```

3. **Inicialize o banco de dados:**
```bash
cd src
FLASK_ENV=production python init_db.py
```

4. **Execute com Gunicorn:**
```bash
gunicorn -c gunicorn.conf.py src.main:app
```

## Variáveis de Ambiente

| Variável | Descrição | Padrão | Obrigatório |
|----------|-----------|---------|-------------|
| `FLASK_ENV` | Ambiente (development/production) | development | Não |
| `SECRET_KEY` | Chave secreta da aplicação | (padrão inseguro) | Sim (produção) |
| `DB_HOST` | Host do PostgreSQL | localhost | Sim (produção) |
| `DB_PORT` | Porta do PostgreSQL | 5432 | Não |
| `DB_NAME` | Nome do banco PostgreSQL | almoxarifado | Sim (produção) |
| `DB_USER` | Usuário do PostgreSQL | postgres | Sim (produção) |
| `DB_PASSWORD` | Senha do PostgreSQL | (vazio) | Sim (produção) |
| `PORT` | Porta da aplicação | 5000 | Não |

## Configuração Automática

O sistema detecta automaticamente o ambiente através da variável `FLASK_ENV`:

- **development**: Usa SQLite (`src/database/app.db`)
- **production**: Usa PostgreSQL (configurado via variáveis de ambiente)

## Deploy

### Render (Recomendado)

O projeto está configurado para deploy automático no Render:

1. **Conecte seu repositório GitHub** no painel do Render
2. **Configure as variáveis de ambiente**:
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: (gere uma chave secreta forte)
   - `DATABASE_URL`: (será fornecida automaticamente pelo PostgreSQL addon)

3. **Configurações de build**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash run_prod.sh`

4. **Adicione um banco PostgreSQL** no Render e conecte ao seu web service

O arquivo `render.yaml` já está configurado para deploy automático.

### Docker

Exemplo de Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.main:app"]
```

### Heroku

1. Adicione as variáveis de ambiente no painel do Heroku
2. Configure o PostgreSQL addon
3. O sistema detectará automaticamente o ambiente de produção

### VPS/Servidor Dedicado

1. Configure o PostgreSQL
2. Configure as variáveis de ambiente
3. Use um processo manager como systemd ou supervisor
4. Configure um proxy reverso (nginx/apache)

## Troubleshooting

### Erro de conexão com PostgreSQL

Verifique se:
- O PostgreSQL está rodando
- As credenciais estão corretas
- O banco de dados existe
- O usuário tem permissões adequadas

### Erro "No module named 'psycopg2'"

Instale o driver PostgreSQL:
```bash
pip install psycopg2-binary
```

### Banco SQLite não encontrado

Execute o script de inicialização:
```bash
cd src
python init_db.py
```

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para mais detalhes.

