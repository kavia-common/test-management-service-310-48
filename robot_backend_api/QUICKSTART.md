# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set your values
# Required variables:
# - DATABASE_URL
# - MINIO_ENDPOINT
# - MINIO_ACCESS_KEY
# - MINIO_SECRET_KEY
```

### Step 3: Run the Application
```bash
# Use the Python runner (easiest)
python3 run.py

# OR use the bash script
chmod +x run.sh
./run.sh

# OR use uvicorn directly
cd src
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 Access API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/

## ✅ Verify Installation

Run the import verification test:
```bash
python3 verify_imports.py
```

Expected output: `✓✓✓ SUCCESS! All imports work correctly!`

## 🔧 Troubleshooting

### ImportError Issues
✅ **FIXED!** The ImportError has been resolved. All imports now use absolute paths.

### Connection Errors
If you see PostgreSQL or MinIO connection errors:
1. Verify services are running
2. Check your `.env` file configuration
3. Ensure credentials are correct

### Port Already in Use
If port 8000 is in use, change it in the run command:
```bash
python3 -c "import sys; sys.path.insert(0, 'src'); import uvicorn; uvicorn.run('api.main:app', host='0.0.0.0', port=8080)"
```

## 📖 More Information

- Full documentation: See `README.md`
- Import fix details: See `IMPORT_FIX_SUMMARY.md`
- Completion status: See `COMPLETION_STATUS.md`

## 🎯 Next Steps

1. Upload a `.robot` test file via `POST /tests`
2. View extracted test cases via `GET /tests/{id}/testcases`
3. Execute tests via `POST /runs`
4. Retrieve logs via `GET /runs/{id}/logs`

Happy testing! 🤖
