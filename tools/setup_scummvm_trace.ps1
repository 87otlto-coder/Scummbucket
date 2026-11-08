# Prepare a separate, pinned ScummVM source tree for P4 Room 23 tracing.
# Run from Windows PowerShell. This DOES NOT build or launch ScummVM.
[CmdletBinding()]
param(
    [string]$Checkout = (Join-Path $HOME 'ScummVM-P4-Trace')
)

$ErrorActionPreference = 'Stop'
$patcher = Join-Path $PSScriptRoot 'instrument_scummvm_palette.py'
$expectedTag = 'v2026.4.0'
$target = Join-Path $Checkout 'engines\scumm\scumm.cpp'
$backup = "$target.scummbucket-p4-original"

if (-not (Test-Path -LiteralPath $patcher -PathType Leaf)) {
    throw "ScummBucket patcher missing: $patcher. Update research/p4-engine-palette-trace."
}
foreach ($command in @('git', 'python')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $command"
    }
}

if (-not (Test-Path -LiteralPath $Checkout)) {
    Write-Host "Cloning pinned ScummVM $expectedTag into $Checkout"
    & git clone --depth 1 --single-branch --branch $expectedTag https://github.com/scummvm/scummvm.git $Checkout
    if ($LASTEXITCODE -ne 0) { throw 'ScummVM clone failed; no patch attempted' }
} elseif (-not (Test-Path -LiteralPath (Join-Path $Checkout '.git'))) {
    throw "Checkout directory exists but is not a Git repository: $Checkout"
}

$head = (& git -C $Checkout rev-parse HEAD)
if ($LASTEXITCODE -ne 0) { throw 'Cannot read ScummVM HEAD' }
$tagCommit = (& git -C $Checkout rev-parse 'refs/tags/v2026.4.0^{commit}')
if ($LASTEXITCODE -ne 0) { throw 'Pinned ScummVM tag not available in checkout' }
if ($head.Trim() -ne $tagCommit.Trim()) {
    throw "Checkout is not pinned to $expectedTag ($tagCommit); HEAD is $head. No patch attempted."
}

if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    throw "Expected source file missing: $target"
}

$alreadyPatched = Select-String -LiteralPath $target -SimpleMatch 'SCUMMBUCKET_P4_PALETTE_TRACE_V1' -Quiet

if ($alreadyPatched) {
    if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) {
        throw "Source is marked as instrumented but its original backup is missing: $backup"
    }
    Write-Host 'Already instrumented; leaving existing patched source unchanged.'
} else {
    Write-Host 'Checking pinned source fingerprint and hook insertion points...'
    & python $patcher $Checkout --check
    if ($LASTEXITCODE -ne 0) { throw 'Patcher preflight failed; source not modified' }
    & python $patcher $Checkout --apply
    if ($LASTEXITCODE -ne 0) { throw 'Patcher failed; check output before compiling' }
}
Write-Host ""
Write-Host "ScummVM commit: $($head.Trim())"
Write-Host "Instrumented source: $target"
Write-Host 'Your existing installed ScummVM and original game files were not modified.'
Write-Host ""
if (Test-Path -LiteralPath 'C:\msys64\ucrt64.exe') {
    Write-Host 'MSYS2 UCRT64 detected. The next step is its minimal SCUMM-only build.'
} else {
    Write-Host 'MSYS2 UCRT64 not detected in C:\msys64.'
    Write-Host 'Install MSYS2 from https://www.msys2.org/ or use upstream Visual Studio build instructions.'
}
