$ErrorActionPreference = "Stop"

# Check if Docker is installed
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is not installed. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is available
try {
    docker compose version | Out-Null
}
catch {
    Write-Host "Docker Compose (v2 CLI) is not available. Please install or update Docker." -ForegroundColor Red
    exit 1
}

# Enable BuildKit
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

# Change to the script's directory
Set-Location $PSScriptRoot

Write-Host "Building services using Docker Compose with BuildKit enabled..." -ForegroundColor Cyan

# Build all services
docker compose build

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful! Starting the services..." -ForegroundColor Green
}
else {
    Write-Host "Build failed. Please check the error messages above." -ForegroundColor Red
    exit 1
}

# Start services
docker compose up -d

Write-Host "Services are up and running!" -ForegroundColor Green
Write-Host "Use 'docker compose ps' to see running containers." -ForegroundColor Cyan
Write-Host "Use 'docker compose logs -f' to view logs." -ForegroundColor Cyan
