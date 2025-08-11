# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Development server (preferred)
fastapi dev app/main.py

# Alternative using uvicorn
uvicorn app.main:app --reload
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable to prevent bytecode generation
export PYTHONDONTWRITEBYTECODE=1
```

### Database Setup
```bash
# Initialize database using the schema
mysql -u root -p < sql/db.sql
```

### Maintenance
```bash
# Clean Python cache files
python3 -m pyclean .
# Or use the provided script
./clearcache.sh
```

### Code Quality
```bash
# The project is configured to use Black formatter in VS Code
# Format code (if Black is installed)
black .

# Note: No tests are currently present in the codebase
# No linting commands are configured
```

## Architecture Overview

This is a FastAPI application that serves as a webhook receiver and request logger for JMS (Jump Server) systems. The application follows a modular FastAPI structure with clear separation of concerns.

### Core Components

- **Main Application** (`app/main.py`): FastAPI app with router registration
- **Configuration** (`config/config.py`): Pydantic settings with database connection and app configuration
- **Models** (`app/models/`): SQLModel-based data models for database entities
- **Routers** (`app/routers/`): API endpoint handlers organized by functionality
- **Dependencies** (`app/dependencies.py`): Shared dependencies including database session management

### Database Architecture

The application uses MySQL with SQLModel/SQLAlchemy for ORM. Key characteristics:
- Database connection configured in `config/config.py` with connection string from environment
- Primary entity is `JMSReqLog` which stores HTTP request/response data from JMS systems
- JSON columns used for flexible storage of headers and body data
- Timestamps stored as Unix timestamps

### Key Data Models

- **JMSReqLog**: Main logging entity storing HTTP request details (method, path, headers, body, status, etc.)
- Models follow SQLModel pattern with separate classes for Create, Update, and Read operations

### API Structure

The application provides CRUD operations for request logs:
- `GET /jms_reqlog/` - List all logs
- `GET /jms_reqlog/list` - Paginated log listing
- `POST /jms_reqlog/` - Create new log entry
- `GET /jms_reqlog/{id}` - Get specific log
- `PUT /jms_reqlog/{id}` - Update log entry
- `DELETE /jms_reqlog/{id}` - Delete log entry

### Authentication

Basic token-based authentication is implemented:
- Admin endpoints require `X-Token` header with value `fake-super-secret-token`
- Query token authentication available but currently disabled

### Configuration

Application settings are managed through Pydantic Settings:
- Database URL configurable via environment variables
- Settings loaded from `.env` file
- Default MySQL connection: `mysql+pymysql://root:mypassword@127.0.0.1/test2`