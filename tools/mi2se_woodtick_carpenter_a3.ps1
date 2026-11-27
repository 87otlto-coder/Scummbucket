#requires -Version 5.1
<#
.SYNOPSIS
Experiment A3: isolate the Woodtick-to-Carpenter entrance at 1.75 and 2 bars early.
.DESCRIPTION
Makes one original reference WAV and two candidates from the verified Room10Bars
suite. Preserves the preceding Wally-to-Woodtick transition and does NOT change
the accepted Carpenter-to-Woodtick exit near 3:39. Original WAVs stay read-only.
.EXAMPLE
.\tools\mi2se_woodtick_carpenter_a3.ps1 -ListOnly
.EXAMPLE
.\tools\mi2se_woodtick_carpenter_a3.ps1
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

if (-not $SuiteManifest) {
    $available = @(Get-ChildItem -LiteralPath $reports -File -Filter 'MI2SE_CREATIVE_Woodtick_Village_Suite_Original_Room10Bars_*.json' |
        Sort-Object FullName)
    if ($available.Count -ne 1) {
        throw "Expected one Room10Bars suite manifest; found $($available.Count). Supply the exact -SuiteManifest path."
    }
    $SuiteManifest = $available[0].FullName
}
if (-not (Test-Path -LiteralPath $SuiteManifest -PathType Leaf)) {
    throw "Missing suite manifest: $SuiteManifest"
}
try {
    $m = Get-Content -LiteralPath $SuiteManifest -Raw | ConvertFrom-Json
} catch {
    throw "Invalid suite JSON: $($_.Exception.Message)"
}
if ([string]$m.Type -ne 'CREATIVE_COMPOSITION_NOT_ENGINE_VERIFIED' -or
    [string]$m.Bank -ne 'MusicOriginal.xwb' -or
    [math]::Abs([double]$m.ActualSeconds - 247.730) -gt 0.15) {
    throw 'Wrong suite. Experiment A3 accepts the original-bank 4:07.730 Room10Bars rendering only.'
}
$sections = @($m.Chapters)
if ($sections.Count -ne 11) { throw "Wrong chapter count: $($sections.Count)" }
$carpenter = @($sections | Where-Object { [int]$_.SoundId -eq 111 })
if ($carpenter.Count -ne 1 -or [int]$carpenter[0].Number -ne 10) {
    throw "Expected Carpenter entrance at section 10."
}
$wood = $sections[8]
if ([int]$wood.SoundId -ne 101 -or [int]$wood.Number -ne 9) {
    throw 'Expected Woodtick section 9 immediately before Carpenter.'
}
$previous = $sections[7]
if ([int]$previous.SoundId -ne 104) {
    throw 'Expected Wally before the reference Woodtick interlude.'
}
$closing = $sections[10]
if ([int]$closing.SoundId -ne 101 -or
    [math]::Abs([double]$closing.SuiteStartSeconds - 219.418) -gt 0.02) {
    throw 'Good Carpenter-to-Woodtick exit moved; refusing test.'
}
$suite = [string]$m.OutputFile
if (-not (Test-Path -LiteralPath $suite -PathType Leaf)) { throw "Suite WAV missing: $suite" }
if (-not $m.OutputSHA256) { throw "Suite manifest lacks SHA256." }
$suiteHash = (Get-FileHash -LiteralPath $suite -Algorithm SHA256).Hash
if ($suiteHash -ine [string]$m.OutputSHA256) {
    throw 'Suite SHA256 does not match provenance.'
}
$sources = @($m.Sources | Where-Object { $_.Cue -ceq 'track111' })
if ($sources.Count -ne 1) { throw "Expected exactly one Carpenter recording." }
if ([string]$sources[0].File -cne 'MusicOriginal_track111_stream_0014.wav') {
    throw "Unexpected Carpenter recording: $($sources[0].File)"
}
$roomPath = Join-Path $outputRoot ([string]$sources[0].File)
if (-not (Test-Path -LiteralPath $roomPath -PathType Leaf)) {
    throw "Carpenter WAV missing: $roomPath"
}
if ((Get-FileHash -LiteralPath $roomPath -Algorithm SHA256).Hash -ine [string]$sources[0].SHA256) {
    throw 'Carpenter source hash does not match the suite provenance.'
}
[decimal]$original = [decimal]$carpenter[0].SuiteStartSeconds
[decimal]$clipStart = [decimal]$wood.SuiteStartSeconds
[decimal]$clipEnd = $original + [decimal]4*$bar
[decimal]$clipLen = $clipEnd-$clipStart
$shifts = @([decimal]1.75,[decimal]2.0)
$plans = New-Object 'System.Collections.Generic.List[object]'
foreach ($shift in $shifts) {
    [decimal]$begin = $original-$shift*$bar
    [decimal]$wallyToWoodtickEnds = $clipStart + $bar
    if ($begin + [decimal]0.001 -lt $wallyToWoodtickEnds) {
        throw "Carpenter -$shift bars starts before Wally-to-Woodtick fade has ended; refusing overlapping fades."
    }
    [decimal]$prefixDuration = $begin+$bar-$clipStart
    [decimal]$roomDuration = $clipEnd-$begin
    if ([math]::Abs([double]($prefixDuration+$roomDuration-$bar-$clipLen)) -gt 0.00001) {
        throw 'Internal clip-duration inconsistency.'
    }
    $plans.Add([pscustomobject]@{
        Room='Carpenter'
        ShiftBars=[double]$shift
        OriginalStartSeconds=[double]$original
        CandidateStartSeconds=[double]$begin
        ClipStartSeconds=[double]$clipStart
        ClipEndSeconds=[double]$clipEnd
        ClipDurationSeconds=[double]$clipLen
        SuitePrefixDurationSeconds=[double]$prefixDuration
        RoomExcerptDurationSeconds=[double]$roomDuration
    })
}
Write-Host 'Experiment A3: Woodtick to Carpenter only' -ForegroundColor Cyan
Write-Host 'Inn (-2 bars), Laundry (-2 bars), Wally (-1 bar) are listener-selected and are not altered.'
Write-Host 'The suite prefix retains the Wally-to-Woodtick crossfade, rather than replacing it with isolated Woodtick.'
Write-Host 'The Carpenter-to-Woodtick EXIT at 3:39.418 remains unchanged.'
$plans.ToArray() | Format-Table ShiftBars,OriginalStartSeconds,CandidateStartSeconds,ClipStartSeconds,ClipEndSeconds -AutoSize
if ($ListOnly) { Write-Host 'ListOnly: no WAVs written.'; return }

$command = Get-Command ffmpeg.exe -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
$ffmpeg = if ($null -ne $command) { [string]$command.Source } else { '' }
if (-not $ffmpeg) {
    $command = Get-ChildItem -LiteralPath $toolsDir -Recurse -Filter ffmpeg.exe -File -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $command) { $ffmpeg = [string]$command.FullName }
}
if (-not $ffmpeg) { throw 'FFmpeg missing.' }
$ffprobe = Join-Path (Split-Path -Parent $ffmpeg) 'ffprobe.exe'
if (-not (Test-Path -LiteralPath $ffprobe -PathType Leaf)) { throw "ffprobe missing: $ffprobe" }
$probeText = (& $ffprobe -v error -show_entries format=duration -of json $roomPath | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Carpenter WAV.' }
$sourceSeconds = [double]::Parse([string]($probeText | ConvertFrom-Json).format.duration,$culture)
foreach ($plan in $plans) {
    if ([double]$plan.RoomExcerptDurationSeconds + 0.02 -gt $sourceSeconds) {
        throw "Carpenter source is shorter than the proposed excerpt."
    }
}
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fffffff'
$runDir = Join-Path $outputRoot ("MI2SE_ExperimentA3_Carpenter_$stamp")
$report = Join-Path $reports ("MI2SE_ExperimentA3_Carpenter_$stamp.json")
if ((Test-Path -LiteralPath $runDir) -or (Test-Path -LiteralPath $report)) {
    throw 'Refusing existing output/report overwrite.'
}
New-Item -ItemType Directory -Path $runDir | Out-Null

function Seconds([decimal]$value) { return $value.ToString('0.000000',$culture) }
function Render([string[]]$ffArgs, [string]$target) {
    & $ffmpeg @ffArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw "FFmpeg failed; preserve any partial output under $runDir : $target"
    }
    $durationJson = (& $ffprobe -v error -show_entries format=duration -of json $target | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed: $target" }
    [double]$duration = [double]::Parse([string]($durationJson | ConvertFrom-Json).format.duration,$culture)
    if ([math]::Abs($duration-[double]$clipLen) -gt 0.05) {
        throw "Output WAV duration mismatch for $target; preserve for inspection."
    }
    return [pscustomobject]@{
        FileName=(Split-Path -Leaf $target)
        DurationSeconds=$duration
        SizeBytes=(Get-Item -LiteralPath $target).Length
        SHA256=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
    }
}

$clipStartS=Seconds $clipStart
$clipLenS=Seconds $clipLen
$baselinePath=Join-Path $runDir 'T10_Carpenter_BASELINE.wav'
$baselineFilter="[0:a]atrim=start=$($clipStartS):duration=$($clipLenS),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[out]"
$baselineArgs=@('-hide_banner','-nostdin','-n','-i',$suite,
    '-filter_complex',$baselineFilter,'-map','[out]','-ar','44100','-c:a','pcm_s16le',$baselinePath)
$reference=Render $baselineArgs $baselinePath
$results=New-Object 'System.Collections.Generic.List[object]'
foreach ($plan in $plans) {
    $shift=[decimal]$plan.ShiftBars
    $label=$shift.ToString('0.00',$culture).Replace('.','P')
    $destination=Join-Path $runDir ("T10_Carpenter_EARLY$($label)BARS_PICKUP.wav")
    $prefix=Seconds ([decimal]$plan.SuitePrefixDurationSeconds)
    $room=Seconds ([decimal]$plan.RoomExcerptDurationSeconds)
    $crossfade=Seconds $bar
    $filter="[0:a]atrim=start=$($clipStartS):duration=$($prefix),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[p];" +
        "[1:a]atrim=start=0:duration=$($room),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[c];" +
        "[p][c]acrossfade=d=$($crossfade):c1=tri:c2=tri[out]"
    $arguments=@('-hide_banner','-nostdin','-n','-i',$suite,'-i',$roomPath,
        '-filter_complex',$filter,'-map','[out]','-ar','44100','-c:a','pcm_s16le',$destination)
    Write-Host ("A3 CANDIDATE: -{0} bars vs original entrance" -f $plan.ShiftBars) -ForegroundColor Cyan
    $rendered=Render $arguments $destination
    $results.Add([pscustomobject]@{
        ShiftBars=$plan.ShiftBars
        CandidateSuiteEntranceSeconds=$plan.CandidateStartSeconds
        Output=$rendered
    })
}
$manifest=[ordered]@{
    Type='CREATIVE_EXPERIMENT_A3_NOT_ENGINE_VERIFIED'
    Scope='Carpenter entrance timing only'
    BaselineSuiteManifest=$SuiteManifest
    BaselineSuiteSHA256=$suiteHash
    CarpenterSourceSHA256=(Get-FileHash -LiteralPath $roomPath -Algorithm SHA256).Hash
    BarSeconds=[double]$bar
    CrossfadeSeconds=[double]$bar
    WindowStartSuiteSeconds=[double]$clipStart
    WindowEndSuiteSeconds=[double]$clipEnd
    WindowDurationSeconds=[double]$clipLen
    PreservesPrecedingWallyToWoodtickFade=$true
    DoesNotModifyCarpenterExit=$true
    AcceptedOtherEntrances=@(
        @{Room='Inn';ShiftBars=-2.0},
        @{Room='Laundromat';ShiftBars=-2.0},
        @{Room='Wally';ShiftBars=-1.0}
    )
    OriginalReference=$reference
    Candidates=@($results.ToArray())
    FfmpegExecutable=$ffmpeg
    CreatedUTC=[DateTime]::UtcNow.ToString('o')
}
$manifest | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $report -Encoding UTF8
Write-Host "A3 comparison WAVs: $runDir" -ForegroundColor Green
Write-Host "Provenance JSON: $report" -ForegroundColor Green
