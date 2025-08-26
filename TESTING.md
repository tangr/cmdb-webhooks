# Testing Guide

This document describes how to run and work with the test suite for the webhook-proxy project.

## Quick Start

To run all tests:

```bash
# Make the test runner executable (one-time)
chmod +x run_tests.sh

# Run all tests
./run_tests.sh
```

## Test Categories

The test suite is organized into several categories using pytest markers:

- **Unit tests** (`-m unit`): Test individual components in isolation
- **Integration tests** (`-m integration`): Test API endpoints and component interactions  
- **Security tests** (`-m security`): Test security and authentication mechanisms
- **Auth tests** (`-m auth`): Test authentication-specific functionality
- **Redis tests** (`-m redis`): Test Redis-dependent functionality

## Running Specific Test Categories

```bash
# Unit tests only
pytest tests/ -m unit

# Integration tests only  
pytest tests/ -m integration

# Security tests only
pytest tests/ -m security

# Auth-related tests
pytest tests/ -m auth

# Redis-dependent tests
pytest tests/ -m redis
```

## Running Individual Test Files

```bash
# Test specific models
pytest tests/test_models/test_cmdb_reqlog.py
pytest tests/test_models/test_feishu_reqlog.py

# Test specific services
pytest tests/test_services/test_redis_session.py
pytest tests/test_services/test_feishu_service.py
pytest tests/test_services/test_webhook_mapping.py

# Test API endpoints
pytest tests/test_auth.py
pytest tests/test_cmdb_integration.py
pytest tests/test_feishu_integration.py

# Test utilities
pytest tests/test_utils/test_logger.py
pytest tests/test_security.py
```

## Test Coverage

Generate coverage reports:

```bash
# Terminal coverage report
pytest tests/ --cov=app --cov-report=term-missing

# HTML coverage report (opens in htmlcov/index.html)
pytest tests/ --cov=app --cov-report=html

# XML coverage report (for CI/CD)
pytest tests/ --cov=app --cov-report=xml
```

## Test Configuration

The test suite uses the following configuration files:

- **pytest.ini**: Main pytest configuration with markers, coverage settings
- **tests/conftest.py**: Shared test fixtures and setup
- **run_tests.sh**: Test runner script with environment setup

## Test Database

Tests use SQLite in-memory databases by default, configured in `conftest.py`:

- **Test database URL**: `sqlite:///./test.db`
- **Redis database**: Uses database 14 (different from production)
- **Automatic cleanup**: Test data is cleaned up after each test

## Environment Variables

The following environment variables affect testing:

- `TESTING=1`: Set automatically by test runner to enable test mode
- `PYTHONPATH`: Automatically set to include the project root

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with XML output
pytest tests/ --cov=app --cov-report=xml --junit-xml=junit.xml
```

## Test Structure

```text
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py            # Authentication API tests (existing)
├── test_models/            # Model unit tests
│   ├── test_cmdb_reqlog.py
│   └── test_feishu_reqlog.py
├── test_services/          # Service unit tests
│   ├── test_redis_session.py
│   ├── test_feishu_service.py
│   └── test_webhook_mapping.py
├── test_utils/            # Utility unit tests
│   └── test_logger.py
├── test_cmdb_integration.py    # CMDB API integration tests
├── test_feishu_integration.py  # Feishu API integration tests
└── test_security.py           # Security and authentication tests
```

## Writing New Tests

### Test File Naming

- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`
- Place in appropriate subdirectory (`test_models/`, `test_services/`, etc.)

### Test Class Naming

```python
@pytest.mark.unit  # or @pytest.mark.integration
class TestModelName:
    """Test description"""
    
    def test_specific_functionality(self):
        """Test specific functionality description"""
        pass
```

### Using Fixtures

Common fixtures available in `conftest.py`:

```python
def test_database_operation(test_session):
    """Use test database session"""
    pass

def test_api_endpoint(async_client, auth_headers):
    """Use async HTTP client with authentication"""
    pass

def test_with_mock_redis(mock_redis):
    """Use mocked Redis connection"""
    pass
```

### Marking Tests

```python
@pytest.mark.unit
def test_unit_functionality():
    pass

@pytest.mark.integration  
def test_api_endpoint():
    pass

@pytest.mark.security
def test_authentication():
    pass

@pytest.mark.redis
def test_redis_functionality():
    pass
```

## Debugging Tests

Run tests with increased verbosity and detailed output:

```bash
# Verbose output with full tracebacks
pytest tests/ -v --tb=long

# Stop at first failure
pytest tests/ -x

# Run specific test with output
pytest tests/test_models/test_cmdb_reqlog.py::TestCmdbReqLogModel::test_create_cmdb_reqlog -v -s

# Run with pdb debugger on failure
pytest tests/ --pdb
```

## Performance Testing

For performance-sensitive tests:

```bash
# Run with timing information
pytest tests/ --durations=10

# Profile slow tests
pytest tests/ --profile
```

## Docker Testing

The project supports running tests in Docker containers for better isolation and consistency across environments.

### Docker Test Setup

**Test-specific files:**

- `Dockerfile.test` - Specialized Dockerfile for testing
- `docker-compose.test.yml` - Docker Compose configuration for tests
- `run_tests_docker.sh` - Docker test runner script

### Running Tests in Docker

**Quick start:**

```bash
# Make script executable (one-time)
chmod +x run_tests_docker.sh

# Run all tests in Docker
./run_tests_docker.sh

# Run specific test categories
./run_tests_docker.sh unit
./run_tests_docker.sh integration
./run_tests_docker.sh security
```

**Available Docker commands:**

```bash
# All test categories
./run_tests_docker.sh unit         # Unit tests only
./run_tests_docker.sh integration  # Integration tests only
./run_tests_docker.sh security     # Security tests only
./run_tests_docker.sh auth         # Authentication tests only
./run_tests_docker.sh redis        # Redis tests only

# Special commands
./run_tests_docker.sh coverage     # All tests with coverage
./run_tests_docker.sh shell        # Interactive shell in test container
./run_tests_docker.sh clean        # Clean up test environment
```

### Docker Test Environment

**Test containers:**

- **test-runner**: Main container running pytest with all dependencies
- **test-redis**: Redis container for integration tests (optional)

**Test isolation:**

- Each test run uses fresh containers
- SQLite in-memory database for data isolation
- Separate Redis database (DB 14) for test isolation
- Automatic cleanup after test completion

**Environment variables:**

- `TESTING=1` - Enables test mode
- `DATABASE_URL=sqlite:///./test.db` - Test database
- `REDIS_HOST=test-redis` - Test Redis instance

### Docker Test Results

Test results and coverage reports are automatically saved to local directories:

```bash
# View test results
open htmlcov/index.html              # Coverage HTML report
cat test-results/junit.xml           # JUnit XML report
cat test-results/coverage.xml        # Coverage XML report
```

**Result directories:**

- `htmlcov/` - HTML coverage reports
- `test-results/` - XML reports for CI/CD

### Docker Development Workflow

**Development testing:**

```bash
# Run tests during development
./run_tests_docker.sh unit

# Debug in container
./run_tests_docker.sh shell
# Then inside container:
pytest tests/test_models/ -v -s
```

**CI/CD integration:**

```bash
# In CI/CD pipeline
./run_tests_docker.sh coverage

# Parse XML results
cat test-results/junit.xml
cat test-results/coverage.xml
```

### Docker Compose Override

For customized test environments, create `docker-compose.test.override.yml`:

```yaml
services:
  test-runner:
    environment:
      - CUSTOM_ENV_VAR=value
    volumes:
      - ./custom-config:/app/custom-config
```

### Advantages of Docker Testing

**Consistency:**

- Same environment across development, CI/CD, and production
- Eliminates "works on my machine" issues
- Consistent Python version and dependencies

**Isolation:**

- Complete isolation from host system
- Clean environment for each test run
- No interference from host services

**Scalability:**

- Easy to run tests in parallel containers
- Simple integration with CI/CD systems
- Consistent test timing and resource usage

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `PYTHONPATH` includes project root
2. **Database errors**: Check test database permissions and cleanup
3. **Redis errors**: Verify Redis connection settings in test configuration
4. **Async errors**: Use `pytest-asyncio` for async test functions
5. **Docker errors**: Ensure Docker is running and accessible

### Docker-specific Issues

1. **Permission errors**: Check Docker daemon permissions
2. **Port conflicts**: Ensure test ports (6380) are available
3. **Build failures**: Clean Docker cache with `./run_tests_docker.sh clean`
4. **Volume issues**: Check Docker volume permissions

### Test Isolation

If tests are interfering with each other:

```bash
# Local testing
pytest tests/ -n auto  # Requires pytest-xdist
pytest tests/ --forked  # Requires pytest-forked

# Docker testing (automatically isolated)
./run_tests_docker.sh unit
```
