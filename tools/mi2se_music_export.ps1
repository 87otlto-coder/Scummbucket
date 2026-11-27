#requires -Version 5.1
<#
.SYNOPSIS
Exports selected Monkey Island 2: Special Edition music cues from locally owned XWB banks.
.DESCRIPTION
Uses the cue inventory produced by vgmstream and its companion XSB mapping.
Selects the exact original cue (trackNNN) and one remastered main loop
(mxNNN_SE_*_lp). Does not guess when mappings are missing or ambiguous.
Never modifies game input archives or overwrites previously exported WAVs.
.EXAMPLE
.\tools\mi2se_music_export.ps1 -ListOnly
.EXAMPLE
.\tools\mi2se_music_export.ps1 -SoundIds 101,103,162
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = 'F:\Dev\SCUMMBUCKET',
    [string]$InventoryCsv = '',
    [int[]]$SoundIds = @(101, 103, 162),
    [switch]$ListOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$decoder = Join-Path $WorkspaceRoot 'TOOLS\vgmstream\vgmstream-cli.exe'
$inputDir = Join-Path $WorkspaceRoot 'FIXTURE\mi2remastered\audio_extracted'
$outputDir = Join-Path $WorkspaceRoot 'FIXTURE\OUTPUT\MI2SE_Music'
$reportDir = Join-Path $WorkspaceRoot 'FIXTURE\REPORTS\MI2SE_Music'
$bankNames = @('MusicOriginal.xwb', 'MusicNew.xwb')

if (-not (Test-Path -LiteralPath $decoder -PathType Leaf)) {
    throw "Missing decoder: $decoder"
}
foreach ($bankName in $bankNames) {
    $bankPath = Join-Path $inputDir $bankName
    if (-not (Test-Path -LiteralPath $bankPath -PathType Leaf)) {
        throw "Missing music bank: $bankPath"
    }
}

if (-not $InventoryCsv) {
    if (-not (Test-Path -LiteralPath $reportDir -PathType Container)) {
        throw "Inventory folder missing: $reportDir"
    }
    $latest = Get-ChildItem -LiteralPath $reportDir -File -Filter 'MI2SE_CueMap_*.csv' |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $latest) {
        throw "No MI2SE_CueMap_*.csv in $reportDir; run the XSB/XWB inventory first."
    }
    $InventoryCsv = $latest.FullName
}
if (-not (Test-Path -LiteralPath $InventoryCsv -PathType Leaf)) {
    throw "Inventory not found: $InventoryCsv"
}

$inventory = @(Import-Csv -LiteralPath $InventoryCsv)
if ($inventory.Count -eq 0) {
    throw "Cue inventory is empty: $InventoryCsv"
}
foreach ($column in @('Bank', 'Stream', 'CueName')) {
    if ($inventory[0].PSObject.Properties.Name -notcontains $column) {
        throw "Cue inventory lacks required column: $column"
    }
}
if (@($SoundIds).Count -eq 0) {
    throw 'Supply at least one sound ID.'
}

function New-Result {
    param(
        [int]$Id, [string]$Bank, [string]$Stream, [string]$Cue,
        [string]$Status, [string]$Output, [string]$Detail, [string]$Metadata
    )
    [pscustomobject]@{
        SoundId = $Id
        Bank = $Bank
        Stream = $Stream
        CueName = $Cue
        Status = $Status
        OutputPath = $Output
        Detail = $Detail
        DecoderMetadataJson = $Metadata
    }
}

New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
if (-not $ListOnly) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$results = New-Object 'System.Collections.Generic.List[object]'

foreach ($soundId in @($SoundIds | Sort-Object -Unique)) {
    if ($soundId -lt 0) {
        throw "Invalid negative sound ID: $soundId"
    }
    foreach ($bankName in $bankNames) {
        # Deliberately select the main cue only, not _T transition segments.
        $pattern = if ($bankName -eq 'MusicOriginal.xwb') {
            '^track{0}$' -f $soundId
        } else {
            '^mx{0}_SE_.*_lp$' -f $soundId
        }
        $candidates = @($inventory | Where-Object {
            $_.Bank -eq $bankName -and $_.CueName -match $pattern
        })
        if ($candidates.Count -ne 1) {
            $status = if ($candidates.Count -eq 0) { 'MissingCue' } else { 'AmbiguousCue' }
            $details = "Expected exactly one cue matching $pattern; found $($candidates.Count)."
            Write-Warning "$bankName sound $soundId : $details"
            $results.Add((New-Result $soundId $bankName '' '' $status '' $details ''))
            continue
        }

        $cueName = [string]$candidates[0].CueName
        [int]$stream = 0
        $parsed = [int]::TryParse([string]$candidates[0].Stream, [ref]$stream)
        if (-not $parsed -or $stream -le 0) {
            $details = "Invalid stream number in inventory: $($candidates[0].Stream)"
            $results.Add((New-Result $soundId $bankName '' $cueName 'InvalidStream' '' $details ''))
            continue
        }

        $stem = [System.IO.Path]::GetFileNameWithoutExtension($bankName)
        $safeName = $cueName -replace '[^a-zA-Z0-9._-]', '_'
        $filename = '{0}_{1}_stream_{2:D4}.wav' -f $stem, $safeName, $stream
        $destination = Join-Path $outputDir $filename
        if ($ListOnly) {
            Write-Host ("MAP {0}: {1} stream {2} ({3})" -f $soundId, $bankName, $stream, $cueName)
            $results.Add((New-Result $soundId $bankName "$stream" $cueName 'MappedOnly' $destination '' ''))
            continue
        }

        $bankPath = Join-Path $inputDir $bankName
        try {
            # Recheck the actual bank before decoding; CSV names alone are insufficient.
            $metadataText = (& $decoder -m -I -s $stream $bankPath | Out-String)
            if ($LASTEXITCODE -ne 0) {
                throw "Decoder metadata failed with exit code $LASTEXITCODE"
            }
            $metadata = $metadataText | ConvertFrom-Json
            $actual = [string]$metadata.streamInfo.name
            if ($actual -cne $cueName) {
                throw "Bank reports cue '$actual', inventory expects '$cueName'."
            }

            # Previous manual exports used different descriptive names: detect by bank+stream.
            $existingPattern = '{0}_*_stream_{1:D4}.wav' -f $stem, $stream
            $existing = @(Get-ChildItem -LiteralPath $outputDir -File -Filter $existingPattern)
            if ($existing.Count -gt 0) {
                $details = "Existing WAV preserved (not revalidated): $($existing[0].FullName)"
                Write-Host "SKIP: $details"
                $results.Add((New-Result $soundId $bankName "$stream" $cueName 'AlreadyPresentUnverified' $existing[0].FullName $details $metadataText))
                continue
            }

            if (Test-Path -LiteralPath $destination) {
                throw "Output already exists: $destination"
            }
            & $decoder -i -s $stream -o $destination $bankPath
            $code = $LASTEXITCODE
            if ($code -ne 0 -or -not (Test-Path -LiteralPath $destination -PathType Leaf)) {
                throw "Audio decode failed (exit code $code); any partial output is left for inspection."
            }
            $size = (Get-Item -LiteralPath $destination).Length
            if ($size -le 44) {
                throw "Decoded output is unexpectedly small: $size bytes"
            }
            Write-Host "EXPORTED: $destination"
            $results.Add((New-Result $soundId $bankName "$stream" $cueName 'Exported' $destination "$size bytes" $metadataText))
        }
        catch {
            $details = $_.Exception.Message
            Write-Warning ("FAILED: {0} / {1} / {2}: {3}" -f $bankName, $soundId, $cueName, $details)
            $results.Add((New-Result $soundId $bankName "$stream" $cueName 'Failed' $destination $details ''))
        }
    }
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fffffff'
$manifest = Join-Path $reportDir "MI2SE_Export_$stamp.csv"
if (Test-Path -LiteralPath $manifest) {
    throw "Report exists, refusing to overwrite: $manifest"
}
$results.ToArray() | Export-Csv -LiteralPath $manifest -NoTypeInformation -Encoding UTF8
Write-Host "Manifest: $manifest"
$results.ToArray() | Select-Object SoundId, Bank, Stream, CueName, Status |
    Format-Table -AutoSize

$bad = @($results.ToArray() | Where-Object {
    $_.Status -in @('MissingCue', 'AmbiguousCue', 'InvalidStream', 'Failed')
})
if ($bad.Count -gt 0) {
    throw "$($bad.Count) cue(s) missing, ambiguous or failed; see manifest."
}
