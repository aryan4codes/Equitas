# Quick Start Guide - Equitas Backend

## Prerequisites Check

Before starting, make sure you have:
1. ✅ Python 3.11+ installed
2. ✅ MongoDB running (or MongoDB Atlas connection string)
3. ✅ Environment variables configured

## Step 1: Setup Environment Variables

Create a `.env` file in the Equitas root directory:

```bash
# MongoDB (Required)
MONGODB_URL=mongodb://localhost:27017
# OR for MongoDB Atlas:
# MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/

MONGODB_DATABASE=equitas

# Clerk Authentication (Required for user endpoints)
CLERK_SECRET_KEY=sk_test_your_secret_key_here

# OpenAI (Required for AI safety features)
OPENAI_API_KEY=sk-your-openai-key

# Security (Optional - defaults provided)
SECRET_KEY=your-secret-key-change-in-production
```

## Step 2: Start the Backend

### Option 1: Using main.py (Recommended)
```bash
uv run python main.py backend
```

### Option 2: Using uvicorn directly
```bash
uv run uvicorn backend_api.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Using Python directly
```bash
uv run python -m backend_api.main
```

## Step 3: Verify It's Running

1. **Check health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **View API documentation:**
   Open browser: http://localhost:8000/docs

3. **Check root endpoint:**
   ```bash
   curl http://localhost:8000/
   ```

## What You'll See

```
Starting Equitas Backend API...
API will be available at http://localhost:8000
API docs at http://localhost:8000/docs

Press CTRL+C to stop

INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Troubleshooting

### MongoDB Connection Failed
- Make sure MongoDB is running: `mongod` or check MongoDB Atlas connection
- Verify `MONGODB_URL` in `.env` is correct
- The backend will still start but user/credit features won't work

### Import Errors
- Run `uv sync` to ensure all dependencies are installed
- Check Python version: `python --version` (should be 3.11+)

### Port Already in Use
- Change port: `uvicorn backend_api.main:app --port 8001`
- Or kill existing process: `lsof -ti:8000 | xargs kill`

## Next Steps

After backend is running:
1. Start frontend: `cd ../Equitas-frontend && npm run dev`
2. Visit: http://localhost:5173 (or your frontend port)
3. Sign up with Clerk
4. Start using the dashboard!

