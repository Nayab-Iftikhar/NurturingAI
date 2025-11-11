# NurturingAI - Django Ninja Project

A Django Ninja project for building AI-powered applications.

## Setup

1. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate  # or: source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server:**
   ```bash
   python manage.py runserver
   ```

## API Documentation

Once the server is running, visit:
- API Docs: http://127.0.0.1:8000/api/docs
- Admin Panel: http://127.0.0.1:8000/admin/

## Test Endpoint

```bash
curl http://127.0.0.1:8000/api/hello
```

## Project Structure

```
.
├── config/          # Django project settings
├── manage.py        # Django management script
├── requirements.txt # Python dependencies
└── .env.example     # Environment variables template
```

