#requires -Version 5.1
<#
.SYNOPSIS
Experiment A2: refine entrance timings based on owner's listening feedback.
.DESCRIPTION
Makes three unchanged reference snippets and five candidate clips:
Inn/Laundry: 1.5 or 2 bars earlier; Carpenter: 1.5 bars earlier.
Wally's already-good one-bar-early result is not regenerated.
Uses the existing 10-bar Woodtick suite and decoded original-bank recordings.
No game archive access, no mutation of previous suite or extracted WAVs.
Carpenter -> Woodtick exit at ~3:39 is the good control, untouched.
.EXAMPLE
.\tools\mi2se_woodtick_entrance_a2.ps1 -ListOnly
.EXAMPLE
.\tools\mi2se_woodtick_entrance_ab.ps1
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = 'F:\Dev\SCUMMBUCKET',
    [string]$SuiteManifest = '',
    [switch]$ListOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$bar = [decimal]3.539
$outputRoot = Join-Path $WorkspaceRoot 'FIXTURE\OUTPUT\MI2SE_Music'
$reports = Join-Path $WorkspaceRoot 'FIXTURE\REPORTS\MI2SE_Music'
$toolsDir = Join-Path $WorkspaceRoot 'TOOLS'

# The specific 4:07.730 Room10Bars suite is mandatory: never silently compare
# against a prior 8-bar suite or a different creative arrangement.
if (-not $SuiteManifest) {
    $found = @(Get-ChildItem -LiteralPath $reports -File -Filter 'MI2SE_CREATIVE_Woodtick_Village_Suite_Original_Room10Bars_*.json')
    if ($found.Count -ne 1) {
        throw "Expected one original Room10Bars manifest in $reports; found $($found.Count). Pass -SuiteManifest with its exact path."
    }
    $SuiteManifest = $found[0].FullName
}
if (-not (Test-Path -LiteralPath $SuiteManifest -PathType Leaf)) {
    throw "Suite manifest missing: $SuiteManifest"
}
try {
    $m = Get-Content -LiteralPath $SuiteManifest -Raw | ConvertFrom-Json
} catch {
    throw "Suite manifest is not valid JSON: $($_.Exception.Message)"
}
if ([string]$m.Type -ne 'CREATIVE_COMPOSITION_NOT_ENGINE_VERIFIED' -or
    [string]$m.Bank -ne 'MusicOriginal.xwb') {
    throw 'This experiment accepts only the original-bank creative suite manifest.'
}
if ([math]::Abs([double]$m.ActualSeconds - 247.730) -gt 0.15) {
    throw 'Expected the original 10-bar-room ~4:07.730 suite, not another arrangement.'
}
$chapters = @($m.Chapters)
$sources = @($m.Sources)
if ($chapters.Count -ne 11) { throw "Expected 11 chapters, got $($chapters.Count)." }
foreach ($chapter in @($chapters | Where-Object { [int]$_.SoundId -ne 101 })) {
    if ([int]$chapter.Bars -ne 10) {
        throw "Non-10-bar interior chapter detected: $($chapter.Name)"
    }
}
if ($sources.Count -ne 6) { throw "Expected six source WAV references." }
$suite = [string]$m.OutputFile
if (-not (Test-Path -LiteralPath $suite -PathType Leaf)) { throw "Full suite WAV missing: $suite" }

$filesById = @{}
foreach ($s in $sources) {
    [int]$id = 0
    if (-not [int]::TryParse(([string]$s.Cue -replace '^track',''),[ref]$id)) {
        throw "Unexpected source cue name: $($s.Cue)"
    }
    if ($filesById.ContainsKey($id)) { throw "Duplicate source cue ID $id in provenance." }
    $path = Join-Path $outputRoot ([string]$s.File)
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Source WAV missing: $path" }
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($hash -ine [string]$s.SHA256) {
        throw "Source WAV hash mismatch for $($s.Cue): $path"
    }
    $filesById[$id] = $path
}
$fullHash = (Get-FileHash -LiteralPath $suite -Algorithm SHA256).Hash
if ($m.PSObject.Properties.Name -contains 'OutputSHA256') {
    if ($fullHash -ine [string]$m.OutputSHA256) {
        throw "Suite WAV hash differs from its provenance. No audio written."
    }
}
foreach ($id in @(101,152,110,104,111)) {
    if (-not $filesById.ContainsKey($id)) { throw "Missing WAV for cue $id" }
}

# Experiment A2:
# - Wally's 1-bar-earlier entrance was accepted by listener; do not change.
# - Inn and Laundry need an additional 0.5 or 1 bar earlier than A1.
# - Carpenter entrance is still late and needs 0.5 bar earlier than A1.
# - Carpenter exit at 3:39.418 remains an unchanged listening control.
# The Bar is not part of this bounded A2.
$targets = @(
    [pscustomobject]@{ Id=152; Label='Inn'; Shifts=@([decimal]1.5,[decimal]2.0) },
    [pscustomobject]@{ Id=110; Label='Laundromat'; Shifts=@([decimal]1.5,[decimal]2.0) },
    [pscustomobject]@{ Id=111; Label='Carpenter'; Shifts=@([decimal]1.5) }
)
$windowBars = [decimal]7
$plan = New-Object 'System.Collections.Generic.List[object]'
foreach ($target in $targets) {
    $incoming = @($chapters | Where-Object { [int]$_.SoundId -eq $target.Id })
    if ($incoming.Count -ne 1) { throw "Expected one incoming chapter $($target.Id)." }
    [int]$idx = [int]$incoming[0].Number - 1
    if ($idx -le 0 -or $idx -ge $chapters.Count) { throw "Bad chapter index for $($target.Label)." }
    $outgoing = $chapters[$idx - 1]
    if ([int]$outgoing.SoundId -ne 101) {
        throw "Expected outgoing Woodtick before $($target.Label); got $($outgoing.Name)."
    }
    [decimal]$t = [decimal]$incoming[0].SuiteStartSeconds
    [decimal]$start = $t - [decimal]3*$bar
    [decimal]$end = $t + [decimal]4*$bar
    if ($start + [decimal]0.002 -lt [decimal]$outgoing.SuiteStartSeconds) {
        throw "Not enough Woodtick before $($target.Label) for a 7-bar listening clip."
    }
    [decimal]$woodtickSourceStart = [decimal]$outgoing.SourceStartSeconds +
        ($start - [decimal]$outgoing.SuiteStartSeconds)
    if ($woodtickSourceStart -lt [decimal]0) {
        throw "Negative Woodtick source start for $($target.Label)."
    }
    foreach ($shift in $target.Shifts) {
        [decimal]$shiftBars = [decimal]$shift
        [decimal]$woodBars = [decimal]4 - $shiftBars
        [decimal]$roomBars = [decimal]4 + $shiftBars
        if ([math]::Abs([double]($woodBars+$roomBars-[decimal]1-$windowBars)) -gt 0.00001) {
            throw "Invalid composition math for $($target.Label), shift $shiftBars."
        }
        $plan.Add([pscustomobject]@{
            Number=[int]$incoming[0].Number
            Id=[int]$target.Id
            Label=[string]$target.Label
            ShiftBars=[double]$shiftBars
            SuiteTransitionStartS=[double]$t
            CandidateTransitionStartS=[double]($t - $shiftBars*$bar)
            ClipStartSuiteS=[double]$start
            ClipEndSuiteS=[double]$end
            ClipLengthS=[double]($windowBars*$bar)
            WoodtickSourceStartS=[double]$woodtickSourceStart
            WoodtickSourceExcerptS=[double]($woodBars*$bar)
            RoomSourceStartS=0.0
            RoomSourceExcerptS=[double]($roomBars*$bar)
            RoomSourceCue="track$($target.Id)"
        })
    }
}
Write-Host 'MI2SE Experiment A2 -- further half-/full-bar entrance adjustments' -ForegroundColor Cyan
Write-Host 'Baseline: exact 7-bar listening excerpt from existing suite.' 
Write-Host 'Candidates: one-bar crossfade begins 1.5 or 2 bars earlier, room source starts at 0s.'
Write-Host 'Original 4:07 suite, Wally accepted result, Bar, and Carpenter EXIT around 3:39 are unchanged.'
$plan.ToArray() | Format-Table Label,ShiftBars,SuiteTransitionStartS,CandidateTransitionStartS,ClipStartSuiteS,ClipEndSuiteS -AutoSize
if ($ListOnly) { Write-Host 'ListOnly: no audio files created.'; return }

$cmd = Get-Command 'ffmpeg.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
$ffmpeg = if ($null -ne $cmd) { [string]$cmd.Source } else { '' }
if (-not $ffmpeg) {
    $exe = Get-ChildItem -LiteralPath $toolsDir -Filter 'ffmpeg.exe' -File -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $exe) { $ffmpeg = [string]$exe.FullName }
}
if (-not $ffmpeg) { throw 'FFmpeg not found; no output files created.' }
$ffprobe = Join-Path (Split-Path -Parent $ffmpeg) 'ffprobe.exe'
if (-not (Test-Path -LiteralPath $ffprobe -PathType Leaf)) { throw "ffprobe.exe missing beside $ffmpeg" }

# Validate decoded source lengths so FFmpeg cannot silently shorten clips.
$durationMap = @{}
foreach ($id in @(101,152,110,104,111)) {
    $p = $filesById[$id]
    $probeText = (& $ffprobe -v error -show_entries format=duration -of json $p | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed for $p" }
    $durationMap[$id] = [double]::Parse([string]($probeText | ConvertFrom-Json).format.duration,$culture)
}
foreach ($item in $plan) {
    if ([double]$item.WoodtickSourceStartS + [double]$item.WoodtickSourceExcerptS + 0.005 -gt [double]$durationMap[101]) {
        throw "Woodtick is too short for $($item.Label) comparison."
    }
    if ([double]$item.RoomSourceExcerptS + 0.005 -gt [double]$durationMap[$item.Id]) {
        throw "Room source is too short for $($item.Label) comparison."
    }
}
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fffffff'
$runDir = Join-Path $outputRoot ("MI2SE_ExperimentA2_Entrances_$stamp")
$reportPath = Join-Path $reports ("MI2SE_ExperimentA2_Entrances_$stamp.json")
if (Test-Path -LiteralPath $runDir) { throw "Refusing output directory overwrite: $runDir" }
if (Test-Path -LiteralPath $reportPath) { throw "Refusing report overwrite: $reportPath" }
New-Item -ItemType Directory -Path $runDir | Out-Null

function Format-Seconds([double]$s) { return ([decimal]$s).ToString('0.000000',$culture) }
function Invoke-CheckedRender([string[]]$renderArgs, [string]$path) {
    & $ffmpeg @renderArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "FFmpeg failed; any partial outputs are retained in $runDir. Failed: $path"
    }
    $txt = (& $ffprobe -v error -show_entries format=duration -of json $path | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "Could not probe $path" }
    $actual = [double]::Parse([string]($txt | ConvertFrom-Json).format.duration,$culture)
    if ([math]::Abs($actual - (7*[double]$bar)) -gt 0.05) {
        throw "Duration mismatch ($actual seconds) for $path; retain file for investigation."
    }
    return [pscustomobject]@{
        Name=(Split-Path -Path $path -Leaf)
        Bytes=(Get-Item -LiteralPath $path).Length
        DurationSeconds=$actual
        SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    }
}

$results = New-Object 'System.Collections.Generic.List[object]'
$baselineCache = @{}
$fade = Format-Seconds ([double]$bar)
foreach ($item in $plan) {
    $stem = 'T{0:D2}_{1}' -f $item.Number,$item.Label
    $baseline = Join-Path $runDir ($stem + '_BASELINE.wav')
    if (-not $baselineCache.ContainsKey($item.Id)) {
        # Baseline is the exact, unaltered seven-bar excerpt of the suite.
        $clipStart = Format-Seconds ([double]$item.ClipStartSuiteS)
        $clipDuration = Format-Seconds ([double]$item.ClipLengthS)
        $baselineGraph = "[0:a]atrim=start=$($clipStart):duration=$($clipDuration),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[out]"
        $baseArgs = @('-hide_banner','-nostdin','-n','-i',$suite,
            '-filter_complex',$baselineGraph,'-map','[out]',
            '-ar','44100','-c:a','pcm_s16le',$baseline)
        Write-Host "BASELINE: $($item.Label)" -ForegroundColor Cyan
        $baselineCache[$item.Id] = Invoke-CheckedRender $baseArgs $baseline
    }
    $shiftLabel = ([decimal]$item.ShiftBars).ToString('0.0',$culture).Replace('.','P')
    $candidate = Join-Path $runDir ($stem + "_EARLY$($shiftLabel)BARS_PICKUP.wav")

    # Fixed seven-bar window. 1.5-bar early: Woodtick 2.5 bars +
    # incoming room 5.5 bars minus 1-bar crossfade = 7 bars.
    # 2-bar early: Woodtick 2 bars + room 6 bars - fade 1 = 7.
    $woodStart = Format-Seconds ([double]$item.WoodtickSourceStartS)
    $woodDuration = Format-Seconds ([double]$item.WoodtickSourceExcerptS)
    $roomDuration = Format-Seconds ([double]$item.RoomSourceExcerptS)
    $candidateGraph =
        "[0:a]atrim=start=$($woodStart):duration=$($woodDuration),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a];" +
        "[1:a]atrim=start=0:duration=$($roomDuration),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[b];" +
        "[a][b]acrossfade=d=$($fade):c1=tri:c2=tri[out]"
    $newArgs = @('-hide_banner','-nostdin','-n',
        '-i',$filesById[101],'-i',$filesById[$item.Id],
        '-filter_complex',$candidateGraph,'-map','[out]',
        '-ar','44100','-c:a','pcm_s16le',$candidate)
    Write-Host ("CANDIDATE: {0}, {1} bars earlier" -f $item.Label,$item.ShiftBars) -ForegroundColor Cyan
    $a = Invoke-CheckedRender $newArgs $candidate
    $results.Add([pscustomobject]@{
        Label=$item.Label
        SoundId=$item.Id
        ShiftBars=$item.ShiftBars
        OriginalTransitionStartSuiteSeconds=$item.SuiteTransitionStartS
        CandidateTransitionStartSuiteSeconds=$item.CandidateTransitionStartS
        WindowStartSuiteSeconds=$item.ClipStartSuiteS
        WindowEndSuiteSeconds=$item.ClipEndSuiteS
        Original=$baselineCache[$item.Id]
        Candidate=$a
    })
}
$manifest = [ordered]@{
    Type='CREATIVE_AB_TEST_NOT_ENGINE_VERIFIED'
    Name='Experiment A2 - listening-led 1.5/2-bar entrance refinements'
    SuiteManifest=$SuiteManifest
    SuiteSHA256=$fullHash
    InputSources=$sources
    SamplesPerSecond=44100
    BarSeconds=[double]$bar
    Baseline='Exact excerpt from existing full 10-bar-room suite'
    Candidate='1.5/2 bars earlier entrance with a 1-bar crossfade, room source starts at 0.000s'
    PickupCaveat='The source pickup is present in the incoming fade; early low gain can still make it hard to hear.'
    UnchangedReference='Carpenter -> Woodtick, suite 3:39.418-3:42.957, is not modified'
    SeparateKnownIssue='Woodtick -> Carpenter entrance needs another 0.5 bar earlier beyond A1. Good 3:39 Carpenter return is untouched.'
    ClipWindowBars=7
    ClipLengthSeconds=[double]([decimal]7*$bar)
    PreviewPlan=@($plan.ToArray())
    Results=@($results.ToArray())
    FfmpegExecutable=$ffmpeg
    GeneratedUTC=[DateTime]::UtcNow.ToString('o')
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "EXPERIMENT A WAV CLIPS: $runDir" -ForegroundColor Green
Write-Host "PROVENANCE: $reportPath" -ForegroundColor Green
Write-Host "Eight 7-bar WAVs rendered: three baselines plus five timing variants. Compare each room against its baseline and A1."
