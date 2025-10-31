#!/bin/bash
# Setup script for testing environment

set -e

echo "=========================================="
echo "Setting up test environment"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Python 3 not found"; exit 1; }
echo "✓ Python 3 is installed"
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "✗ Error: requirements.txt not found"
    echo "  Please run this script from robot_backend_api directory"
    exit 1
fi
echo "✓ In correct directory"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip3 install -q -r requirements.txt 2>&1 | grep -v "already satisfied" || true
echo "✓ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠ No .env file found"
    echo "  Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env file"
        echo "  Please edit .env with your database credentials"
    else
        echo "  Creating minimal .env..."
        cat > .env << EOF
DATABASE_URL=postgresql://user:pass@localhost:5432/testdb
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
EOF
        echo "✓ Created minimal .env file"
    fi
else
    echo "✓ .env file exists"
fi
echo ""

# Test parser (doesn't need DB)
echo "Testing parser enhancements..."
if python3 tests/test_parser_variables.py; then
    echo "✓ Parser test passed"
else
    echo "✗ Parser test failed"
    exit 1
fi
echo ""

# Check if database is accessible
echo "Checking database connectivity..."
python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    from core.database import SessionLocal
    db = SessionLocal()
    db.execute('SELECT 1')
    db.close()
    print('✓ Database is accessible')
    sys.exit(0)
except Exception as e:
    print('⚠ Database not accessible:', str(e))
    print('  This is OK for parser tests')
    print('  Start database for full testing')
    sys.exit(0)  # Not a fatal error
"
echo ""

echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "You can now run:"
echo "  1. Parser test:       python3 tests/test_parser_variables.py"
echo "  2. Endpoint diagnosis: python3 tests/diagnose_endpoint.py 2 4  (needs DB)"
echo "  3. Start API:         python3 run.py  (needs DB)"
echo "  4. Test with curl:    bash tests/test_endpoint_curl.sh  (needs API)"
echo ""
