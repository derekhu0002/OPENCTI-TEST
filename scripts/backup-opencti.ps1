[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$OutputRoot = "backups"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"

function Get-EnvValue {
    param(
        [string]$FilePath,
        [string]$Name,
        [string]$Default = ""
    )

    if (-not (Test-Path -LiteralPath $FilePath)) {
        return $Default
    }

    foreach ($line in Get-Content -LiteralPath $FilePath) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) {
            continue
        }

        if ($line -like "$Name=*") {
            return $line.Substring($Name.Length + 1)
        }
    }

    return $Default
}

function Invoke-Docker {
    param(
        [string[]]$Arguments
    )

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($Arguments -join ' ')"
    }
}

$projectName = Get-EnvValue -FilePath $envPath -Name "COMPOSE_PROJECT_NAME" -Default ([IO.Path]::GetFileName($repoRoot).ToLowerInvariant())
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $repoRoot $OutputRoot
$backupDir = Join-Path $backupRoot $timestamp
$volumeBackupDir = Join-Path $backupDir "volumes"
$metadataDir = Join-Path $backupDir "metadata"

$runningServicesOutput = & docker compose --project-directory $repoRoot ps --services --status running 2>$null
$stackWasRunning = $LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($runningServicesOutput | Out-String).Trim())

$volumeNames = @(& docker volume ls --filter "label=com.docker.compose.project=$projectName" --format "{{.Name}}") |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

if (-not $volumeNames) {
    throw "No Docker volumes found for Compose project '$projectName'."
}

if ($PSCmdlet.ShouldProcess($backupDir, "Create backup directory structure")) {
    New-Item -ItemType Directory -Path $volumeBackupDir -Force | Out-Null
    New-Item -ItemType Directory -Path $metadataDir -Force | Out-Null
}

if ($stackWasRunning -and $PSCmdlet.ShouldProcess($repoRoot, "Stop Compose stack for a consistent backup")) {
    Invoke-Docker -Arguments @("compose", "--project-directory", $repoRoot, "stop")
}

try {
    $backupMount = [IO.Path]::GetFullPath($backupDir)

    foreach ($volumeName in $volumeNames) {
        $archiveName = "$volumeName.tar.gz"
        $archiveTarget = Join-Path $volumeBackupDir $archiveName

        if ($PSCmdlet.ShouldProcess($archiveTarget, "Archive Docker volume $volumeName")) {
            Invoke-Docker -Arguments @(
                "run",
                "--rm",
                "-v", "${volumeName}:/source:ro",
                "-v", "${backupMount}:/backup",
                "alpine:3.20",
                "sh",
                "-lc",
                "tar -czf /backup/volumes/$archiveName -C /source ."
            )
        }
    }

    $copyFiles = @(
        ".env",
        ".env.sample",
        "docker-compose.yml",
        "docker-compose.opensearch.yml",
        "docker-compose.misp-test.yml",
        "Caddyfile",
        "rabbitmq.conf"
    )

    foreach ($relativePath in $copyFiles) {
        $sourcePath = Join-Path $repoRoot $relativePath
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            continue
        }

        $targetPath = Join-Path $metadataDir $relativePath
        $targetParent = Split-Path -Parent $targetPath
        if ($PSCmdlet.ShouldProcess($targetPath, "Copy metadata file $relativePath")) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
            Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        }
    }

    $manifest = [ordered]@{
        createdAt = (Get-Date).ToString("o")
        repoRoot = $repoRoot
        projectName = $projectName
        stackWasRunning = $stackWasRunning
        volumes = $volumeNames
    } | ConvertTo-Json -Depth 3

    $manifestPath = Join-Path $metadataDir "manifest.json"
    if ($PSCmdlet.ShouldProcess($manifestPath, "Write backup manifest")) {
        Set-Content -LiteralPath $manifestPath -Value $manifest -Encoding UTF8
    }
}
finally {
    if ($stackWasRunning -and $PSCmdlet.ShouldProcess($repoRoot, "Start Compose stack after backup")) {
        Invoke-Docker -Arguments @("compose", "--project-directory", $repoRoot, "start")
    }
}

Write-Host "Backup completed: $backupDir"