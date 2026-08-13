<div align="center">
  <img src="./static/assets/brands/main_brand.svg" alt="TM Hub" width="260">

  # TM Hub · API

  API, regras de negócio, segurança e eventos em tempo real do Painel Executivo TM Hub.

  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
  [![Socket.IO](https://img.shields.io/badge/Socket.IO-Tempo%20real-010101?logo=socketdotio&logoColor=white)](https://socket.io/)
  [![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=jsonwebtokens&logoColor=white)](https://jwt.io/)

  [Frontend](https://github.com/foxtec198/tmhub) ·
  [Fluxo do time](./FLUXO.md) ·
  [Documentação OpenAPI](/docs)
</div>

---

## Visão geral

A API TM Hub centraliza persistência, autenticação, permissões, escopo de
filiais, automações e comunicação em tempo real para o frontend e agentes
integrados. A documentação interativa é exposta em `/docs` e o contrato OpenAPI
em `/openapi.json`.

## Domínios principais

| Prefixo | Domínio |
| --- | --- |
| `/login` e `/usuarios` | Autenticação, perfil, senha, tema e permissões. |
| `/filiais`, `/centro`, `/funcionarios`, `/supervisores` | Filiais, departamentos, contratos, colaboradores e supervisores. |
| `/repo`, `/reservas`, `/controle-faltas` | Reposições, histórico, reservas e faltas. |
| `/glosas` | Controle de glosas, cobertura, evidências, exportação e Roçada. |
| `/admissao/vagas` e `/rescisoes` | Vagas, admissões, aditivos e desligamentos. |
| `/estoque/*` | Produtos, categorias, movimentações e logística. |
| `/estrutura` | Hierarquia de contratos, locais, subestruturas e ativos. |
| `/tm-ops` | Acessos, rotinas, checklists, tarefas, evidências e geolocalização. |
| `/projetos` | Projetos, cards, membros, comentários, anexos e métricas. |
| `/tickets` | Chamados, comentários, motivos, responsáveis, SLA e notificações. |
| `/dash/*` | Indicadores operacionais e executivos. |
| `/timo` e `/timo/agentes` | Intenções, aprendizado, comandos e Timo Voice Agent. |

## Recursos atuais

- API REST com Flask, SQLAlchemy e PostgreSQL.
- OpenAPI/Swagger gerado a partir das rotas registradas.
- JWT com invalidação por versão de token e senhas novas em Argon2id com pepper.
- Pendências obrigatórias de primeiro acesso: CPF, senha e dados de perfil conforme a política configurada.
- Matriz de permissões por tela e ação, aplicada antes das rotas protegidas.
- Escopo de filial no backend por `X-Filial-Ids`; o servidor decide o que cada usuário pode consultar.
- Eventos Socket.IO por domínio e evento genérico `data_changed`, evitando atualização global desnecessária.
- Importação de colaboradores com progresso, validação de cargos e atualização em tempo real.
- Scheduler/TM Ops com recorrência ancorada, tarefas compartilhadas, executor, checklist, evidências e trilha GPS.
- Chamados vinculados à filial, SLA de 24 horas, comentários, gestão de motivos, notificações SMTP e atualização em tempo real.
- Timo configurável, aprendizado assistido e suporte ao agente desktop pareado por WebSocket.

## Arquitetura

```text
routes/       Blueprints e contratos HTTP
   │
   ▼
services/     Regras de negócio, validações e transações
   ├── models/       Entidades SQLAlchemy
   ├── utils/        JWT, permissões, filial, Socket.IO e OpenAPI
   ├── storage/      Evidências e arquivos persistidos
   └── PostgreSQL
```

## Execução local

### Pré-requisitos

- Python 3.11 ou superior.
- PostgreSQL acessível.
- Ambiente virtual Python.

```powershell
git clone https://github.com/foxtec198/api_tmhub.git
cd api_tmhub
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

A API responde, por padrão, em `http://localhost:8590`.

Variáveis essenciais em `.env`:

```env
SECRET=troque-por-uma-chave-segura
PASSWORD_PEPPER=segredo-longo-exclusivo-do-ambiente
DB_URI=postgresql://usuario:senha@localhost:5432/tmhub
HOST=0.0.0.0
PORT=8590

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_STARTTLS=true
```

As tabelas e migrations aditivas compatíveis são verificadas na inicialização.
Quando uma alteração exigir uma migration específica, ela deve ser executada e
validada antes de publicar a API.

## Produção

O GitHub Actions faz deploy apenas após push em `main`. O workflow atualiza o
checkout no servidor, instala dependências e reinicia o serviço `api_tmhub`.

Exemplo de execução com WebSocket:

```bash
gunicorn \
  --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
  --workers 1 \
  --bind 0.0.0.0:8590 \
  wsgi:app
```

## Segurança e filial

1. O token chega pelo cabeçalho `Access-Token`.
2. A API identifica o usuário e aplica a matriz de permissões.
3. O escopo de filiais calcula os centros de custo autorizados.
4. Serviços e queries aplicam `apply_cost_center_scope` ou a regra de domínio equivalente.

Administradores têm visão global. Usuários vinculados à Matriz podem selecionar
filiais no layout; usuários comuns recebem apenas o conjunto de filiais que
possuem vínculo ativo.

## Eventos em tempo real

| Evento/canal | Finalidade |
| --- | --- |
| `new_request`, `new_history`, `kds_update` | Reposições, histórico e KDS. |
| `absence_control_update` | Controle e dashboard de faltas. |
| `disallowance_update` | Glosas e Roçada. |
| `ticket_update` | Criação, comentário, atualização e atraso de chamados. |
| `data_changed` | Atualização por domínio da tela afetada. |
| `timo_learning_updated`, `timo_agent_*` | Aprendizado e estado do Timo Voice Agent. |
| `command`, `command_done` | Comunicação com agentes RPA. |

## Estrutura do backend

```text
api_tmhub/
├── models/       entidades SQLAlchemy
├── routes/       blueprints HTTP
├── services/     casos de uso e regras de negócio
├── utils/        infraestrutura, segurança e Socket.IO
├── storage/      arquivos persistidos
├── import_col/   importação de colaboradores
├── scripts/      fluxo de branches e Pull Requests
├── app.py        aplicação Flask
└── wsgi.py       entrada de produção
```

## Contribuição

Leia [FLUXO.md](./FLUXO.md). Toda nova tela autenticada deve ter permissão,
escopo de filial no backend, eventos em tempo real quando aplicável e validação
do contrato OpenAPI.

## Projeto relacionado

A interface web está em **[tmhub](https://github.com/foxtec198/tmhub)**.

## Licença e uso

Projeto proprietário de uso interno. Distribuição, cópia ou modificação externa
dependem de autorização.
