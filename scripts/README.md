# Fluxo de entrega do time

O ambiente de trabalho compartilhado é `dev`. A produção é `main` e só o
responsável do projeto promove `dev` para ela.

## Iniciar uma atividade

```powershell
.\scripts\new-work.ps1 -Type fix -Name "corrige validacao de tickets"
```

Tipos disponíveis: `feat`, `fix`, `update`, `chore` e `hotfix`.

O script exige uma árvore limpa, atualiza `dev` com `pull --ff-only` e cria uma
branch no formato `tipo/nome-da-atividade`.

## Enviar para revisão

```powershell
.\scripts\deploy-pr.ps1 -Message "fix: corrige validacao de tickets"
```

O script adiciona e cria o commit pendente, atualiza a branch por rebase em
`origin/dev`, faz push com proteção `--force-with-lease` e abre o Pull Request
para `dev`. Se a revisão já existir, ele apenas atualiza o PR.

Use `-Draft` quando a implementação ainda não estiver pronta para análise.

> `deploy-pr.ps1` não faz deploy em produção. As branches `main` e `dev` são
> bloqueadas como origem do envio para preservar a revisão por PR.
