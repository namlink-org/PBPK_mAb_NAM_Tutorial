# pbpk.ps1 - one-word launcher for the Docker workflow (Windows PowerShell or PowerShell 7).
#
# From the repository root:
#   powershell -ExecutionPolicy Bypass -File docker\pbpk.ps1 apriori
# Commands: build, apriori, sensitivity, compare, summary, versions, help
#
# 'build' (or the first run) creates the image 'pbpk-mab-nam' from docker\Dockerfile.

param([string]$Command = "help")

$ErrorActionPreference = "Continue"
$image = "pbpk-mab-nam"
$repo  = Split-Path -Parent $PSScriptRoot      # the folder that contains docker\

function Fail($m) { Write-Host ""; Write-Host "STOPPED: $m" -ForegroundColor Red; exit 1 }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker is not installed. Install Docker Desktop, start it, and try again."
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Fail "Docker is not running. Start Docker Desktop, wait for 'Engine running', and try again."
}

docker image inspect $image *> $null
$haveImage = ($LASTEXITCODE -eq 0)

if ($Command -eq "build" -or -not $haveImage) {
    Write-Host "==> Building the '$image' image (first time: 15 to 30 minutes, about 1 GB download)" -ForegroundColor Cyan
    docker build -t $image (Join-Path $repo "docker")
    if ($LASTEXITCODE -ne 0) { Fail "Image build failed. Send a screenshot of the red text above." }
    if ($Command -eq "build") { exit 0 }
}

docker run --rm -v "${repo}:/work" $image $Command
exit $LASTEXITCODE
