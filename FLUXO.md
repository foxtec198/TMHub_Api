# Fluxo de desenvolvimento e entrega

Este documento vale para o backend **API TM Hub** e para o frontend
**TM Hub**.

## Papéis e branches

| Papel | Responsabilidade |
| --- | --- |
| Colaborador | Trabalha em branch própria e abre Pull Request para `dev`. |
| Responsável técnico | Revisa, aprova ou reprova PRs destinados a `dev`. |
| Dono do projeto | Trabalha e integra em `dev`; promove `dev` para `main` após validar a release. |

| Branch | Uso |
| --- | --- |
| `main` | Produção. Push dispara o deploy automático. |
| `dev` | Integração e homologação. |
| `feat/*`, `fix/*`, `update/*`, `chore/*`, `hotfix/*` | Atividades isoladas. |

> Colaboradores não enviam alterações diretamente para `dev` ou `main`. Isso
> preserva a revisão obrigatória por Pull Request.

## 1. Iniciar uma atividade

O script exige uma árvore limpa, sincroniza a base com `origin/dev` usando
`pull --ff-only` e cria uma branch padronizada.

```powershell
.\scripts\new-work.ps1 -Type feat -Name "adiciona notificacao de chamado"
```

Tipos aceitos: `feat`, `fix`, `update`, `chore` e `hotfix`.

## 2. Desenvolver e validar

- Não altere `.env`, credenciais, tokens ou arquivos de produção.
- Preserve mudanças de outros colaboradores que já estejam no repositório.
- Toda rota autenticada deve validar permissão e escopo de filial no backend.
- Operações críticas devem usar transação e eventos WebSocket apenas no domínio afetado.

### Validações mínimas

```powershell
.\venv\Scripts\python.exe -m compileall -q app.py routes services models
```

Quando houver alteração no frontend associado:

```powershell
cd ..\tmhub
npm.cmd run build
```

## 3. Enviar para revisão

O script adiciona os arquivos, cria o commit pendente, atualiza a branch por
rebase em `origin/dev`, faz push com `--force-with-lease` e abre o PR para
`dev`. Se o PR já existir, ele só é atualizado.

```powershell
.\scripts\deploy-pr.ps1 -Message "feat: adiciona notificacao de chamado"
```

Para abrir como rascunho, acrescente `-Draft`.

> Esse comando **não faz deploy em produção**. Ele apenas publica a branch e
> cria/atualiza o PR para `dev`.

## 4. Revisão e promoção

1. O responsável revisa o PR para `dev`.
2. Após aprovação, integra em `dev` e testa a homologação.
3. O dono do projeto promove `dev` para `main` quando a release estiver validada.
4. O push em `main` dispara o GitHub Actions de deploy do respectivo repositório.

## Conflitos

Se o script de envio parar por conflito no rebase:

```powershell
git add <arquivos-resolvidos>
git rebase --continue
```

Para abandonar o rebase e voltar ao estado anterior:

```powershell
git rebase --abort
```

## Primeiro uso na máquina

O GitHub CLI precisa estar autenticado para abrir PRs automaticamente:

```powershell
gh auth login
gh auth status
```
