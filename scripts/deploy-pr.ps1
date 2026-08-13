[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Message,
    [string]$Title,
    [string]$BaseBranch = 'dev',
    [switch]$Draft
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git falhou: git $($Arguments -join ' ')" }
}

Push-Location $repositoryRoot
try {
    $branch = (git branch --show-current).Trim()
    if (-not $branch) { throw 'Não foi possível identificar a branch atual.' }
    if ($branch -in @('main', 'master', $BaseBranch)) { throw "Não envie alterações diretamente para '$branch'. Crie uma branch de trabalho primeiro com .\scripts\new-work.ps1." }

    Invoke-Git add --all
    & git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) { Invoke-Git commit -m $Message }

    Invoke-Git fetch origin $BaseBranch --prune
    & git rebase "origin/$BaseBranch"
    if ($LASTEXITCODE -ne 0) { throw "O rebase encontrou conflito. Resolva-o, execute 'git rebase --continue' e rode este script novamente." }

    Invoke-Git push --set-upstream origin $branch --force-with-lease
    & gh auth status *> $null
    if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI sem autenticação. Execute: gh auth login' }

    $existingPr = (& gh pr view $branch --json url --jq '.url' 2>$null).Trim()
    if ($LASTEXITCODE -eq 0 -and $existingPr) {
        Write-Host "`nPush concluído. PR já existente: $existingPr" -ForegroundColor Green
        exit 0
    }

    if (-not $Title) { $Title = $Message }
    $body = "## Resumo`n$Message`n`n## Fluxo`n- Base sincronizada com ``$BaseBranch`` antes do envio.`n- PR destinado a ``$BaseBranch``.`n- Aguardando revisão e aprovação."
    $ghArguments = @('pr', 'create', '--base', $BaseBranch, '--head', $branch, '--title', $Title, '--body', $body)
    if ($Draft) { $ghArguments += '--draft' }
    & gh @ghArguments
    if ($LASTEXITCODE -ne 0) { throw 'O push foi concluído, mas não foi possível criar o PR automaticamente.' }
    Write-Host "`nPR criado para '$BaseBranch'. Nenhum deploy de produção foi realizado." -ForegroundColor Green
}
finally { Pop-Location }
