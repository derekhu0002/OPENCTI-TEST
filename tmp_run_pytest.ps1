param(
    [Parameter(Mandatory = $true)]
    [string]$TestPath,
    [Parameter(Mandatory = $true)]
    [string]$BaseName
)

$stdoutPath = Join-Path (Get-Location) ($BaseName + '.txt')
$stderrPath = Join-Path (Get-Location) ($BaseName + '.err')
$exitPath = Join-Path (Get-Location) ($BaseName + '.exit')

$process = Start-Process -FilePath python -ArgumentList '-m','pytest',$TestPath,'-q' -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
Set-Content -Path $exitPath -Value $process.ExitCode
