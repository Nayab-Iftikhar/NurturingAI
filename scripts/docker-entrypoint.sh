#!/bin/bash
# Docker entrypoint script for NurturingAI

set -e

echo "Starting NurturingAI application setup..."

# Wait for database to be ready (if using external database)
if [ -n "$DATABASE_HOST" ]; then
    echo "Waiting for database..."
    while ! nc -z "$DATABASE_HOST" "${DATABASE_PORT:-5432}"; do
        sleep 0.1
    done
    echo "Database is ready!"
fi

# Remove existing database to ensure clean state
if [ -f "db.sqlite3" ]; then
    echo "Removing existing database for clean setup..."
    rm -f db.sqlite3
fi

# Remove ChromaDB data for clean state
if [ -d "data/chromadb" ]; then
    echo "Clearing ChromaDB data for clean setup..."
    rm -rf data/chromadb/*
fi

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Reset database and create default admin user
echo "Resetting database and creating default admin user..."
python manage.py reset_database

# Seed Vanna training data (optional, won't fail if it doesn't exist)
echo "Seeding Vanna training data (if available)..."
python manage.py shell << EOF
try:
    from campaigns.management.commands.seed_vanna_training import Command
    cmd = Command()
    cmd.handle()
    print("✓ Vanna training data seeded")
except Exception as e:
    print(f"Note: Vanna training data seeding skipped: {e}")
EOF

echo "Setup complete!"
echo ""
echo "Default admin credentials:"
echo "  Email: admin@admin.com"
echo "  Password: admin@123"
echo ""

# Execute the main command
exec "$@"

