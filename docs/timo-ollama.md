# Conversação do TIMO

A tela `/timo` envia `POST /timo/process` com `X-Timo-Channel: web-text`,
`conversation: true`, `text` e `history: [{role, content}]`. A autenticação atual
continua obrigatória. Clientes antigos e o agente de voz mantêm seu contrato.

Comandos do catálogo, comandos personalizados e frases treinadas continuam
usando consultas, respostas e permissões existentes. Para mensagens sem um
comando reconhecido, a API chama o Ollama antes do classificador estatístico.
Conversa livre não alimenta a fila de treinamento de comandos.

Continuações curtas como `e ontem?` e `e neste mês?` reutilizam apenas o assunto
da consulta anterior reconhecida pelo catálogo. Datas, números e permissões são
consultados novamente. O modelo não executa ferramentas, SQL ou navegação.
Perguntas livres sobre dados que não correspondem ao catálogo ainda dependem
de reformulação pelo usuário; não há planejamento geral de ferramentas nesta versão.

`Quantas RTs disponíveis?` consulta reservas técnicas. `Quantos PCDs possuímos?`
consulta o cadastro atual com o mesmo critério do Indicador PCD (todas as situações),
exigindo `indicador_pcd:view` e aplicando o escopo por centro de custo. Aspas,
pontuação e acentos não impedem o reconhecimento dos comandos analíticos.

Respostas que só copiam ou reformulam muito de perto a pergunta são substituídas
por um aviso de que o TIMO não conseguiu responder. Esses ecos também são
removidos do histórico enviado ao modelo. A detecção é heurística; não garante
qualidade de todas as respostas livres do modelo de 0,6B.

## Configuração no servidor

Os padrões abaixo já permitem o teste no servidor onde o Ollama está instalado:

```dotenv
TIMO_OLLAMA_ENABLED=true
TIMO_OLLAMA_URL=http://127.0.0.1:11434
TIMO_OLLAMA_MODEL=qwen3:0.6b
```

O Ollama deve estar acessível pela conta que executa a API. Se a API estiver em
container, `127.0.0.1` será o próprio container; configure uma URL interna acessível.
Não é necessário publicar a porta do Ollama na internet.

Para um servidor de 4 GB: contexto fixo de 2.048 tokens, até 150 tokens por
resposta, `think: false` e retenção do modelo por cinco minutos. A API admite uma
chamada por host entre seus workers (flock no Linux), sem fila bloqueante.
Uma segunda conversa recebe aviso para tentar novamente; consultas tradicionais
continuam disponíveis. Chamadas externas à API do TMHub não participam desse bloqueio.
Se houver outros clientes Ollama, configure também `OLLAMA_NUM_PARALLEL=1` e
`OLLAMA_MAX_LOADED_MODELS=1` no serviço Ollama.

Timeout de conexão de 2 segundos e de leitura de 25 segundos; a interface aguarda
até 35 segundos. Erros, respostas vazias e modelo ausente viram mensagem de
indisponibilidade, sem converter bate-papo em uma ação estatística.

Histórico: últimas seis mensagens, até 500 caracteres por mensagem e 1.600
caracteres no total enviado ao modelo, além da mensagem atual. Só aceita papéis
`user`/`assistant`. Não grava conversas em banco; recarregar a página reinicia o
histórico. A interface separa contexto por sessão e filtros. Histórico enviado
pelo cliente não concede permissões nem autoriza ações. Respostas geradas podem
conter erros: consultas oficiais continuam vindo dos serviços do TMHub.

## Testar e reverter

O deploy executa os testes isolados antes de reiniciar a API e o smoke test
Ollama depois. O smoke test usa apenas uma saudação, sem consultar dados reais.

```bash
venv/bin/python -m unittest discover -s tests -p test_timo_conversation.py -v
venv/bin/python scripts/check_timo_ollama.py
```

Na tela `/timo`, testar:

1. `Meu nome é João.` e depois `Qual é meu nome?`.
2. `quantas faltas tivemos hoje` e depois `e ontem?`.
3. `abrir chamados`, verificando o botão de navegação já existente.
4. Trocar os filtros e repetir a consulta, sem reutilizar respostas do escopo anterior.

Para desativar a integração, definir `TIMO_OLLAMA_ENABLED=false` no `.env` da API
e executar `sudo systemctl restart tm`. Isso restaura o processamento anterior.
Se o smoke test falhar após o restart, a API pode já estar atualizada; consulte
`systemctl status tm` e a configuração do Ollama antes de repetir o deploy.

Referências: https://docs.ollama.com/api/chat e https://docs.ollama.com/faq.
