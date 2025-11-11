# Docker Setup Guide

This guide explains how to build and run the NurturingAI application using Docker.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## Quick Start

### Using Docker Compose (Recommended)

1. **Create `.env` file** (copy from `.env.example`):
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Build and run**:
   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - Web interface: http://localhost:8000
   - API: http://localhost:8000/api

## Default Admin User

Every Docker build creates a fresh database with a default admin user:

- **Email**: `admin@admin.com`
- **Password**: `admin@123`
- **Username**: `admin`

**Note**: The Docker build automatically:
- Clears all existing database data (campaigns, leads, documents, etc.)
- Clears ChromaDB vector store data
- Creates a fresh database with migrations
- Creates the default admin user

This ensures a clean state for every Docker build.

### Using Docker directly

1. **Build the image**:
   ```bash
   docker build -t nurturingai:latest .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name nurturingai \
     -p 8000:8000 \
     --env-file .env \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/media:/app/media \
     nurturingai:latest
   ```

## Environment Variables

Required environment variables (see `.env.example`):

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `OPENAI_API_KEY`: OpenAI API key (optional, can use Ollama)
- `OLLAMA_BASE_URL`: Ollama base URL (default: http://localhost:11434)
- `EMAIL_HOST`: SMTP host
- `EMAIL_PORT`: SMTP port
- `EMAIL_HOST_USER`: SMTP username
- `EMAIL_HOST_PASSWORD`: SMTP password
- `IMAP_HOST`: IMAP host for email replies
- `IMAP_USER`: IMAP username
- `IMAP_PASSWORD`: IMAP password

## Volumes

The following directories are mounted as volumes:

- `/app/data`: ChromaDB data and brochures
- `/app/media`: Uploaded media files
- `/app/staticfiles`: Collected static files

## Running Tests in Docker

```bash
# Run all tests
docker-compose exec web pytest tests/ -v

# Run specific test file
docker-compose exec web pytest tests/test_api_workflow.py -v

# Run with coverage
docker-compose exec web pytest tests/ -v --cov=. --cov-report=html
```

## Running Management Commands

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Check email replies
docker-compose exec web python manage.py check_email_replies

# Process auto replies
docker-compose exec web python manage.py process_auto_replies
```

## Production Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Set proper `ALLOWED_HOSTS`
3. Use a production database (PostgreSQL recommended)
4. Use a production web server (Gunicorn + Nginx)
5. Set up SSL/TLS certificates
6. Configure proper backup strategy for data volumes

### Production Dockerfile

For production, you may want to use a multi-stage build with Gunicorn:

```dockerfile
# Add to Dockerfile
RUN pip install gunicorn

# Change CMD to:
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
```

## Troubleshooting

### Container won't start

- Check logs: `docker-compose logs web`
- Verify environment variables in `.env`
- Ensure ports 8000 is not in use

### Database errors

- Run migrations: `docker-compose exec web python manage.py migrate`
- Check database permissions

### ChromaDB errors

- Ensure `/app/data/chromadb` directory has write permissions
- Check disk space

### Email sending issues

- Verify SMTP credentials in `.env`
- Check firewall settings
- For development, use console backend: `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`

