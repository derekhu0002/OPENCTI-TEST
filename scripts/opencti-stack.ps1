[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Stop", "Start", "Restart", "Up", "Status")]
    [string]$Action
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-DockerCompose {
    param(
        [string[]]$Arguments
    )

    & docker compose --project-directory $repoRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose command failed: docker compose --project-directory $repoRoot $($Arguments -join ' ')"
    }
}

switch ($Action) {
    "Stop" {
        Invoke-DockerCompose -Arguments @("stop")
    }
    "Start" {
        Invoke-DockerCompose -Arguments @("start")
    }
    "Restart" {
        Invoke-DockerCompose -Arguments @("restart")
    }
    "Up" {
        Invoke-DockerCompose -Arguments @("up", "-d")
    }
    "Status" {
        Invoke-DockerCompose -Arguments @("ps")
    }
}