#!/bin/bash

# Docker test runner script for webhook-proxy project
# This script runs the complete test suite in Docker containers

set -e  # Exit on any error

echo "🐳 Starting webhook-proxy Docker test suite..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_docker() {
    echo -e "${BLUE}[DOCKER]${NC} $1"
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi

# Determine docker-compose command
COMPOSE_CMD="docker-compose"
if ! command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker compose"
fi

# Create test results directory
mkdir -p test-results htmlcov

print_status "Setting up test environment..."

# Clean up any existing test containers
print_docker "Cleaning up existing test containers..."
$COMPOSE_CMD -f docker-compose.test.yml down --remove-orphans --volumes 2>/dev/null || true

# Build test image
print_docker "Building test image..."
$COMPOSE_CMD -f docker-compose.test.yml build --no-cache test-runner

# Start dependencies (Redis)
print_docker "Starting test dependencies..."
$COMPOSE_CMD -f docker-compose.test.yml up -d test-redis

# Wait for dependencies to be ready
print_status "Waiting for test dependencies to be ready..."
sleep 5

# Function to run specific test category
run_test_category() {
    local category=$1
    local description=$2
    
    print_status "Running $description..."
    
    if [ "$category" = "all" ]; then
        $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner \
            python -m pytest tests/ -v \
            --cov=app \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --cov-report=xml:test-results/coverage.xml \
            --junit-xml=test-results/junit.xml
    else
        $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner \
            python -m pytest tests/ -m "$category" -v --tb=short
    fi
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    # Run all test categories
    print_status "No specific category provided, running all tests..."
    
    print_status "Running unit tests..."
    run_test_category "unit" "unit tests"
    
    print_status "Running integration tests..."
    run_test_category "integration" "integration tests"
    
    print_status "Running security tests..."
    run_test_category "security" "security tests"
    
    print_status "Running complete test suite with coverage..."
    run_test_category "all" "complete test suite"
    
elif [ "$1" = "unit" ]; then
    run_test_category "unit" "unit tests"
elif [ "$1" = "integration" ]; then
    run_test_category "integration" "integration tests"
elif [ "$1" = "security" ]; then
    run_test_category "security" "security tests"
elif [ "$1" = "auth" ]; then
    run_test_category "auth" "authentication tests"
elif [ "$1" = "redis" ]; then
    run_test_category "redis" "Redis tests"
elif [ "$1" = "coverage" ]; then
    run_test_category "all" "complete test suite with coverage"
elif [ "$1" = "shell" ]; then
    print_status "Opening interactive shell in test container..."
    $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner bash
elif [ "$1" = "clean" ]; then
    print_status "Cleaning up test environment..."
    $COMPOSE_CMD -f docker-compose.test.yml down --remove-orphans --volumes --rmi local
    docker system prune -f
    rm -rf test-results htmlcov
    print_status "Cleanup complete!"
    exit 0
else
    print_error "Unknown test category: $1"
    echo ""
    echo "Usage: $0 [category]"
    echo ""
    echo "Available categories:"
    echo "  unit         - Run unit tests only"
    echo "  integration  - Run integration tests only"
    echo "  security     - Run security tests only"
    echo "  auth         - Run authentication tests only"
    echo "  redis        - Run Redis tests only"
    echo "  coverage     - Run all tests with coverage report"
    echo "  shell        - Open interactive shell in test container"
    echo "  clean        - Clean up test environment"
    echo ""
    echo "If no category is specified, all tests will be run."
    exit 1
fi

# Clean up test containers (but keep volumes for test results)
print_docker "Cleaning up test containers..."
$COMPOSE_CMD -f docker-compose.test.yml down --remove-orphans

print_status "✅ Docker tests completed successfully!"

# Show test results location
echo ""
echo "📊 Test Results:"
echo "  • Coverage HTML report: htmlcov/index.html"
echo "  • Coverage XML report:  test-results/coverage.xml"
echo "  • JUnit XML report:     test-results/junit.xml"
echo ""
echo "📋 Quick Commands:"
echo "  • View HTML coverage:   open htmlcov/index.html"
echo "  • Run specific tests:   $0 [unit|integration|security|auth|redis]"
echo "  • Interactive shell:    $0 shell"
echo "  • Clean environment:    $0 clean"
