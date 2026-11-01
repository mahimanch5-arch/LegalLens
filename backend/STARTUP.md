## Backend Startup Guide

**FastAPI Backend for LegalLens**

---

## ✅ Prerequisites

1. **Python 3.12+** installed
   ```bash
   python --version  # Should show 3.12 or higher
   ```

2. **Dependencies installed**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment configured**
   ```bash
   # Check .env exists with ANTHROPIC_API_KEY
   cat .env
   ```

---

## 🚀 Quick Start (Pick One)

### Option 1: Using Python Script (Recommended)

```bash
cd backend
python run.py

# Expected output:
# 🚀 Starting Legal Lens Backend
#    Host: 127.0.0.1
#    Port: 8000
#    Reload: False
#    Workers: 1
#
# 📍 API will be available at http://127.0.0.1:8000/api
# 📚 Interactive docs at http://127.0.0.1:8000/api/docs
```

### Option 2: Using Uvicorn Directly

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Option 3: With Auto-Reload (Development)

```bash
cd backend
python run.py --reload

# or

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Option 4: Different Port

```bash
cd backend
python run.py --port 5000

# or

uvicorn app.main:app --host 127.0.0.1 --port 5000
```

---

## 🔍 Verify Backend is Running

### Test 1: Check API Docs

```
Open browser:
http://127.0.0.1:8000/api/docs

You should see:
✅ Swagger UI with all API endpoints
✅ Try it out buttons on each endpoint
```

### Test 2: Test API Endpoint

```bash
# In new terminal, test the Ask endpoint
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the parties?",
    "chat_history": []
  }'

# Expected response:
# {"success": true, "data": {"original_question": "...", ...}}
```

### Test 3: Check Logs

```
In terminal where backend is running:

✅ You should see:
   - Database migrations complete
   - Legal Lens API ready message
   - Request logs for each API call
```

---

## 🔧 Command Options

### Port Selection

```bash
# Default (8000)
python run.py

# Custom port
python run.py --port 5000
python run.py --port 3000

# Popular ports:
# 8000 - Default FastAPI port
# 5000 - Flask default (good for frontend compatibility)
# 3000 - React frontend (don't use for backend)
```

### Auto-Reload (Development Only)

```bash
# Enable auto-reload when code changes
python run.py --reload

# Great for development
# NOT for production
```

### Multiple Workers (Production)

```bash
# Run with 4 worker processes
python run.py --workers 4

# Good for handling multiple requests
# Not needed for single-user development
```

### Custom Host

```bash
# Listen on all interfaces (0.0.0.0)
python run.py --host 0.0.0.0 --port 8000

# Listen on localhost only (default)
python run.py --host 127.0.0.1 --port 8000
```

---

## 🐛 Common Startup Issues

### Issue 1: "ModuleNotFoundError: No module named 'app'"

**Cause:** Not in the correct directory

**Fix:**
```bash
cd backend
python run.py
```

### Issue 2: "Address already in use"

**Cause:** Another process using port 8000

**Fix:**
```bash
# Use different port
python run.py --port 5000

# Or find and stop the other process
# Linux/Mac:
lsof -i :8000
kill <PID>

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Issue 3: "No such file or directory: .env"

**Cause:** Environment file missing

**Fix:**
```bash
# Copy from example
cp .env.example .env

# Edit .env with your API key
nano .env  # or use your editor
```

### Issue 4: "Invalid API key" when calling API

**Cause:** ANTHROPIC_API_KEY not set or invalid

**Fix:**
```bash
# Check .env
cat .env

# Update with your actual key from https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Restart backend
```

### Issue 5: "Can't connect to vector store"

**Cause:** First run or corrupted data

**Fix:**
```bash
# Delete cached data
rm -rf data/chroma_db

# Restart backend
python run.py

# Re-ingest documents if needed
```

---

## 📊 Expected Startup Output

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 🔄 Development Workflow

```bash
# Terminal 1: Backend with auto-reload
cd backend
python run.py --reload

# Terminal 2: Frontend
cd frontend
npm start

# Terminal 3: Testing
# Test API or Frontend

# Make code changes in any file
# Backend auto-reloads (shows "Reloading")
# Frontend auto-reloads (shows "Compiled successfully")
```

---

## 🛑 Stopping the Server

```bash
# Press Ctrl+C in the terminal where backend is running

# Expected output:
# Shutdown complete
```

---

## 📝 Using the API

Once backend is running:

### Interactive Docs (Recommended for Testing)

```
http://127.0.0.1:8000/api/docs

Try:
1. Click "Ask" endpoint
2. Click "Try it out"
3. Enter test JSON
4. Click "Execute"
5. See response
```

### Using cURL

```bash
# Ask workflow
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the parties?","chat_history":[]}'

# Check response in terminal
```

### Using Python

```python
import requests

url = "http://127.0.0.1:8000/api/ask"
data = {
    "question": "What are the parties?",
    "chat_history": []
}

response = requests.post(url, json=data)
print(response.json())
```

---

## ✅ Startup Checklist

- [ ] In `backend` directory
- [ ] requirements.txt installed
- [ ] .env file exists with API key
- [ ] Run `python run.py`
- [ ] See "Application startup complete"
- [ ] Open http://127.0.0.1:8000/api/docs
- [ ] Test one API endpoint
- [ ] See successful response

---

## 🎯 Common Configurations

### Development (Auto-Reload)
```bash
python run.py --reload
```

### Testing with Custom Port
```bash
python run.py --port 5000
```

### Production Simulation
```bash
python run.py --workers 4
```

### Debugging
```bash
python run.py --reload --host 127.0.0.1 --port 8000
```

---

## 🚀 Next Steps

1. **Backend running?** ✅
2. **Test API?** Use `/api/docs` in browser
3. **Start Frontend?** `cd frontend && npm start`
4. **Test Integration?** Follow FRONTEND-TESTING-GUIDE.md

---

**Backend is now ready!** 🎉
