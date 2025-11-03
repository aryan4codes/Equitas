# How to Start Equitas Backend

## Quick Start (3 Steps)

### 1. Ensure Environment Variables are Set
Your `.env` file should have at minimum:
```bash
MONGODB_URL=mongodb://localhost:27017  # Or your MongoDB Atlas URL
CLERK_SECRET_KEY=sk_test_...            # Already set ✅
```

### 2. Start the Backend

**Option A: Using main.py (Easiest)**
```bash
uv run python main.py backend
```

**Option B: Using uvicorn directly**
```bash
uv run uvicorn backend_api.main:app --reload
```

**Option C: Using Python module**
```bash
uv run python -m backend_api.main
```

### 3. Verify It's Running

Open in browser:
- **API Root**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Expected Output

```
Starting Equitas Backend API...
API will be available at http://localhost:8000
API docs at http://localhost:8000/docs

Press CTRL+C to stop

INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Notes

- **MongoDB**: If not running, the backend will still start but show warnings. User/credit features require MongoDB.
- **Port**: Default is 8000. Change with `--port 8001` if needed.
- **Auto-reload**: Enabled by default. Code changes will restart the server.

## Troubleshooting

**Port already in use?**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill

# Or use different port
uv run uvicorn backend_api.main:app --port 8001
```

**MongoDB connection failed?**
- Check if MongoDB is running: `mongod --version`
- Verify `MONGODB_URL` in `.env`
- For MongoDB Atlas, ensure IP is whitelisted

**Import errors?**
```bash
uv sync  # Reinstall dependencies
```

## Next: Start Frontend

Once backend is running, start the frontend:
```bash
cd ../Equitas-frontend
npm run dev
```

Then visit: http://localhost:5173 (or your Vite port)

