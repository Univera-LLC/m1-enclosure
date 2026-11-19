#Requires -Version 7.0
<#
.SYNOPSIS
  Work with the Mac mini M1 enclosure from any directory.
.EXAMPLE
  ./project.ps1 check
.EXAMPLE
  ./project.ps1 build -InputsPath /path/to/references
#>
[CmdletBinding()]
param(
    [Parameter(Position=0)][ValidateSet('doctor','check','viewer','build')][string]$Task = 'doctor',
    [Alias('Profile')][ValidateSet('release','viewer','cad')][string]$ToolProfile = 'release',
    [string]$InputsPath,
    [string]$Assembly,
    [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$project = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'project.json') | ConvertFrom-Json
# Resolve caller-supplied paths before switching to the project.
$cadArgs = @()
if ($InputsPath) { $cadArgs += @('--inputs', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($InputsPath)) }
if ($Assembly) { $cadArgs += @('--assembly', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Assembly)) }
if ($OutputPath) { $runPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath) }
elseif ($Task -eq 'build') {
    $runPath = Join-Path $PSScriptRoot ('build/' + $project.revision.ToLowerInvariant() + '-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))
}
if ($Task -eq 'build') {
    $baselinePath = if ($project.revision -eq 'D2.7') { Join-Path $runPath 'baseline' } else { $runPath }
    if (Test-Path -LiteralPath $runPath) { throw 'Choose a new build output directory.' }
    $cadArgs += @('--output', $baselinePath)
}
if ($OutputPath -and $Task -ne 'build') { throw '-OutputPath applies to build.' }
if (($InputsPath -or $Assembly) -and $Task -ne 'build' -and !($Task -eq 'doctor' -and $ToolProfile -eq 'cad')) { throw 'Reference inputs apply to build or doctor -Profile cad.' }

function Find-Tool([string[]]$Names, [string]$Hint) {
    foreach ($name in $Names) {
        $tool = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($tool) { return $tool.Source }
    }
    throw $Hint
}
function Get-ViewerNode {
    $node = Find-Tool @('node') 'Install Node.js with npm; see docs/VIEWER.md.'
    Push-Location -LiteralPath $project.viewer
    try { & $node -e "for (const p of ['esbuild','three','playwright']) require.resolve(p)" } finally { Pop-Location }
    if ($LASTEXITCODE) { throw 'Install viewer dependencies: npm ci --prefix cad/solidcraft-m1/viewer' }
    return $node
}
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($Task -eq 'doctor' -and $ToolProfile -eq 'release') {
        $py = Find-Tool @('python','python3') 'Install Python 3.10 or newer for the release check.'
        & $py -c "import sys; print('Python', sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3,10) else 1)"
        if ($LASTEXITCODE) { throw 'Python 3.10 or newer is required.' }
        & $py tools/verify_release.py
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
        Write-Output 'For browser or native CAD prerequisites: ./project.ps1 doctor -Profile viewer or -Profile cad.'
    } elseif ($Task -eq 'build' -or ($Task -eq 'doctor' -and $ToolProfile -eq 'cad')) {
        $uv = Find-Tool @('uv') 'Install uv and follow docs/CAD-BUILD.md for the native build.'
        if ($Task -eq 'doctor') {
            if (!(Test-Path -LiteralPath '.venv/pyvenv.cfg')) { throw 'Run uv sync --locked first; see docs/CAD-BUILD.md.' }
            & $uv run --no-sync --locked python tools/cad_build.py --doctor @cadArgs
        } else {
            $node = Get-ViewerNode
            & $uv run --locked python tools/cad_build.py @cadArgs
            if ($LASTEXITCODE) { exit $LASTEXITCODE }
            $nativeReceipt = 'verified.json'
            if ($project.revision -eq 'D2.7') {
                $generated = Join-Path $runPath 'cad'
                & $uv run --locked python "$($project.cad)/build_d27.py" --baseline $baselinePath --output $generated
                if ($LASTEXITCODE) { exit $LASTEXITCODE }
                $nativeReceipt = 'cad/verified.json'
            } else {
                $generated = Join-Path $runPath "workspace/$($project.cad)"
            }
            $packed = Join-Path $runPath 'packed'
            $site = Join-Path $runPath 'viewer'
            & $uv run --locked python "$($project.viewer)/pack_model.py" --cad-dir $generated --output $packed
            if ($LASTEXITCODE) { exit $LASTEXITCODE }
            & $node "$($project.viewer)/build.mjs" --cad-dir $generated --packed $packed --output $site
            if ($LASTEXITCODE) { exit $LASTEXITCODE }
            & $node "$($project.viewer)/browser.mjs" --engineering $site
            if ($LASTEXITCODE) { exit $LASTEXITCODE }
            [ordered]@{revision=$project.revision; digital='passed'; physical='NOT TESTED'; native=$nativeReceipt; viewer='viewer/'} |
                ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runPath 'candidate.json') -Encoding utf8NoBOM
            Write-Output "Verified rebuilt CAD, print kits and browser candidate: $runPath"
        }
        exit $LASTEXITCODE
    } else {
        $npm = Find-Tool @('npm.cmd','npm') 'Install Node.js with npm; see docs/VIEWER.md.'
        if ($Task -eq 'doctor') {
            $node = Get-ViewerNode
            & $node --version
            Write-Output 'Run ./project.ps1 check to exercise the installed browser.'
        } else {
            $command = if ($Task -eq 'check') { 'check' } else { 'preview' }
            & $npm --prefix $project.viewer run $command
            exit $LASTEXITCODE
        }
    }
} finally { Pop-Location }
