<#
.SYNOPSIS
    Safe local Room 23/Room 7 regression and portable-preview acceptance gate.
.DESCRIPTION
    Default mode is read-only: verifies canonical checkout state, original
    archive hashes and the pinned 87-frame Room 7 capture/report inventory.
    -Full additionally runs synthetic + selected private tests and re-renders
    the captured Room 7 scene into a NEW FIXTURE/OUTPUT directory.
    No game files are modified. No git fetch/merge/reset/push is performed.
    No private captures or frame images are uploaded to GitHub.
.NOTES
    CI uses -CheckSyntax only. CI does not prove the private fixture result.
#>
[CmdletBinding()]
param(
    [string] $WorkspaceRoot = 'F:\Dev\SCUMMBUCKET',
    [switch] $Full,
    [switch] $OpenPreview,
    [switch] $CheckSyntax,
    [switch] $CheckPythonRuntime
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($CheckSyntax -and $CheckPythonRuntime) {
    throw 'Choose either -CheckSyntax or -CheckPythonRuntime, not both.'
}
if ($CheckSyntax) {
    Write-Output 'P4 private acceptance script parsed successfully (no fixtures accessed).'
    return
}
function Assert-PillowAvailable {
    # The -c argument deliberately contains no embedded double quotes.
    # Windows PowerShell 5.1 strips those quotes when invoking native Python.
    & python -B -c 'import PIL; print(PIL.__version__)'
    if ($LASTEXITCODE -ne 0) {
        throw 'Python cannot import Pillow: install the project [gif] optional dependency for this interpreter.'
    }
}
if ($CheckPythonRuntime) {
    Assert-PillowAvailable
    Write-Output 'P4 Python/Pillow native invocation passed (no private fixtures accessed).'
    return
}
if ($OpenPreview -and -not $Full) {
    throw '-OpenPreview requires -Full so a fresh verified preview is generated.'
}

$root = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$repo = Join-Path $root 'SOURCE\ScummBucket'
$fixture = Join-Path $root 'FIXTURE'
$expectedBranch = 'research/p4-engine-palette-trace'

if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw "Missing workspace root: $root"
}
$folders = @(Get-ChildItem -LiteralPath $root -Directory | Select-Object -ExpandProperty Name)
$missing = @('SOURCE', 'TOOLS', 'FIXTURE') | Where-Object { $_ -notin $folders }
$extra = $folders | Where-Object { $_ -notin @('SOURCE', 'TOOLS', 'FIXTURE') }
if (@($missing).Count -or @($extra).Count) {
    throw "Workspace layout differs from approved three folders; missing: $($missing -join ', '); extra: $($extra -join ', ')"
}
if (-not (Test-Path -LiteralPath (Join-Path $repo '.git'))) {
    throw "Missing repository at $repo"
}

function Invoke-GitVerified {
    param([string[]] $Arguments)
    $lines = @(& git -C $repo @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Git operation failed: git $($Arguments -join ' ')"
    }
    return $lines
}
$currentBranch = (Invoke-GitVerified -Arguments @('branch', '--show-current') | Out-String).Trim()
if ($currentBranch -ne $expectedBranch) {
    throw "Expected local branch $expectedBranch but found $currentBranch"
}
$dirty = @(Invoke-GitVerified -Arguments @('status', '--porcelain'))
if ($dirty.Count) {
    throw "Checkout is dirty; refusing to run. Review 'git status' before retrying."
}
$head = (Invoke-GitVerified -Arguments @('rev-parse', 'HEAD') | Out-String).Trim()
$tracking = (Invoke-GitVerified -Arguments @('rev-parse', '--verify', "refs/remotes/origin/$expectedBranch") | Out-String).Trim()
if ($head -ne $tracking) {
    throw "Local HEAD $head differs from last fetched origin/$expectedBranch $tracking; inspect and fast-forward separately."
}
Write-Host "Clean research checkout: $head"

$preflight = Join-Path $repo 'tools\room7_work_preflight.py'
if (-not (Test-Path -LiteralPath $preflight -PathType Leaf)) {
    throw "Missing read-only preflight: $preflight"
}
$raw = @(& python -B $preflight --root $root --hash-frames)
if ($LASTEXITCODE -ne 0) {
    Write-Host ($raw -join [Environment]::NewLine)
    throw 'Room 7 read-only preflight failed.'
}
$report = ($raw -join [Environment]::NewLine) | ConvertFrom-Json
foreach ($check in $report.checks) {
    if ($check.severity -eq 'warning' -or $check.severity -eq 'error') {
        Write-Warning "$($check.code): $($check.detail)"
    }
}
Write-Host "Preflight status: $($report.status)"
if (-not $Full) {
    Write-Host 'Read-only preflight complete. No frame outputs generated.'
    return
}
if ($report.status -ne 'ready') {
    throw 'Private full acceptance is blocked: preflight is not ready. Resolve warnings/errors rather than skipping missing fixtures.'
}

$game = Join-Path $fixture 'GAMES\MonkeyIsland2_DOS_VGA'
$normal = Join-Path $fixture 'CAPTURES\Room23\walk-20261110-a-normal'
$control = Join-Path $fixture 'CAPTURES\Room23\walk-20261110-a-control'
$costumeReport = Join-Path $fixture 'REPORTS\Room23\walk-20261110-a.json'
foreach ($path in @($game, $normal, $control)) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "Required private regression fixture missing: $path"
    }
}
if (-not (Test-Path -LiteralPath $costumeReport -PathType Leaf)) {
    throw "Required Room 23 costume regression evidence missing: $costumeReport"
}
Assert-PillowAvailable

$envNames = @('SCUMMBUCKET_MI2_ARCHIVE', 'SCUMMBUCKET_MI2_GAME', 'SCUMMBUCKET_WALK_NORMAL', 'SCUMMBUCKET_WALK_CONTROL', 'SCUMMBUCKET_COSTUME_FIXTURE')
$previous = @{}
foreach ($key in $envNames) {
    $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
[Environment]::SetEnvironmentVariable('SCUMMBUCKET_MI2_ARCHIVE', $game, 'Process')
[Environment]::SetEnvironmentVariable('SCUMMBUCKET_MI2_GAME', $game, 'Process')
[Environment]::SetEnvironmentVariable('SCUMMBUCKET_WALK_NORMAL', $normal, 'Process')
[Environment]::SetEnvironmentVariable('SCUMMBUCKET_WALK_CONTROL', $control, 'Process')
# test_classic_costume.py uses the fixture root to compare 87 original
# Room 23 normal/control engine frames; a missing variable silently SKIPS it.
[Environment]::SetEnvironmentVariable('SCUMMBUCKET_COSTUME_FIXTURE', $fixture, 'Process')

Push-Location $repo
try {
    & python -B -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw 'Unit/private fixture tests failed: do not accept the P4 integration.'
    }

    $utc = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
    $outDir = Join-Path $fixture ("OUTPUT\Room7\acceptance-" + $utc)
    if (Test-Path -LiteralPath $outDir) {
        throw "Refusing to overwrite previous output: $outDir"
    }
    & python -B -m tools.verify_room7_scene $fixture $outDir
    if ($LASTEXITCODE -ne 0) {
        throw "Room 7 independent composition failed. Partial evidence, if any, remains at $outDir"
    }

    $manifestPath = Join-Path $outDir 'manifest.json'
    $previewPath = Join-Path $outDir 'preview.html'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $previewPath -PathType Leaf)) {
        throw 'Verifier did not produce the expected manifest and portable preview.'
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $frames = @($manifest.frames)
    $mismatchCount = 0
    $unmaskedCount = 0
    foreach ($frame in $frames) {
        $mismatchCount += [int] $frame.mismatches
        $unmaskedCount += [int] $frame.unmasked
    }
    $pngCount = @(Get-ChildItem -LiteralPath $outDir -Filter 'frame-*.png' -File).Count
    $html = Get-Content -LiteralPath $previewPath -Raw -Encoding UTF8
    if ($frames.Count -ne 87 -or $pngCount -ne 87 -or $mismatchCount -ne 0 -or
        $unmaskedCount -ne 778 -or $manifest.entry -ne 'debugger-equivalent Room 23 save jump' -or
        -not $html.Contains('data:image/png;base64,')) {
        throw "Acceptance mismatch: frames=$($frames.Count), PNGs=$pngCount, indexed=$mismatchCount, unmasked=$unmaskedCount, embedded=$($html.Contains('data:image/png;base64,'))"
    }

    Write-Host 'P4 full regression passed for the pinned debugger-equivalent Room 7 capture.' -ForegroundColor Green
    Write-Host 'Compared 87 x 320 x 144 indexed pixels = 4,008,960; zero mismatches.'
    Write-Host "Disabling ZP01 yields $unmaskedCount mismatches, as expected."
    Write-Host "New private output: $outDir"
    Write-Host "Standalone preview: $previewPath"
    if ($OpenPreview) {
        Start-Process -FilePath $previewPath
        Write-Warning 'Preview opened/requested. Human visual playback confirmation is still required.'
    }
}
finally {
    Pop-Location
    foreach ($key in $envNames) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')
    }
}
