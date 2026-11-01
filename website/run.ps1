param([ValidateSet('dev', 'build', 'test', 'preview', 'sync-data', 'verify-source')][string]$Action = 'dev')
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    # The presentation build can run offline without installing JavaScript packages.
    if ($Action -eq 'preview' -and !(Test-Path -LiteralPath 'node_modules/vite/bin/vite.js')) {
        if (!(Test-Path -LiteralPath 'dist/index.html')) { throw 'Run .\run.ps1 build to create the presentation first.' }
        Write-Host 'Open http://127.0.0.1:4173/ (Ctrl+C to stop)'
        & python -m http.server 4173 --bind 127.0.0.1 --directory dist
        if ($LASTEXITCODE -ne 0) { throw 'Preview requires Python 3 or the website development dependencies.' }
        return
    }
    $bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    $nodeCandidates = @($bundledNode)
    if ($nodeCommand) { $nodeCandidates += $nodeCommand.Source }
    $selectedNode = $null
    foreach ($candidate in $nodeCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            $version = & $candidate --version
            if ($version -match '^v24\.') { $selectedNode = $candidate; break }
        }
    }
    if (-not $selectedNode) { throw 'Node.js 24 LTS is required. Install it and retry.' }
    Write-Host "Using $(& $selectedNode --version) for $Action"
    function Invoke-NodeStep([string[]]$StepArguments) {
        & $selectedNode @StepArguments
        if ($LASTEXITCODE -ne 0) { throw "Command failed: node $($StepArguments -join ' ')" }
    }
    if ($Action -in @('dev', 'build', 'test') -and !(Test-Path -LiteralPath 'node_modules/vite/bin/vite.js')) {
        $npm = Get-Command npm.cmd -ErrorAction Stop
        $npmCli = Join-Path (Split-Path $npm.Source) 'node_modules/npm/bin/npm-cli.js'
        Write-Host 'Restoring the locked development dependencies from the npm cache or registry...'
        $previousPath = $env:Path
        try {
            $env:Path = (Split-Path $selectedNode) + ';' + $previousPath
            Invoke-NodeStep @($npmCli, 'ci', '--prefer-offline', '--no-audit', '--no-fund')
        } finally { $env:Path = $previousPath }
    }
    if ($Action -in @('dev', 'build', 'test', 'sync-data')) {
        Invoke-NodeStep @('scripts/sync-data.mjs')
    }
    if ($Action -eq 'verify-source') {
        Invoke-NodeStep @('scripts/sync-data.mjs', '--require-current-submission')
    }
    switch ($Action) {
        'dev' { Invoke-NodeStep @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1') }
        'preview' { Invoke-NodeStep @('node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1') }
        'test' { Invoke-NodeStep @('node_modules/vitest/vitest.mjs', 'run') }
        'build' {
            Invoke-NodeStep @('node_modules/typescript/bin/tsc', '-b')
            Invoke-NodeStep @('node_modules/vite/bin/vite.js', 'build')
        }
    }
} finally { Pop-Location }
