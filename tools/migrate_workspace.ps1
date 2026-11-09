# Preview-first ScummBucket workspace migration. Copies files; never deletes sources.
# PowerShell: .\tools\migrate_workspace.ps1 [-Apply]
[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$Root = 'F:\Dev\SCUMMBUCKET',
    [string]$OldRepo = 'C:\Users\87otl\ScummBucket',
    [string]$OldEngine = 'C:\Users\87otl\ScummVM-P4-Trace',
    [string]$OldGame = 'D:\old\mi2'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$expectedHash = 'ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e'
$repoDest = Join-Path $Root 'SOURCE\ScummBucket'
$engineDest = Join-Path $Root 'TOOLS\ScummVM-P4-Trace'
$gameDest = Join-Path $Root 'FIXTURE\GAMES\MonkeyIsland2_DOS_VGA'
$captureDest = Join-Path $Root 'FIXTURE\CAPTURES\Room23'
$outputDest = Join-Path $Root 'FIXTURE\OUTPUT\LegacyExports'
$reportDest = Join-Path $Root 'FIXTURE\REPORTS\LegacyRepoReports'
$migrationDir = Join-Path $Root 'FIXTURE\REPORTS\Migration'

function Require-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" }
}
function Require-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Missing directory: $Path" }
}
function File-Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Verify-Identical([string]$Source, [string]$Dest) {
    Require-File $Source
    Require-File $Dest
    if ((File-Hash $Source) -ne (File-Hash $Dest)) { throw "SHA256 mismatch: $Source -> $Dest" }
}
function Ensure-Folder([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        [void](New-Item -Path $Path -ItemType Directory -Force)
    }
}
function Copy-Verified([string]$Source, [string]$Dest) {
    if (Test-Path -LiteralPath $Dest) {
        Verify-Identical $Source $Dest
        return
    }
    Ensure-Folder (Split-Path -Parent $Dest)
    Copy-Item -LiteralPath $Source -Destination $Dest -ErrorAction Stop
    Verify-Identical $Source $Dest
}
function Copy-FreshTree([string]$Source, [string]$Dest, [string[]]$SkipDirs = @(),
                        [string[]]$SkipFiles = @()) {
    if (Test-Path -LiteralPath $Dest) { throw "Destination already exists; refusing bulk overwrite: $Dest" }
    Ensure-Folder (Split-Path -Parent $Dest)
    $options = @('/E','/COPY:DAT','/DCOPY:DAT','/R:0','/W:0','/XJ','/NP','/NFL','/NDL')
    if ($SkipDirs.Count) { $options += '/XD'; $options += $SkipDirs }
    if ($SkipFiles.Count) { $options += '/XF'; $options += $SkipFiles }
    & robocopy $Source $Dest @options
    if ($LASTEXITCODE -ge 8) { throw "Robocopy failed with exit $LASTEXITCODE; partial copy retained at $Dest" }
}
function Copy-Legacy([string]$Source, [string]$Dest, [string]$Category) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) { return 0 }
    $count = 0
    $prefix = $Source.TrimEnd('\') + '\'
    foreach ($file in Get-ChildItem -LiteralPath $Source -File -Recurse -Force) {
        $raw = $file.Name -like '*.raw.log'
        if ($Category -eq 'raw' -and -not $raw) { continue }
        if ($Category -eq 'other' -and $raw) { continue }
        $relative = $file.FullName.Substring($prefix.Length)
        Copy-Verified $file.FullName (Join-Path $Dest $relative)
        $count++
    }
    return $count
}

Require-Directory $Root
$unexpected = @(Get-ChildItem -LiteralPath $Root -Force | Where-Object { $_.Name -notin @('SOURCE','TOOLS','FIXTURE') })
if ($unexpected.Count) { throw "Unexpected top-level entries under $Root; do not restructure without approval." }
Require-Directory $OldRepo
Require-Directory $OldEngine
Require-Directory $OldGame
Require-File (Join-Path $OldRepo '.git\HEAD')
Require-File (Join-Path $OldEngine 'scummvm.exe')
Require-File (Join-Path $OldEngine 'engines\scumm\scumm.cpp')
Require-File (Join-Path $OldGame 'MONKEY2.000')
Require-File (Join-Path $OldGame 'MONKEY2.001')
if ((File-Hash (Join-Path $OldGame 'MONKEY2.001')) -ne $expectedHash) {
    throw "Game edition fingerprint does not match validated original DOS VGA MI2."
}
if (-not (Select-String -LiteralPath (Join-Path $OldEngine 'engines\scumm\scumm.cpp') -SimpleMatch 'SCUMMBUCKET_P4_PALETTE_TRACE_V2' -Quiet)) {
    throw 'Instrumented V2 hook absent from source checkout.'
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required for repository verification.' }
$head = (& git -C $OldRepo rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $head.Trim().Length -ne 40) { throw 'Cannot read original ScummBucket commit.' }
$engineHead = (& git -C $OldEngine rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $engineHead.Trim().Length -ne 40) { throw 'Cannot read original engine commit.' }

Write-Host ""
Write-Host "Mode: $(if ($Apply) { 'COPY + VERIFY' } else { 'PREVIEW ONLY' })"
Write-Host "Repo: $OldRepo -> $repoDest"
Write-Host "Patched engine: $OldEngine -> $engineDest"
Write-Host "Original MI2: $OldGame -> $gameDest"
Write-Host "Existing raw captures: $captureDest"
Write-Host "Existing exports: $outputDest"
Write-Host "Existing reports: $reportDest"
Write-Host 'All old directories, game files and system-wide MSYS2 remain untouched.'
if (-not $Apply) {
    Write-Host 'PREVIEW_COMPLETE. Inspect paths, then re-run with -Apply.'
    return
}

foreach ($name in @('SOURCE','TOOLS','FIXTURE')) { Ensure-Folder (Join-Path $Root $name) }
foreach ($name in @('GAMES','CAPTURES','REFERENCE','OUTPUT','REPORTS')) {
    Ensure-Folder (Join-Path (Join-Path $Root 'FIXTURE') $name)
}

if (-not (Test-Path -LiteralPath $repoDest)) {
    $excludedFolders = @(
        (Join-Path $OldRepo 'exports'), (Join-Path $OldRepo 'reports'),
        (Join-Path $OldRepo '.venv'), (Join-Path $OldRepo 'venv'),
        (Join-Path $OldRepo '__pycache__'), (Join-Path $OldRepo '.pytest_cache'))
    $excludedFiles = @('*.000','*.001','*.zip','*.png','*.gif','*.webp',
                       '*.webm','*.mp4','*.wav','*.ogg','*.flac','*.mid',
                       '*.rom','*.exe','*.pyc')
    Copy-FreshTree $OldRepo $repoDest $excludedFolders $excludedFiles
} else {
    Write-Host 'Repository destination exists; checking tracked files, not overwriting.'
}
$newHead = (& git -C $repoDest rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $newHead.Trim() -ne $head.Trim()) { throw 'Repository HEAD mismatch.' }
$tracked = @(& git -C $OldRepo ls-files)
if ($LASTEXITCODE -ne 0) { throw 'Cannot enumerate tracked source files.' }
foreach ($relative in $tracked) {
    $name = $relative.Replace('/', '\')
    Verify-Identical (Join-Path $OldRepo $name) (Join-Path $repoDest $name)
}
Write-Host "Verified $($tracked.Count) tracked repository file hashes and commit."

if (-not (Test-Path -LiteralPath $engineDest)) {
    Copy-FreshTree $OldEngine $engineDest
} else {
    Write-Host 'Engine destination exists; checking critical files, not overwriting.'
}
Verify-Identical (Join-Path $OldEngine 'scummvm.exe') (Join-Path $engineDest 'scummvm.exe')
Verify-Identical (Join-Path $OldEngine 'engines\scumm\scumm.cpp') (Join-Path $engineDest 'engines\scumm\scumm.cpp')
$newEngineHead = (& git -C $engineDest rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $newEngineHead.Trim() -ne $engineHead.Trim()) { throw 'Engine checkout HEAD mismatch.' }
Write-Host 'Verified experimental ScummVM executable, hook source and source commit.'

if (-not (Test-Path -LiteralPath $gameDest)) {
    Copy-FreshTree $OldGame $gameDest
} else {
    Write-Host 'Game destination exists; checking every original file, not overwriting.'
}
$originalFiles = @(Get-ChildItem -LiteralPath $OldGame -File -Recurse -Force)
$sourcePrefix = $OldGame.TrimEnd('\') + '\'
foreach ($file in $originalFiles) {
    Verify-Identical $file.FullName (Join-Path $gameDest $file.FullName.Substring($sourcePrefix.Length))
}
$copiedFiles = @(Get-ChildItem -LiteralPath $gameDest -File -Recurse -Force)
if ($copiedFiles.Count -ne $originalFiles.Count) { throw 'Copied game file count differs.' }
Write-Host "Verified all $($originalFiles.Count) original MI2 file hashes."

$rawCount = Copy-Legacy (Join-Path $OldRepo 'exports') $captureDest 'raw'
$outputCount = Copy-Legacy (Join-Path $OldRepo 'exports') $outputDest 'other'
$reportCount = Copy-Legacy (Join-Path $OldRepo 'reports') $reportDest 'all'

Ensure-Folder $migrationDir
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$manifest = Join-Path $migrationDir "workspace-copy-$stamp.json"
if (Test-Path -LiteralPath $manifest) { throw "Report collision: $manifest" }
[ordered]@{
    status = 'copied_selected_files_verified_originals_retained'
    completed_at = (Get-Date).ToString('o')
    root = $Root
    source_repo = $OldRepo
    destination_repo = $repoDest
    repo_head = $newHead.Trim()
    tracked_files_verified = $tracked.Count
    source_engine = $OldEngine
    destination_engine = $engineDest
    engine_head = $newEngineHead.Trim()
    scummvm_exe_sha256 = (File-Hash (Join-Path $engineDest 'scummvm.exe'))
    source_game = $OldGame
    destination_game = $gameDest
    game_files_verified = $originalFiles.Count
    game_resource_sha256 = $expectedHash
    existing_raw_logs_copied = $rawCount
    existing_exports_copied = $outputCount
    existing_reports_copied = $reportCount
    originals_deleted = $false
    next_check = 'Run Python tests and a real patched-engine capture using new paths.'
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifest -Encoding UTF8 -NoNewline
Write-Host "COPY_VERIFIED. Manifest: $manifest"
Write-Host 'Existing files retained. Retire old locations only after separate runtime validation.'
