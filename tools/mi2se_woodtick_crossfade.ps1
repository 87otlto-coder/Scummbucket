#requires -Version 5.1
<#
.SYNOPSIS
Creates a short, creative Woodtick-to-Bar crossfade from already extracted MI2SE WAVs.
.DESCRIPTION
An EXPERIMENTAL listening edit, not a verified Special Edition XACT transition or DOS iMUSE replay.
Uses the documented 3.539 s shared bar length and 0.442 s offset for sounds 101 and 103.
Does not read or alter XWB archives; never overwrites existing outputs.
Requires FFmpeg, either on PATH or installed under the canonical TOOLS directory.
.EXAMPLE
.\tools\mi2se_woodtick_crossfade.ps1 -Variant Original
.EXAMPLE
.\tools\mi2se_woodtick_crossfade.ps1 -Variant New
#>
[CmdletBinding()]
param(
    [ValidateSet('Original', 'New')]
    [string]$Variant = 'Original',

    [string]$WorkspaceRoot = 'F:\Dev\SCUMMBUCKET'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$inputDir = Join-Path $WorkspaceRoot 'FIXTURE\OUTPUT\MI2SE_Music'
$toolsDir = Join-Path $WorkspaceRoot 'TOOLS'

if ($Variant -eq 'Original') {
    $woodtickName = 'MusicOriginal_track101_stream_0002.wav'
    $barName = 'MusicOriginal_track103_stream_0003.wav'
} else {
    $woodtickName = 'MusicNew_Woodtick_101_stream_0014.wav'
    $barName = 'MusicNew_Bar_103_stream_0016.wav'
}

$woodtick = Join-Path $inputDir $woodtickName
$bar = Join-Path $inputDir $barName
foreach ($source in @($woodtick, $bar)) {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Required decoded WAV not found: $source"
    }
}

$command = Get-Command 'ffmpeg.exe' -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
$ffmpeg = ''
if ($null -ne $command) {
    $ffmpeg = [string]$command.Source
} elseif (Test-Path -LiteralPath $toolsDir -PathType Container) {
    $found = Get-ChildItem -LiteralPath $toolsDir -Filter 'ffmpeg.exe' -File -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $found) {
        $ffmpeg = [string]$found.FullName
    }
}
if (-not $ffmpeg) {
    throw "FFmpeg not found on PATH or in $toolsDir. Install FFmpeg under TOOLS and retry; no file was changed."
}

$outputName = 'MI2SE_CREATIVE_Woodtick_to_Bar_{0}_9bars.wav' -f $Variant
$outputPath = Join-Path $inputDir $outputName
$manifestPath = [System.IO.Path]::ChangeExtension($outputPath, '.json')
foreach ($target in @($outputPath, $manifestPath)) {
    if (Test-Path -LiteralPath $target) {
        throw "Refusing to overwrite existing output: $target"
    }
}

# Observed Special Edition implementation CSV: 101 and 103 use the same 3.539 s
# bar period and 0.442 s offset. This is an ARTISTIC alignment hypothesis.
# Use 5 bars of each cue; overlap the last/first 1 bar for a 9-bar listening clip.
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$barSeconds = [decimal]3.539
$offsetSeconds = [decimal]0.442
$clipSeconds = [decimal]5 * $barSeconds
$fadeSeconds = $barSeconds

$offsetText = $offsetSeconds.ToString('0.000', $culture)
$clipText = $clipSeconds.ToString('0.000', $culture)
$fadeText = $fadeSeconds.ToString('0.000', $culture)

# Resample the WAVs to the SAME rate to accommodate decoder-reported 44100/44101 Hz.
# acrossfade does not emulate music segment scheduling or iMUSE's event control.
$graph = "[0:a]atrim=start=$($offsetText):duration=$($clipText),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a];" +
         "[1:a]atrim=start=$($offsetText):duration=$($clipText),asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[b];" +
         "[a][b]acrossfade=d=$($fadeText):c1=tri:c2=tri[out]"

Write-Host "Creating a creative $Variant Woodtick-to-Bar crossfade."
Write-Host "Inputs: $woodtickName / $barName"
Write-Host "Bar: $fadeText s; offset: $offsetText s; five bars per cue."
Write-Host "Expected output: approximately $([decimal]9 * $barSeconds) seconds."

& $ffmpeg -hide_banner -nostdin -n -i $woodtick -i $bar -filter_complex $graph -map '[out]' -ar 44100 -c:a pcm_s16le $outputPath
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "FFmpeg exited $exitCode. Any partial output is left untouched for inspection: $outputPath"
}
if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
    throw "FFmpeg exited successfully but no WAV was produced: $outputPath"
}
$outputBytes = (Get-Item -LiteralPath $outputPath).Length
if ($outputBytes -le 44) {
    throw "WAV appears empty or truncated ($outputBytes bytes): $outputPath"
}

$manifest = [ordered]@{
    Type = 'CREATIVE_EXPERIMENT_NOT_ENGINE_VERIFIED'
    Game = 'Monkey Island 2 Special Edition'
    BankVariant = $Variant
    Source101 = $woodtickName
    Source101SHA256 = (Get-FileHash -LiteralPath $woodtick -Algorithm SHA256).Hash
    Source103 = $barName
    Source103SHA256 = (Get-FileHash -LiteralPath $bar -Algorithm SHA256).Hash
    SourceImplementation = 'MI2_MUSIC_IMPLEMENTATION.csv'
    ImplementationEvidence = 'track101/track103: Bar-sync, bar 3.539 seconds, offset 0.442 seconds'
    AudioMethod = 'FFmpeg atrim + aresample + one-bar linear acrossfade'
    BarSeconds = [double]$barSeconds
    StartOffsetSeconds = [double]$offsetSeconds
    BarsPerInput = 5
    CrossfadeBars = 1
    ExpectedDurationSeconds = [double]([decimal]9 * $barSeconds)
    ObservedWavBytes = $outputBytes
    OutputSHA256 = (Get-FileHash -LiteralPath $outputPath -Algorithm SHA256).Hash
    FfmpegExecutable = $ffmpeg
    ExportedAtUTC = [DateTime]::UtcNow.ToString('o')
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "CREATIVE WAV: $outputPath" -ForegroundColor Green
Write-Host "PROVENANCE JSON: $manifestPath"
