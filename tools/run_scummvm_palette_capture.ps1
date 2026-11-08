# Run a private Room 23 engine capture, then import and verify its real palette log.
# Does not modify original game archives or the normal installed ScummVM.
[CmdletBinding()]
param(
    [ValidateSet('normal','stress')]
    [string]$Mode = 'normal',
    [string]$Checkout = (Join-Path $HOME 'ScummVM-P4-Trace'),
    [string]$GameDirectory = 'D:\old\mi2'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$exe = Join-Path $Checkout 'scummvm.exe'
$resource = Join-Path $GameDirectory 'MONKEY2.001'
$index = Join-Path $GameDirectory 'MONKEY2.000'
$expectedResource = 'ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e'

if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Patched ScummVM executable not found: $exe. Build it first with build_scummvm_trace_msys2.sh."
}
if (-not (Test-Path -LiteralPath $resource -PathType Leaf) -or
    -not (Test-Path -LiteralPath $index -PathType Leaf)) {
    throw "Required original MI2 game data not found under $GameDirectory."
}
$actualHash = (Get-FileHash -LiteralPath $resource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $expectedResource) {
    throw "Archive fingerprint mismatch: $actualHash. No capture launched."
}
foreach ($tool in @('python', 'git')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Required command missing: $tool"
    }
}
$engineCommit = (& git -C $Checkout rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $engineCommit.Trim().Length -ne 40) {
    throw 'Cannot identify patched ScummVM source commit'
}
$engineCommit = $engineCommit.Trim().ToLowerInvariant()

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$exportDir = Join-Path $repoRoot 'exports'
$reportDir = Join-Path $repoRoot 'reports'
New-Item -ItemType Directory -Force -Path $exportDir, $reportDir | Out-Null
$raw = Join-Path $exportDir "room23-$Mode-$stamp.raw.log"
$trace = Join-Path $reportDir "room23-$Mode-$stamp.trace.json"
$report = Join-Path $reportDir "room23-$Mode-$stamp.verify.json"
if (Test-Path -LiteralPath $raw) { throw "Output collision: $raw" }

$oldPath = $env:PATH
$oldCapture = $env:SCUMMBUCKET_PALETTE_TRACE_PATH
$ucrtBin = 'C:\msys64\ucrt64\bin'

Write-Host ''
Write-Host "Starting patched engine: $exe"
Write-Host "Private log destination: $raw"
Write-Host "Capture type: $Mode"
if ($Mode -eq 'normal') {
    Write-Host 'In the ScummVM debugger: scumm_vars[19] 6 ; room 23'
    Write-Host 'Remain in Room 23 for at least 256 updates, approximately 26 seconds.'
} else {
    Write-Host 'In the ScummVM debugger: scumm_vars[19] 60 ; room 23'
    Write-Host 'At 1 Hz, 256 updates take about 4.3 minutes. Alternatively, after several updates'
    Write-Host 'change to a nonzero room (for example room 22), then continue to close the log.'
}
Write-Host 'Room 23 changes scenes and automatically closes the debugger; do not add continue.'
Write-Host 'Use the patched ScummVM window, not the normal ScummVM shortcut.'
Write-Host ''

try {
    $env:SCUMMBUCKET_PALETTE_TRACE_PATH = $raw
    if (Test-Path -LiteralPath (Join-Path $ucrtBin 'SDL2.dll')) {
        $env:PATH = "$ucrtBin;$oldPath"
    }
    # ScummVM can use the Windows GUI subsystem. Start-Process -Wait prevents
    # the verifier from racing the still-running engine or its raw trace file.
    $engineProcess = Start-Process -FilePath $exe -WorkingDirectory $Checkout -Wait -PassThru
    Write-Host "ScummVM exit code: $($engineProcess.ExitCode)"
} finally {
    $env:PATH = $oldPath
    if ($null -eq $oldCapture) {
        Remove-Item Env:SCUMMBUCKET_PALETTE_TRACE_PATH -ErrorAction SilentlyContinue
    } else {
        $env:SCUMMBUCKET_PALETTE_TRACE_PATH = $oldCapture
    }
}

if (-not (Test-Path -LiteralPath $raw -PathType Leaf)) {
    throw 'No trace file was created. Verify that the patched build ran and reached DOS VGA MI2 Room 23.'
}
$lastLine = Get-Content -LiteralPath $raw -Tail 1
Write-Host "Raw trace last line: $lastLine"
if ($lastLine -notmatch '^SBP4[|]END[|][0-9]+[|](limit|room_exit)$') {
    Write-Warning 'Capture is incomplete. Raw log is preserved. No success report will be claimed.'
    Write-Host "Preserved log: $raw"
    exit 2
}

Push-Location $repoRoot
try {
    & python -m scummbucket import-scummvm-palette-log $raw --resource-file $resource --engine-commit $engineCommit --expected-source-sha256 $expectedResource --output $trace
    if ($LASTEXITCODE -ne 0) {
        throw "Trace import failed. Preserve the raw log and diagnostics: $raw"
    }
    Write-Host "Imported trace: $trace"
    & python -m scummbucket verify-palette-trace $GameDirectory --room 23 --trace $trace --output $report --json
    $verifyExit = $LASTEXITCODE
    Write-Host "Verification report: $report"
    if ($verifyExit -ne 0) {
        Write-Warning 'Palette verification reported a mismatch or error. This is a research finding, not a successful match.'
        exit $verifyExit
    }
    Write-Host 'Palette comparison completed successfully. Inspect the report for limitations.'
} finally {
    Pop-Location
}
