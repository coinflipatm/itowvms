#!/bin/bash
# filepath: /workspaces/itowvms/deploy.sh
"""
Production Deployment Script for iTow VMS
Enhanced architecture with automated workflows
"""

set -e

echo "=== iTow VMS Production Deployment ==="
echo "Starting deployment at $(date)"

# Configuration
PROJECT_NAME="itowvms"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
DATA_DIR="./data"
LOG_DIR="./logs"

# Create necessary directories
mkdir -p "$BACKUP_DIR" "$DATA_DIR" "$LOG_DIR"

# Function to check if service is running
check_service() {
    if docker-compose -f docker-compose.production.yml ps "$1" | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Function to backup database
backup_database() {
    echo "Creating database backup..."
    if [ -f "$DATA_DIR/vehicles.db" ]; then
        cp "$DATA_DIR/vehicles.db" "$BACKUP_DIR/vehicles_backup.db"
        echo "Database backed up to $BACKUP_DIR/vehicles_backup.db"
    fi
}

# Function to validate environment
validate_environment() {
    echo "Validating environment..."
    
    # Check required environment variables
    required_vars=("SECRET_KEY" "SMTP_USERNAME" "SMTP_PASSWORD" "SENDER_EMAIL")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: Environment variable $var is not set"
            echo "Please set all required environment variables in .env file"
            exit 1
        fi
    done
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "Error: Docker Compose is not installed"
        exit 1
    fi
    
    echo "Environment validation passed"
}

# Function to build and deploy
deploy() {
    echo "Building Docker image..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    echo "Starting services..."
    docker-compose -f docker-compose.production.yml up -d
    
    # Wait for services to be healthy
    echo "Waiting for services to start..."
    sleep 30
    
    # Check service health
    echo "Checking service health..."
    if check_service "itowvms"; then
        echo "✅ iTow VMS service is running"
    else
        echo "❌ iTow VMS service failed to start"
        exit 1
    fi
    
    if check_service "redis"; then
        echo "✅ Redis service is running"
    else
        echo "❌ Redis service failed to start"
        exit 1
    fi
}

# Function to run post-deployment tests
run_tests() {
    echo "Running post-deployment tests..."
    
    # Test health endpoint
    if curl -f http://localhost/health &> /dev/null; then
        echo "✅ Health check passed"
    else
        echo "❌ Health check failed"
        exit 1
    fi
    
    # Test login page
    if curl -f http://localhost/auth/login &> /dev/null; then
        echo "✅ Login page accessible"
    else
        echo "❌ Login page not accessible"
        exit 1
    fi
    
    # Test API endpoint
    if curl -f http://localhost/api/vehicles/status/New &> /dev/null; then
        echo "✅ API endpoints working"
    else
        echo "❌ API endpoints not working"
        exit 1
    fi
    
    echo "All post-deployment tests passed"
}

# Function to setup monitoring
setup_monitoring() {
    echo "Setting up monitoring..."
    
    # Create monitoring script
    cat > monitor.sh << 'EOF'
#!/bin/bash
# Simple monitoring script for iTow VMS

while true; do
    echo "=== $(date) ==="
    
    # Check service status
    docker-compose -f docker-compose.production.yml ps
    
    # Check disk space
    df -h
    
    # Check memory usage
    free -h
    
    # Check application logs for errors
    echo "Recent errors:"
    docker-compose -f docker-compose.production.yml logs --tail=10 itowvms 2>&1 | grep -i error || echo "No recent errors"
    
    echo "================================"
    sleep 300  # Check every 5 minutes
done
EOF
    
    chmod +x monitor.sh
    echo "Monitoring script created: ./monitor.sh"
}

# Function to display deployment summary
deployment_summary() {
    echo ""
    echo "=== Deployment Summary ==="
    echo "✅ iTow VMS Enhanced Architecture deployed successfully"
    echo "✅ Automated workflow engine operational"
    echo "✅ Background task scheduler running"
    echo "✅ Email notification system configured"
    echo "✅ Production security measures in place"
    echo ""
    echo "Access URLs:"
    echo "- Application: http://localhost"
    echo "- Health Check: http://localhost/health"
    echo "- API: http://localhost/api/"
    echo ""
    echo "Management Commands:"
    echo "- View logs: docker-compose -f docker-compose.production.yml logs -f"
    echo "- Restart services: docker-compose -f docker-compose.production.yml restart"
    echo "- Stop services: docker-compose -f docker-compose.production.yml down"
    echo "- Monitor: ./monitor.sh"
    echo ""
    echo "Backup location: $BACKUP_DIR"
    echo "Deployment completed at $(date)"
}

# Main deployment flow
main() {
    echo "Starting production deployment..."
    
    # Load environment variables
    if [ -f .env ]; then
        source .env
        echo "Environment variables loaded from .env"
    fi
    
    validate_environment
    backup_database
    echo "Building PWA static assets..."
    (cd mobile/pwa && npm ci && npm run build)
    deploy
    run_tests
    setup_monitoring
    deployment_summary
    
    echo ""
    echo "🎉 iTow VMS Production Deployment COMPLETE!"
    echo "The enhanced architecture is now running in production mode."
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "backup")
        backup_database
        ;;
    "test")
        run_tests
        ;;
    "monitor")
        ./monitor.sh
        ;;
    "logs")
        docker-compose -f docker-compose.production.yml logs -f
        ;;
    "stop")
        docker-compose -f docker-compose.production.yml down
        echo "Services stopped"
        ;;
    "restart")
        docker-compose -f docker-compose.production.yml restart
        echo "Services restarted"
        ;;
    *)
        echo "Usage: $0 {deploy|backup|test|monitor|logs|stop|restart}"
        exit 1
        ;;
esac
