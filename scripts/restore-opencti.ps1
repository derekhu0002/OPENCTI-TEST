[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$BackupPath,
    [string]$OutputRoot = "backups",
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backupRoot = Join-Path $repoRoot $OutputRoot

function Invoke-Docker {
    param(
        [string[]]$Arguments
    )

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($Arguments -join ' ')"
    }
}

function Resolve-BackupDirectory {
    param(
        [string]$RequestedPath,
        [string]$DefaultRoot
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        $candidate = $RequestedPath
        if (-not [IO.Path]::IsPathRooted($candidate)) {
            $candidate = Join-Path $repoRoot $candidate
        }

        if (-not (Test-Path -LiteralPath $candidate -PathType Container)) {
            throw "Backup directory not found: $candidate"
        }

        return [IO.Path]::GetFullPath($candidate)
    }

    if (-not (Test-Path -LiteralPath $DefaultRoot -PathType Container)) {
        throw "Backup root not found: $DefaultRoot"
    }

    $latestBackup = Get-ChildItem -LiteralPath $DefaultRoot -Directory |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1

    if (-not $latestBackup) {
        throw "No backup directories found under $DefaultRoot"
    }

    return $latestBackup.FullName
}

function Get-BackupVolumeNames {
    param(
        [string]$ManifestPath,
        [string]$VolumeDir
    )

    if (Test-Path -LiteralPath $ManifestPath -PathType Leaf) {
        $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
        if ($manifest.volumes) {
            return @($manifest.volumes)
        }
    }

    return @(Get-ChildItem -LiteralPath $VolumeDir -Filter '*.tar.gz' -File |
        ForEach-Object { [IO.Path]::GetFileNameWithoutExtension([IO.Path]::GetFileNameWithoutExtension($_.Name)) })
}

$resolvedBackupPath = Resolve-BackupDirectory -RequestedPath $BackupPath -DefaultRoot $backupRoot
$volumeBackupDir = Join-Path $resolvedBackupPath "volumes"
$metadataDir = Join-Path $resolvedBackupPath "metadata"
$manifestPath = Join-Path $metadataDir "manifest.json"

if (-not (Test-Path -LiteralPath $volumeBackupDir -PathType Container)) {
    throw "Backup volume directory not found: $volumeBackupDir"
}

$volumeNames = Get-BackupVolumeNames -ManifestPath $manifestPath -VolumeDir $volumeBackupDir |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

if (-not $volumeNames) {
    throw "No archived Docker volumes found in $volumeBackupDir"
}

$metadataFiles = @(
    ".env",
    ".env.sample",
    "docker-compose.yml",
    "docker-compose.opensearch.yml",
    "docker-compose.misp-test.yml",
    "Caddyfile",
    "rabbitmq.conf"
)

$runningServicesOutput = & docker compose --project-directory $repoRoot ps --services --status running 2>$null
$stackWasRunning = $LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($runningServicesOutput | Out-String).Trim())

if ($PSCmdlet.ShouldProcess($repoRoot, "Stop and remove current Compose stack before restore")) {
    Invoke-Docker -Arguments @("compose", "--project-directory", $repoRoot, "down")
}

foreach ($relativePath in $metadataFiles) {
    $sourcePath = Join-Path $metadataDir $relativePath
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        continue
    }

    $targetPath = Join-Path $repoRoot $relativePath
    $targetParent = Split-Path -Parent $targetPath

    if ($PSCmdlet.ShouldProcess($targetPath, "Restore metadata file $relativePath")) {
        New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
    }
}

$backupMount = [IO.Path]::GetFullPath($resolvedBackupPath)

foreach ($volumeName in $volumeNames) {
    $archiveName = "$volumeName.tar.gz"
    $archivePath = Join-Path $volumeBackupDir $archiveName

    if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
        throw "Archive for volume '$volumeName' not found: $archivePath"
    }

    if ($PSCmdlet.ShouldProcess($volumeName, "Recreate Docker volume from backup archive")) {
        & docker volume rm $volumeName 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
            throw "Failed to remove Docker volume '$volumeName'"
        }

        Invoke-Docker -Arguments @("volume", "create", $volumeName)
        Invoke-Docker -Arguments @(
            "run",
            "--rm",
            "-v", "${volumeName}:/target",
            "-v", "${backupMount}:/backup:ro",
            "alpine:3.20",
            "sh",
            "-lc",
            "tar -xzf /backup/volumes/$archiveName -C /target"
        )
    }
}

if (-not $NoStart -and $stackWasRunning -and $PSCmdlet.ShouldProcess($repoRoot, "Start Compose stack after restore")) {
    Invoke-Docker -Arguments @("compose", "--project-directory", $repoRoot, "up", "-d")
}

Write-Host "Restore completed from: $resolvedBackupPath"