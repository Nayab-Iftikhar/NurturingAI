#!/bin/bash
# Setup script for NurturingAI application

set -e

echo "Setting up NurturingAI application..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data/chromadb
mkdir -p data/brochures
mkdir -p media
mkdir -p staticfiles

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser (optional, skip if exists)
echo "Creating superuser (if needed)..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created: admin/admin123")
else:
    print("Superuser already exists")
EOF

# Seed Vanna training data (optional)
echo "Seeding Vanna training data..."
python manage.py shell << EOF
try:
    from campaigns.management.commands.seed_vanna_training import Command
    cmd = Command()
    cmd.handle()
    print("Vanna training data seeded successfully")
except Exception as e:
    print(f"Note: Vanna training data seeding skipped: {e}")
EOF

echo "Setup complete!"
echo ""
echo "To run the application:"
echo "  source .venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "To run tests:"
echo "  pytest tests/ -v"
echo ""
echo "To run evaluation:"
echo "  pytest tests/run_eval.py -v"

