[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Message,
    [string]$Title,
    [string]$BaseBranch = 'dev',
    [switch]$Draft,
    [switch]$KeepLocalBranch
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git falhou: git $($Arguments -join ' ')" }
}

function Ensure-GitHubCli {
    if (Get-Command gh -ErrorAction SilentlyContinue) { return }

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'GitHub CLI nao foi encontrado e o winget nao esta disponivel. Instale o GitHub CLI manualmente: https://cli.github.com/'
    }

    Write-Host 'GitHub CLI nao encontrado. Instalando pelo winget...' -ForegroundColor Yellow
    & $winget.Source install --id GitHub.cli --exact --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel instalar o GitHub CLI automaticamente.'
    }

    $knownPaths = @(
        (Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\GitHub CLI\gh.exe'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\gh.exe')
    )
    $installedGh = $knownPaths | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if ($installedGh) {
        $env:Path = "$(Split-Path -Parent $installedGh);$env:Path"
    }

    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'O GitHub CLI foi instalado, mas nao esta disponivel nesta sessao. Feche e abra o PowerShell e execute o script novamente.'
    }
}

function Remove-LocalWorkBranch {
    param([string]$BranchName)

    if ($KeepLocalBranch) {
        Write-Host "Branch local '$BranchName' preservada por solicitacao." -ForegroundColor Yellow
        return
    }

    Invoke-Git switch $BaseBranch
    Invoke-Git branch -D $BranchName
    Write-Host "Branch local '$BranchName' removida. A branch remota foi mantida para o PR." -ForegroundColor Green
}

Ensure-GitHubCli

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

$existingPr = [string](& gh pr list --head $branch --state open --json url --jq '.[0].url' 2>$null)
$existingPr = $existingPr.Trim()
if ($existingPr) {
        Write-Host "`nPush concluído. PR já existente: $existingPr" -ForegroundColor Green
        Remove-LocalWorkBranch -BranchName $branch
        return
    }

    if (-not $Title) { $Title = $Message }
    $body = "## Resumo`n$Message`n`n## Fluxo`n- Base sincronizada com ``$BaseBranch`` antes do envio.`n- PR destinado a ``$BaseBranch``.`n- Aguardando revisão e aprovação."
    $ghArguments = @('pr', 'create', '--base', $BaseBranch, '--head', $branch, '--title', $Title, '--body', $body)
    if ($Draft) { $ghArguments += '--draft' }
    & gh @ghArguments
    if ($LASTEXITCODE -eq 0) { Remove-LocalWorkBranch -BranchName $branch }
    if ($LASTEXITCODE -ne 0) { throw 'O push foi concluído, mas não foi possível criar o PR automaticamente.' }
    Write-Host "`nPR criado para '$BaseBranch'. Nenhum deploy de produção foi realizado." -ForegroundColor Green
}
finally { Pop-Location }
