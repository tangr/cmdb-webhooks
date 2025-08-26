#!/bin/bash

# Test runner script for webhook-proxy project
# This script runs the complete test suite with proper configuration

set -e  # Exit on any error

echo "🧪 Starting webhook-proxy test suite..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

# Check if pytest is installed
if ! python3 -c "import pytest" &> /dev/null; then
    print_error "pytest is not installed. Please run: pip install pytest pytest-asyncio pytest-cov"
    exit 1
fi

# Set environment variables for testing
export PYTHONPATH="$(pwd):$PYTHONPATH"
export TESTING=1

# Create test database directory if it doesn't exist
mkdir -p $(dirname "./test.db") 2>/dev/null || true

print_status "Running unit tests..."
python3 -m pytest tests/ -m "unit" -v --tb=short

print_status "Running integration tests..."
python3 -m pytest tests/ -m "integration" -v --tb=short

print_status "Running security tests..."
python3 -m pytest tests/ -m "security" -v --tb=short

print_status "Running all tests with coverage..."
python3 -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml

print_status "Running specific test categories..."

echo ""
echo "📋 Test Categories Available:"
echo "  • Unit tests:        pytest tests/ -m unit"
echo "  • Integration tests: pytest tests/ -m integration" 
echo "  • Security tests:    pytest tests/ -m security"
echo "  • Auth tests:        pytest tests/ -m auth"
echo "  • Redis tests:       pytest tests/ -m redis"
echo ""
echo "📊 Coverage report generated in: htmlcov/index.html"
echo ""

# Clean up test artifacts
if [ -f "./test.db" ]; then
    rm -f "./test.db"
    print_status "Cleaned up test database"
fi

print_status "✅ All tests completed successfully!"