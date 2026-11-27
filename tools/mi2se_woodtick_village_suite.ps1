#requires -Version 5.1
<#
.SYNOPSIS
Produce a creative 11-section Woodtick village suite from MI2SE MusicOriginal.xwb.
.DESCRIPTION
Returns to Woodtick between Inn, Bar, Laundry, Wally, and Carpenter.
Not a reconstruction of DOS iMUSE or Special Edition XACT transitions.
Does not modify original game archives or overwrite existing WAVs.
.EXAMPLE
.\tools\mi2se_woodtick_village_suite.ps1 -ListOnly
.EXAMPLE
.\tools\mi2se_woodtick_village_suite.ps1
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = 'F:\Dev\SCUMMBUCKET',
    [string]$InventoryCsv = '',
    [switch]$ListOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$bank = Join-Path $WorkspaceRoot 'FIXTURE\mi2remastered\audio_extracted\MusicOriginal.xwb'
$decoder = Join-Path $WorkspaceRoot 'TOOLS\vgmstream\vgmstream-cli.exe'
$outputDir = Join-Path $WorkspaceRoot 'FIXTURE\OUTPUT\MI2SE_Music'
$reportDir = Join-Path $WorkspaceRoot 'FIXTURE\REPORTS\MI2SE_Music'
$toolsDir = Join-Path $WorkspaceRoot 'TOOLS'

foreach ($required in @($bank,$decoder)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing required file: $required"
    }
}
if (-not $InventoryCsv) {
    $candidateFiles = @(Get-ChildItem -LiteralPath $reportDir -Filter 'MI2SE_CueMap_*.csv' -File |
        Sort-Object LastWriteTime -Descending)
    if ($candidateFiles.Count -eq 0) { throw "Cue inventory missing in $reportDir" }
    $InventoryCsv = $candidateFiles[0].FullName
}
if (-not (Test-Path -LiteralPath $InventoryCsv -PathType Leaf)) {
    throw "Cue inventory missing: $InventoryCsv"
}
$inventory = @(Import-Csv -LiteralPath $InventoryCsv)
if ($inventory.Count -eq 0) { throw 'Cue inventory empty.' }
foreach ($key in @('Bank','Stream','CueName')) {
    if ($inventory[0].PSObject.Properties.Name -notcontains $key) {
        throw "Cue inventory missing column: $key"
    }
}

# Shared bar timing documented for all six selected cue IDs in
# MI2_MUSIC_IMPLEMENTATION.csv. Treat edits as creative, not engine-observed.
$bar = [decimal]3.539
$offset = [decimal]0.442
$sections = @(
    [pscustomobject]@{Name='Woodtick - Opening';      Id=101; Bars=6; StartBar=0},
    [pscustomobject]@{Name='Swamp Rot Inn';           Id=152; Bars=8; StartBar=0},
    [pscustomobject]@{Name='Woodtick - Interlude 1';  Id=101; Bars=4; StartBar=6},
    [pscustomobject]@{Name='Bloody Lip Bar';          Id=103; Bars=8; StartBar=0},
    [pscustomobject]@{Name='Woodtick - Interlude 2';  Id=101; Bars=4; StartBar=10},
    [pscustomobject]@{Name='Laundromat';              Id=110; Bars=8; StartBar=0},
    [pscustomobject]@{Name='Woodtick - Interlude 3';  Id=101; Bars=4; StartBar=14},
    [pscustomobject]@{Name='Wally - Cartographer';    Id=104; Bars=8; StartBar=0},
    [pscustomobject]@{Name='Woodtick - Interlude 4';  Id=101; Bars=4; StartBar=18},
    [pscustomobject]@{Name='Carpenter - Woodsmith';   Id=111; Bars=8; StartBar=0},
    [pscustomobject]@{Name='Woodtick - Closing';      Id=101; Bars=8; StartBar=22}
)
$resolved = @{}
foreach ($id in @($sections | ForEach-Object { $_.Id } | Sort-Object -Unique)) {
    $name = "track$id"
    $matches = @($inventory | Where-Object {
        $_.Bank -eq 'MusicOriginal.xwb' -and $_.CueName -ceq $name
    })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one original cue $name. Found $($matches.Count)."
    }
    [int]$stream = 0
    if (-not [int]::TryParse([string]$matches[0].Stream,[ref]$stream) -or $stream -le 0) {
        throw "Invalid stream index for $name"
    }
    $filename = 'MusicOriginal_{0}_stream_{1:D4}.wav' -f $name,$stream
    $resolved[$id] = [pscustomobject]@{
        SoundId=$id; Cue=$name; Stream=$stream; FileName=$filename;
        Path=(Join-Path $outputDir $filename)
    }
}
$totalBars = [decimal](($sections | Measure-Object -Property Bars -Sum).Sum)
$expected = ($totalBars - [decimal]($sections.Count - 1)) * $bar
$chapters = New-Object 'System.Collections.Generic.List[object]'
$timeline = [decimal]0
for ($i=0; $i -lt $sections.Count; $i++) {
    $section = $sections[$i]
    if ($i -gt 0) { $timeline -= $bar }
    $start = $offset + [decimal]$section.StartBar * $bar
    $length = [decimal]$section.Bars * $bar
    $chapters.Add([pscustomobject]@{
        Number=($i+1); Name=$section.Name; SoundId=$section.Id
        Cue=$resolved[$section.Id].Cue; Stream=$resolved[$section.Id].Stream
        SourceStartSeconds=[double]$start
        SourceDurationSeconds=[double]$length
        SuiteStartSeconds=[double]$timeline
        Bars=$section.Bars
    })
    $timeline += $length
}
if ([math]::Abs([double]($timeline - $expected)) -gt 0.001) {
    throw 'Internal timeline mismatch.'
}
Write-Host "WOODTICK COMPLETE VILLAGE SUITE (Original-bank creative arrangement)" -ForegroundColor Cyan
$chapters.ToArray() | Format-Table Number,Name,SoundId,SuiteStartSeconds -AutoSize
Write-Host ("Expected runtime: {0} seconds" -f $expected.ToString('0.000',$culture))
if ($ListOnly) {
    foreach ($source in @($resolved.Values | Sort-Object SoundId)) {
        Write-Host ("ORIGINAL CUE {0}: {1}, stream {2}" -f $source.SoundId,$source.Cue,$source.Stream)
        $newPattern = '^mx{0}_SE_' -f $source.SoundId
        $newCandidates = @($inventory | Where-Object {
            $_.Bank -eq 'MusicNew.xwb' -and $_.CueName -match $newPattern
        })
        $examples = @($newCandidates | Select-Object -First 4 -ExpandProperty CueName)
        if ($newCandidates.Count -gt 0) {
            Write-Host ("  Remastered naming evidence ({0} entries): {1}" -f $newCandidates.Count,($examples -join ', '))
        } else {
            Write-Warning "No matching New-bank cue names for sound $($source.SoundId); location label requires listening confirmation."
        }
    }
    Write-Host 'Plan only: no audio decoded or written.'
    return
}

$found = Get-Command 'ffmpeg.exe' -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
$ffmpeg = ''
if ($null -ne $found) { $ffmpeg = [string]$found.Source }
if (-not $ffmpeg) {
    $found = Get-ChildItem -LiteralPath $toolsDir -Filter 'ffmpeg.exe' -File -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $found) { $ffmpeg = [string]$found.FullName }
}
if (-not $ffmpeg) { throw "ffmpeg.exe not found on PATH or under $toolsDir" }
$ffprobe = Join-Path (Split-Path -Path $ffmpeg -Parent) 'ffprobe.exe'
if (-not (Test-Path -LiteralPath $ffprobe -PathType Leaf)) {
    throw "ffprobe.exe missing alongside FFmpeg: $ffprobe"
}

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$sources = New-Object 'System.Collections.Generic.List[object]'
foreach ($source in @($resolved.Values | Sort-Object SoundId)) {
    $metadataText = (& $decoder -m -I -s $source.Stream $bank | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "Decoder metadata failed for $($source.Cue)" }
    try { $metadata = $metadataText | ConvertFrom-Json }
    catch { throw "Invalid JSON metadata for $($source.Cue)" }
    if ([string]$metadata.streamInfo.name -cne $source.Cue) {
        throw "Cue mismatch: $($source.Cue), bank reports $($metadata.streamInfo.name)"
    }
    if (-not (Test-Path -LiteralPath $source.Path -PathType Leaf)) {
        Write-Host "DECODING: $($source.Cue)" -ForegroundColor Cyan
        & $decoder -i -s $source.Stream -o $source.Path $bank
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $source.Path -PathType Leaf)) {
            throw "Decoder failed for $($source.Cue); any partial WAV remains for inspection."
        }
    } else {
        Write-Host "REUSING (unverified WAV): $($source.Path)"
    }
    if ((Get-Item -LiteralPath $source.Path).Length -le 44) {
        throw "WAV too small: $($source.Path)"
    }
    $probe = (& $ffprobe -v error -show_entries format=duration -of json $source.Path | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed for $($source.Path)" }
    try {
        $wavDuration = [double]::Parse([string]($probe | ConvertFrom-Json).format.duration,$culture)
    } catch { throw "Cannot parse WAV duration for $($source.Cue)" }
    $maxNeeded = [double]0
    foreach ($section in @($sections | Where-Object { $_.Id -eq $source.SoundId })) {
        $needed = [double]($offset + [decimal]$section.StartBar * $bar + [decimal]$section.Bars * $bar)
        if ($needed -gt $maxNeeded) { $maxNeeded = $needed }
    }
    if ($wavDuration + 0.02 -lt $maxNeeded) {
        throw "WAV $($source.Cue) is $wavDuration seconds; needs $maxNeeded. No padding or looping will be faked."
    }
    $sources.Add([pscustomobject]@{
        Cue=$source.Cue; Stream=$source.Stream; File=$source.FileName
        DurationSeconds=$wavDuration
        SHA256=(Get-FileHash -LiteralPath $source.Path -Algorithm SHA256).Hash
    })
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fffffff'
$baseName = "MI2SE_CREATIVE_Woodtick_Village_Suite_Original_$stamp"
$wavOut = Join-Path $outputDir ($baseName + '.wav')
$jsonOut = Join-Path $reportDir ($baseName + '.json')
foreach ($target in @($wavOut,$jsonOut)) {
    if (Test-Path -LiteralPath $target) { throw "Refusing overwrite: $target" }
}
$arguments = New-Object 'System.Collections.Generic.List[string]'
foreach ($p in @('-hide_banner','-nostdin','-n')) { $arguments.Add($p) }
$filters = New-Object 'System.Collections.Generic.List[string]'
for ($i=0; $i -lt $chapters.Count; $i++) {
    $chapter = $chapters[$i]
    $arguments.Add('-i')
    $arguments.Add($resolved[[int]$chapter.SoundId].Path)
    $s = ([decimal]$chapter.SourceStartSeconds).ToString('0.000',$culture)
    $d = ([decimal]$chapter.SourceDurationSeconds).ToString('0.000',$culture)
    $filters.Add(('[{0}:a]atrim=start={1}:duration={2},asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[s{0}]' -f $i,$s,$d))
}
$previous = 's0'
$fade = $bar.ToString('0.000',$culture)
for ($i=1; $i -lt $chapters.Count; $i++) {
    $next = "m$i"
    $filters.Add(('['+$previous+'][s'+$i+']acrossfade=d='+$fade+':c1=tri:c2=tri['+$next+']'))
    $previous = $next
}
$endFadeAt = ($expected - [decimal]2.000).ToString('0.000',$culture)
$filters.Add(('['+$previous+']afade=t=in:st=0:d=0.25,afade=t=out:st='+$endFadeAt+':d=2.000[out]'))
$graph = $filters.ToArray() -join ';'
foreach ($p in @('-filter_complex',$graph,'-map','[out]','-ar','44100','-c:a','pcm_s16le',$wavOut)) {
    $arguments.Add($p)
}
Write-Host "Rendering creative suite: $wavOut" -ForegroundColor Cyan
$ffmpegArguments = $arguments.ToArray()
& $ffmpeg @ffmpegArguments
$code = $LASTEXITCODE
if ($code -ne 0 -or -not (Test-Path -LiteralPath $wavOut -PathType Leaf)) {
    throw "FFmpeg failed (exit $code); partial output, if any, remains in place: $wavOut"
}
$outputProbe = (& $ffprobe -v error -show_entries format=duration -of json $wavOut | Out-String)
if ($LASTEXITCODE -ne 0) { throw "Could not verify rendered WAV duration." }
$actual = [double]::Parse([string]($outputProbe | ConvertFrom-Json).format.duration,$culture)
if ([math]::Abs($actual - [double]$expected) -gt 0.10) {
    throw "Duration mismatch: expected $expected, actual $actual. WAV retained for inspection."
}

$provenance = [ordered]@{
    Type='CREATIVE_COMPOSITION_NOT_ENGINE_VERIFIED'
    Title='Woodtick - The Complete Village Suite'
    Bank='MusicOriginal.xwb'
    Game='Monkey Island 2 Special Edition'
    BarLengthSeconds=[double]$bar; BarOffsetSeconds=[double]$offset
    Crossfade='One bar, linear, via FFmpeg; NOT verified iMUSE/XACT'
    ExpectedSeconds=[double]$expected; ActualSeconds=$actual
    CueInventory=$InventoryCsv
    Chapters=@($chapters.ToArray())
    Sources=@($sources.ToArray())
    FfmpegExecutable=$ffmpeg
    OutputFile=$wavOut
    OutputBytes=(Get-Item -LiteralPath $wavOut).Length
    OutputSHA256=(Get-FileHash -LiteralPath $wavOut -Algorithm SHA256).Hash
    CreatedUTC=[DateTime]::UtcNow.ToString('o')
}
$provenance | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonOut -Encoding UTF8
Write-Host "SUITE WAV: $wavOut" -ForegroundColor Green
Write-Host "PROVENANCE: $jsonOut" -ForegroundColor Green
Write-Host ("DURATION: {0} seconds" -f $actual.ToString('0.000',$culture))
