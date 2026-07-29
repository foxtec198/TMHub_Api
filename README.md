<div align="center">
  <img src="./public/brands/main_brand.svg" alt="TM Hub" width="260">
  <h1>TM Hub | API</h1>


  <p>
    API, regras de negócio e eventos em tempo real do Painel Executivo TM Hub.
  </p>

  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
  [![Socket.IO](https://img.shields.io/badge/Socket.IO-Realtime-010101?logo=socketdotio&logoColor=white)](https://socket.io/)
  [![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
  [![Gunicorn](https://img.shields.io/badge/Gunicorn-Production-499848?logo=gunicorn&logoColor=white)](https://gunicorn.org/)

  [Frontend](https://github.com/foxtec198/tmhub) ·
  [Configuração](#executando-localmente) ·
  [Recursos](#domínios-da-api)
</div>

---

## Sobre

A **TM Hub API** concentra a persistência, autenticação, permissões, regras de
filial e automações do Painel Executivo. A aplicação oferece endpoints REST e
eventos Socket.IO para os módulos operacionais do
[frontend TM Hub](https://github.com/foxtec198/tmhub).

## Domínios da API

| Prefixo | Domínio |
| --- | --- |
| `/login` | Autenticação |
| `/usuarios` | Usuários, perfil, tema e permissões |
| `/filiais` | Filiais, departamentos, contratos e vínculos de usuários |
| `/funcionarios` | Colaboradores e busca operacional |
| `/supervisores` | Supervisores |
| `/centro` | Centros de custo e contratos |
| `/repo` | Requisições, histórico, timeline, importação e KDS |
| `/reservas` | Reservas técnicas |
| `/controle-faltas` | Faltas, tratativas e dashboard |
| `/glosas` | Glosas, cobertura, valores, evidências e exportação |
| `/admissao/vagas` | Vagas, admissões e aditivos |
| `/estrutura` | Locais, ativos e patrimônio |
| `/estoque/*` | Categorias, produtos e movimentações |
| `/dash/*` | Indicadores e Ponto 48h |
| `/projetos` | Projetos e atividades |
| `/rpa` | Comunicação com agentes RPA |

## Recursos principais

- API REST com Flask.
- PostgreSQL com SQLAlchemy.
- Autenticação por JWT.
- Matriz de permissões por tela e ação.
- Escopo obrigatório de dados por filial.
- Atualizações em tempo real via Flask-SocketIO.
- Importação e exportação de planilhas com Pandas/OpenPyXL.
- Armazenamento controlado de evidências de glosas.
- Envio de códigos de segurança por SMTP.
- Integrações com SQL Server via PyODBC/PyMSSQL.
- Execução produtiva com Gunicorn, Gevent e WebSocket.

> [!IMPORTANT]
> `apply_cost_center_scope` e `can_access_cost_center` fazem parte da barreira de
> segurança do sistema. Novas telas autenticadas que consultem contratos,
> colaboradores ou dados operacionais devem aplicar o escopo de filial.

## Tecnologias

| Categoria | Tecnologias |
| --- | --- |
| Web | Flask, Flask-CORS e Werkzeug |
| Persistência | PostgreSQL, SQLAlchemy e psycopg2 |
| Tempo real | Flask-SocketIO, Gevent e WebSocket |
| Segurança | PyJWT e Cryptography |
| Dados | Pandas, NumPy e OpenPyXL |
| Bancos externos | PyODBC e PyMSSQL |
| Produção | Gunicorn |
| Integrações | HTTPX, Requests, SMTP e OpenAI SDK |

## Arquitetura

```text
routes/       Endpoints e blueprints
    │
    ▼
services/     Regras de negócio, validação e eventos
    │
    ├────────► models/        Modelos SQLAlchemy
    ├────────► utils/         Token, permissões, filial e banco
    ├────────► storage/       Evidências persistidas
    └────────► PostgreSQL
```

## Executando localmente

### Pré-requisitos

- Python 3.11 ou superior.
- PostgreSQL.
- Ambiente virtual Python.

### Instalação

```bash
git clone https://github.com/foxtec198/api_tmhub.git
cd api_tmhub
python -m venv venv
```

Ative o ambiente virtual:

```powershell
# Windows
.\venv\Scripts\Activate.ps1
```

```bash
# Linux/macOS
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e configure o ambiente:

```env
SECRET=troque-por-uma-chave-segura
DB_URI=postgresql://usuario:senha@localhost:5432/tmhub
HOST=0.0.0.0
PORT=8590
DEBUG=False

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_STARTTLS=true

# Opcional: diretório persistente para evidências
GLOSA_EVIDENCE_DIR=
```

Inicie a API:

```bash
python app.py
```

Por padrão, o serviço utiliza a porta `8590`.

## Produção

Exemplo com Gunicorn e worker Gevent WebSocket:

```bash
gunicorn \
  --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
  --workers 1 \
  --bind 0.0.0.0:8590 \
  wsgi:app
```

O Socket.IO mantém estado de conexões e eventos; revise a estratégia de
mensageria antes de aumentar o número de workers.

## Autenticação e permissões

As rotas autenticadas recebem o JWT pelo cabeçalho:

```http
Access-Token: <token>
```

A autorização combina:

1. Usuário autenticado.
2. Permissão da tela e da ação.
3. Filiais vinculadas ao usuário.
4. Centros de custo permitidos pelas filiais.

Administradores possuem visão global. Usuários comuns recebem a união das
filiais autorizadas.

## Eventos em tempo real

Entre os eventos publicados pela API estão:

| Evento | Finalidade |
| --- | --- |
| `new_request` | Atualizar requisições |
| `new_history` | Atualizar histórico |
| `kds_update` | Atualizar o painel KDS |
| `absence_control_update` | Atualizar controle e dashboard de faltas |
| `disallowance_update` | Atualizar controle de glosas |
| `command` / `command_done` | Comunicação com agentes RPA |

## Estrutura principal

```text
api_tmhub/
├── models/          # Entidades SQLAlchemy
├── routes/          # Blueprints HTTP
├── services/        # Casos de uso e regras de negócio
├── utils/           # Infraestrutura e segurança
├── storage/         # Arquivos persistidos
├── import_col/      # Importação de colaboradores
├── app.py           # Aplicação principal
└── wsgi.py          # Entrada para produção
```

## Boas práticas

- Nunca versionar `.env`, credenciais ou tokens.
- Aplicar o escopo de filial em toda nova consulta autenticada.
- Validar permissão novamente na API; ocultar botões no frontend não é segurança.
- Executar migrations necessárias antes de publicar alterações de modelo.
- Manter uploads em armazenamento persistente no ambiente de produção.

## Projeto relacionado

A interface web está no repositório
**[tmhub](https://github.com/foxtec198/tmhub)**.

## Licença e uso

Projeto proprietário destinado ao uso interno. Distribuição, cópia ou
modificação externa dependem de autorização.
