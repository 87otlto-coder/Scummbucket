# P4 cross-room private acceptance. Windows PowerShell 5.1 compatible.
# All original SCUMM game files and existing TOOLS builds remain read-only.
# Run only from the canonical F:\Dev\SCUMMBUCKET workspace.
[CmdletBinding()]
param(
    [ValidateSet('Room23','Preflight','Build','Capture','Compare')]
    [string]$Stage = 'Preflight',
    [string]$BuildName,
    [string]$CaptureDirectory,
    [switch]$CheckSyntax
)

$ErrorActionPreference = 'Stop'
if ($CheckSyntax) {
    Write-Host 'P4 cross-room PowerShell syntax: accepted'
    return
}

$root = 'F:\Dev\SCUMMBUCKET'
$repo = Join-Path $root 'SOURCE\ScummBucket'
if (-not (Test-Path -LiteralPath $repo -PathType Container)) {
    throw "Canonical repository not present: $repo"
}
Set-Location -LiteralPath $repo

$expectedBranch = 'research/p5-cross-room-reconstruction'
$actualBranch = (& git branch --show-current)
if ($LASTEXITCODE -ne 0 -or $actualBranch.Trim() -ne $expectedBranch) {
    throw "Expected branch $expectedBranch, found $actualBranch. Do not switch automatically."
}
$changes = @(& git status --porcelain)
if ($LASTEXITCODE -ne 0) { throw 'Git status failed' }
if ($changes.Count -gt 0) { throw 'Uncommitted changes; inspect before continuing' }

$fx = Join-Path $root 'FIXTURE'
$game = Join-Path $fx 'GAMES\MonkeyIsland2_DOS_VGA'

if ($Stage -eq 'Room23') {
    $native = Join-Path $fx 'OUTPUT\Room23\native-mixed-20261110-v1'
    $raw = Join-Path $fx 'CAPTURES\Room23\room23-normal-20261110-081315-043.raw.log'
    foreach ($file in @(
        (Join-Path $native 'manifest.json'),
        $raw,
        (Join-Path $game 'MONKEY2.000'),
        (Join-Path $game 'MONKEY2.001')
    )) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Missing historical Room 23 evidence: $file"
        }
    }
    $player = Join-Path $native 'play-standalone.html'
    $manifest = Join-Path $native 'animation.json'
    $playerExists = Test-Path -LiteralPath $player
    $manifestExists = Test-Path -LiteralPath $manifest
    if ($playerExists -ne $manifestExists) {
        throw 'Incomplete earlier portable package. Preserve files; do not overwrite'
    }
    if (-not $playerExists) {
        & python -B -m tools.package_room23_portable_animation $native --raw-log $raw --game $game
        if ($LASTEXITCODE -ne 0) {
            throw 'Room 23 packaging failed; preserve original evidence'
        }
    }
    & python -B -m tools.verify_room23_portable_animation $native --raw-log $raw --game $game
    if ($LASTEXITCODE -ne 0) { throw 'Room 23 private verification failed' }
    Write-Host 'ROOM 23 PORTABLE ACCEPTANCE PASSED'
    Write-Host "Verified manifest: $manifest"
    Write-Host "Offline preview: $player"
    return
}

if ($Stage -eq 'Preflight') {
    & python -B -m tools.build_cross_room_recorder --root $root --check-only
    if ($LASTEXITCODE -ne 0) { throw 'Cross-room recorder read-only preflight failed' }
    Write-Host 'CROSS-ROOM BUILD PREFLIGHT PASSED (not linked or runtime verified)'
    return
}

if ($Stage -eq 'Build') {
    & python -B -m tools.build_cross_room_recorder --root $root
    if ($LASTEXITCODE -ne 0) {
        throw 'Cross-room build failed. Preserve new TOOLS directories/logs; original is untouched'
    }
    Write-Host 'NEW BUILD PRODUCED; NO RUNTIME CAPTURE YET'
    Write-Host 'Use the BuildName from the printed build_dir for the Capture stage'
    return
}

if ($Stage -eq 'Capture') {
    if ([string]::IsNullOrWhiteSpace($BuildName)) {
        throw 'Capture requires -BuildName ScummVM-P4-CrossRoom-<unique-suffix>'
    }
    & python -B -m tools.capture_cross_room --root $root --build $BuildName
    if ($LASTEXITCODE -ne 0) {
        throw 'Cross-room capture incomplete. Preserve raw CAPTURES and REPORTS for review'
    }
    Write-Host 'CROSS-ROOM INDEXED CAPTURE ACCEPTED; ROOM 12 SCENE FIDELITY NOT YET VERIFIED'
    return
}

if ($Stage -eq 'Compare') {
    if ([string]::IsNullOrWhiteSpace($CaptureDirectory)) {
        throw 'Compare requires -CaptureDirectory with an existing private cross-room capture'
    }
    $capture = (Resolve-Path -LiteralPath $CaptureDirectory -ErrorAction Stop).Path
    $expected = Join-Path $fx 'CAPTURES\Room7'
    $expected = [System.IO.Path]::GetFullPath($expected)
    $capture = [System.IO.Path]::GetFullPath($capture)
    if (-not $capture.StartsWith(($expected.TrimEnd('\') + '\'), [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Cross-room comparison input must be inside FIXTURE\CAPTURES\Room7'
    }
    $out = Join-Path $fx ('REPORTS\P5\room12-indexed-' + [guid]::NewGuid().ToString('N'))
    Write-Host "Non-overwriting comparison output: $out"
    & python -B -m tools.compare_cross_room_scene --game $game --capture $capture --output $out
    if ($LASTEXITCODE -ne 0) {
        throw "Room 12 scene still has mismatches or unsupported states; preserve report in $out"
    }
    Write-Host 'ROOM 12 RECORDED-ROUTE INDEXED COMPOSITION MATCHED'
    return
}

throw "Unexpected acceptance stage: $Stage"
