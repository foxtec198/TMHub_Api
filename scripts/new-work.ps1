[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('feat', 'fix', 'update', 'chore', 'hotfix')]
    [string]$Type,

    [Parameter(Mandatory)]
    [string]$Name,

    [string]$BaseBranch = 'dev'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git falhou: git $($Arguments -join ' ')" }
}

function ConvertTo-BranchSlug {
    param([string]$Text)
    $normalized = $Text.Normalize([Text.NormalizationForm]::FormD)
    $builder = [Text.StringBuilder]::new()
    foreach ($character in $normalized.ToCharArray()) {
        if ([Globalization.CharUnicodeInfo]::GetUnicodeCategory($character) -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$builder.Append($character)
        }
    }
    return ($builder.ToString().ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
}

Push-Location $repositoryRoot
try {
    if (git status --porcelain) { throw 'Há alterações locais. Faça commit, stash ou descarte-as antes de iniciar uma nova atividade.' }
    $slug = ConvertTo-BranchSlug $Name
    if (-not $slug) { throw 'Informe um nome válido para a atividade.' }
    $branch = "$Type/$slug"
    Invoke-Git fetch origin $BaseBranch --prune

    & git show-ref --verify --quiet "refs/heads/$BaseBranch"
    if ($LASTEXITCODE -ne 0) { Invoke-Git switch --track -c $BaseBranch "origin/$BaseBranch" }
    else { Invoke-Git switch $BaseBranch; Invoke-Git pull --ff-only origin $BaseBranch }

    & git show-ref --verify --quiet "refs/heads/$branch"
    if ($LASTEXITCODE -eq 0) { throw "A branch local '$branch' já existe. Troque para ela ou escolha outro nome." }
    & git ls-remote --exit-code --heads origin $branch *> $null
    if ($LASTEXITCODE -eq 0) { throw "A branch remota '$branch' já existe. Escolha outro nome." }

    Invoke-Git switch -c $branch
    Write-Host "`nAtividade pronta: $branch" -ForegroundColor Green
    Write-Host "Base sincronizada: origin/$BaseBranch" -ForegroundColor Cyan
    Write-Host "Ao finalizar, execute: .\scripts\deploy-pr.ps1 -Message 'tipo: resumo da alteração'" -ForegroundColor Yellow
}
finally { Pop-Location }
