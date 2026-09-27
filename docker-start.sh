#!/bin/bash
# Cinematic Multi-Language Video Studio - Docker Startup Script
# Usage: ./docker-start.sh [command]
# Commands: up, down, build, logs, restart, status, clean

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop or Docker daemon."
        exit 1
    fi
}

# Check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "docker-compose is not installed. Please install Docker Compose."
        exit 1
    fi
}

# Build images
cmd_build() {
    print_info "Building Docker images..."
    docker-compose build --parallel
    print_success "Build completed!"
}

# Start services
cmd_up() {
    print_info "Starting services..."
    docker-compose up -d
    print_success "Services started!"
    print_info "Frontend: http://localhost"
    print_info "Backend API: http://localhost:8000"
    print_info "API Docs: http://localhost:8000/docs"
}

# Stop services
cmd_down() {
    print_info "Stopping services..."
    docker-compose down
    print_success "Services stopped!"
}

# Restart services
cmd_restart() {
    print_info "Restarting services..."
    docker-compose restart
    print_success "Services restarted!"
}

# Show logs
cmd_logs() {
    if [ -n "$2" ]; then
        docker-compose logs -f "$2"
    else
        docker-compose logs -f
    fi
}

# Show status
cmd_status() {
    print_info "Service status:"
    docker-compose ps
}

# Clean up
cmd_clean() {
    print_warning "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_info "Cleanup cancelled."
    fi
}

# Show help
cmd_help() {
    echo "Cinematic Multi-Language Video Studio - Docker Management Script"
    echo ""
    echo "Usage: ./docker-start.sh [command]"
    echo ""
    echo "Commands:"
    echo "  build       Build Docker images"
    echo "  up          Start all services"
    echo "  down        Stop all services"
    echo "  restart     Restart all services"
    echo "  logs [svc]  Show logs (optionally for specific service)"
    echo "  status      Show service status"
    echo "  clean       Remove all containers, networks, and volumes"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-start.sh build    # Build images"
    echo "  ./docker-start.sh up       # Start services"
    echo "  ./docker-start.sh logs backend  # Show backend logs"
    echo "  ./docker-start.sh status   # Show service status"
}

# Main script
main() {
    check_docker
    check_docker_compose

    case "${1:-help}" in
        build)
            cmd_build
            ;;
        up)
            cmd_up
            ;;
        down)
            cmd_down
            ;;
        restart)
            cmd_restart
            ;;
        logs)
            cmd_logs "$@"
            ;;
        status)
            cmd_status
            ;;
        clean)
            cmd_clean
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            print_error "Unknown command: $1"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"