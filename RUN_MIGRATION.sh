#!/bin/bash

# Know Me Feature - PostgreSQL Migration Script
# ============================================
# This script runs the Alembic migration to create the private tables
# for the Know Me feature.

# STEP 1: Update your PostgreSQL connection URL below
# Replace with your actual PostgreSQL connection string
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/mentormuni"

# STEP 2: Set environment and run migration
echo "🔄 Running Know Me migration..."
echo "Database: $DATABASE_URL"
echo ""

cd /Users/rahul/Downloads/MentorMuni/MentorMuniAPI/mentormuni-api

# Run all pending migrations up to 0020
export DATABASE_URL="$DATABASE_URL"
../.venv/bin/alembic upgrade head

# Check if migration succeeded
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Update .env with your DATABASE_URL"
    echo "2. Start the API: cd /Users/rahul/Downloads/MentorMuni/MentorMuniAPI/mentormuni-api && ../.venv/bin/uvicorn app.main:app --reload --port 8000"
    echo "3. Test Know Me endpoint: POST http://localhost:8000/student/know-me/start"
else
    echo ""
    echo "❌ Migration failed. Check the error above."
    echo ""
    echo "Troubleshooting:"
    echo "- Verify DATABASE_URL is correct"
    echo "- Check PostgreSQL is running and accessible"
    echo "- Run: psql -c 'SELECT version()' to test connection"
fi
