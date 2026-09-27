@echo off
REM Cinematic Multi-Language Video Studio - Docker Startup Script (Windows)
REM Usage: docker-start.bat [command]
REM Commands: up, down, build, logs, restart, status, clean, help

@echo off
setlocal enabledelayedexpansion

REM Colors for output
set RED=\033[0;31m
set GREEN=\033[0;32m
set YELLOW=\033[1;33m
set BLUE=\033[0;34m
set NC=\033[0m

REM Project root
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

REM Function to print colored output
:print_info
echo %BLUE%[INFO]%NC% %1
goto :eof

:print_success
echo %GREEN%[SUCCESS]%NC% %1
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %1
goto :eof

REM Check if Docker is running
:check_docker
docker info >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker is not running. Please start Docker Desktop."
    exit /b 1
)

REM Check if docker-compose is available
:check_docker_compose
docker-compose version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        call :print_error "docker-compose is not installed. Please install Docker Compose."
        exit /b 1
    )
    set DOCKER_COMPOSE=docker compose
) else (
    set DOCKER_COMPOSE=docker-compose
)

REM Build images
:cmd_build
call :print_info "Building Docker images..."
% DOCKER_COMPOSE% build --parallel
call :print_success "Build completed!"
goto :eof

REM Start services
:cmd_up
call :print_info "Starting services..."
% DOCKER_COMPOSE% up -d
call :print_success "Services started!"
echo.
echo Frontend: http://localhost
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
goto :eof

REM Stop services
:cmd_down
call :print_info "Stopping services..."
% DOCKER_COMPOSE% down
call :print_success "Services stopped!"
goto :eof

REM Restart services
:cmd_restart
call :print_info "Restarting services..."
% DOCKER_COMPOSE% restart
call :print_success "Services restarted!"
goto :eof

REM Show logs
:cmd_logs
if "%~2"=="" (
    % DOCKER_COMPOSE% logs -f
) else (
    % DOCKER_COMPOSE% logs -f %2
)
goto :eof

REM Show status
:cmd_status
call :print_info "Service status:"
% DOCKER_COMPOSE% ps
goto :eof

REM Clean up
:cmd_clean
call :print_warning "This will remove all containers, networks, and volumes!"
set /p confirm="Are you sure? (y/N) "
if /i "%confirm%"=="y" (
    % DOCKER_COMPOSE% down -v --remove-orphans
    docker system prune -f
    call :print_success "Cleanup completed!"
) else (
    call :print_info "Cleanup cancelled."
)
goto :eof

REM Show help
:cmd_help
echo Cinematic Multi-Language Video Studio - Docker Management Script
echo.
echo Usage: docker-start.bat [command]
echo.
echo Commands:
echo   build       Build Docker images
echo   up          Start all services
echo   down        Stop all services
echo   restart     Restart all services
echo   logs [svc]  Show logs (optionally for specific service)
echo   status      Show service status
echo   clean       Remove all containers, networks, and volumes
echo   help        Show this help message
echo.
echo Examples:
echo   docker-start.bat build    # Build images
echo   docker-start.bat up       # Start services
echo   docker-start.bat logs backend  # Show backend logs
echo   docker-start.bat status   # Show service status
goto :eof

REM Main script
if "%1"=="" (
    call :cmd_help
    goto :eof
)

call :check_docker
call :check_docker_compose

if "%1"=="build" call :cmd_build
if "%1"=="up" call :cmd_up
if "%1"=="down" call :cmd_down
if "%1"=="restart" call :cmd_restart
if "%1"=="logs" call :cmd_logs %*
if "%1"=="status" call :cmd_status
if "%1"=="clean" call :cmd_clean
if "%1"=="help" call :cmd_help
if "%1"=="-h" call :cmd_help
if "%1"=="--help" call :cmd_help

REM Unknown command
if not "%1"=="" (
    call :print_error "Unknown command: %1"
    call :cmd_help
    exit /b 1
)

goto :eof