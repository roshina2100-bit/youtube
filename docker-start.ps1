<#
.SYNOPSIS
    Cinematic Multi-Language Video Studio - Docker Management Script (PowerShell)

.DESCRIPTION
    PowerShell script to manage Docker containers for the Cinematic Multi-Language Video Studio.

.PARAMETER Command
    The command to execute: build, up, down, restart, logs, status, clean, help

.PARAMETER Service
    Optional service name for logs command (backend, frontend)

.EXAMPLE
    .\docker-start.ps1 build
    .\docker-start.ps1 up
    .\docker-start.ps1 logs backend
    .\docker-start.ps1 status
    .\docker-start.ps1 clean
#>

param(
    [Parameter(Mandatory=$false, Position=0)]
    [ValidateSet('build', 'up', 'down', 'restart', 'logs', 'status', 'clean', 'help')]
    [string]$Command = 'help',

    [Parameter(Mandatory=$false, Position=1)]
    [string]$Service = ''
)

# Colors for output
$RED = [ConsoleColor]::Red
$GREEN = [ConsoleColor]::Green
$YELLOW = [ConsoleColor]::Yellow
$BLUE = [ConsoleColor]::Cyan
$GRAY = [ConsoleColor]::DarkGray

function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $BLUE }
function Write-Success { param($msg) Write-Host "[SUCCESS] $msg" -ForegroundColor $GREEN }
function Write-Warning { param($msg) Write-Host "[WARNING] $msg" -ForegroundColor $YELLOW }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $RED }

function Check-Docker {
    try {
        docker info | Out-Null
        return $true
    } catch {
        Write-Error "Docker is not running. Please start Docker Desktop."
        return $false
    }
}

function Check-DockerCompose {
    $dockerCompose = $null
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $dockerCompose = 'docker-compose'
    } elseif (docker compose version 2>$null) {
        $dockerCompose = 'docker compose'
    } else {
        Write-Error "docker-compose is not installed. Please install Docker Compose."
        return $null
    }
    return $dockerCompose
}

function Invoke-Build {
    Write-Info "Building Docker images..."
    & $global:dockerCompose build --parallel
    Write-Success "Build completed!"
}

function Invoke-Up {
    Write-Info "Starting services..."
    docker-compose up -d
    Write-Success "Services started!"
    Write-Info "Frontend: http://localhost"
    Write-Info "Backend API: http://localhost:8000"
    Write-Info "API Docs: http://localhost:8000/docs"
}

function Invoke-Down {
    Write-Info "Stopping services..."
    docker-compose down
    Write-Success "Services stopped!"
}

function Invoke-Restart {
    Write-Info "Restarting services..."
    docker-compose restart
    Write-Success "Services restarted!"
}

function Invoke-Logs {
    param($service)
    if ($service) {
        docker-compose logs -f $service
    } else {
        docker-compose logs -f
    }
}

function Invoke-Status {
    Write-Info "Service status:"
    docker-compose ps
}

function Invoke-Clean {
    Write-Warning "This will remove all containers, networks, and volumes!"
    $confirm = Read-Host "Are you sure? (y/N)"
    if ($confirm -ieq 'y') {
        docker-compose down -v --remove-orphans
        docker system prune -f
        Write-Success "Cleanup completed!"
    } else {
        Write-Info "Cleanup cancelled."
    }
}

function Show-Help {
    Write-Host "Cinematic Multi-Language Video Studio - Docker Management Script (PowerShell)"
    Write-Host ""
    Write-Host "Usage: .\docker-start.ps1 [command] [service]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  build       Build Docker images"
    Write-Host "  up          Start all services"
    Write-Host "  down        Stop all services"
    Write-Host "  restart     Restart all services"
    Write-Host "  logs [svc]  Show logs (optionally for specific service: backend, frontend)"
    Write-Host "  status      Show service status"
    Write-Host "  clean       Remove all containers, networks, and volumes"
    Write-Host "  help        Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\docker-start.ps1 build"
    Write-Host "  .\docker-start.ps1 up"
    Write-Host "  .\docker-start.ps1 logs backend"
    Write-Host "  .\docker-start.ps1 status"
}

# Main execution
$Command = $Command.ToLower()

if (-not (Check-Docker)) { exit 1 }
$global:dockerCompose = Check-DockerCompose
if (-not $global:dockerCompose) { exit 1 }

switch ($Command) {
    'build' { Invoke-Build }
    'up' { Invoke-Up }
    'down' { Invoke-Down }
    'restart' { Invoke-Restart }
    'logs' { Invoke-Logs -service $Service }
    'status' { Invoke-Status }
    'clean' { Invoke-Clean }
    'help' { Show-Help }
    default {
        Write-Error "Unknown command: $Command"
        Show-Help
        exit 1
    }
}