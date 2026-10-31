# Quick Start: Intent Classifier Testing

**Time to test:** 5 minutes  
**API Key needed:** Yes (get from https://console.anthropic.com/)

---

## 3-Step Setup

### 1️⃣ Get API Key
Go to: https://console.anthropic.com/  
Copy your API key (starts with `sk-ant-v0-`)

### 2️⃣ Add to `.env`
Edit: `backend/app/orchestrator/.env`

Change this:
```bash
ANTHROPIC_API_KEY=
```

To this:
```bash
ANTHROPIC_API_KEY=sk-ant-v0-your-actual-key-here
```

### 3️⃣ Install & Test
```bash
cd backend
pip install langchain langchain-anthropic python-dotenv pytest

cd app/orchestrator
python test_classifier_cli.py --batch
```

---

## Expected Output

You should see ✅ after each test:

```
✅ [PASS] What are the termination rights?    → ask
✅ [PASS] Summarize this contract             → summary
✅ [PASS] Draft a memo                        → draft
...
✅ [PASS] xyz                                 → ask

Results: 20 passed, 0 failed out of 20 tests
🎉 All tests passed!
```

---

## Testing Options

**Interactive (Try Different Messages):**
```bash
python test_classifier_cli.py

# Type messages and hit Enter:
# What are the termination rights?
# Summarize this contract
# Draft a memo
# quit
```

**Batch (See All 20 Tests):**
```bash
python test_classifier_cli.py --batch
```

**Single Message:**
```bash
python test_classifier_cli.py "Your message here"
```

**Unit Tests:**
```bash
pytest test_intent_classifier.py -v
```

---

## Common Issues

| Issue | Solution |
|-------|----------|
| "API key not set" | Add your key to `.env` |
| "Module not found" | Run: `pip install langchain langchain-anthropic` |
| Tests timeout | Check internet, verify API key works |
| Wrong classifications | Run batch tests first to see pattern |

---

## What to Do Next

1. **Run the batch tests** above
2. **Tell me the results** — Copy/paste the output
3. **We'll verify it works** — Might need small adjustments
4. **Then build the full orchestrator** — Integrate with backend

---

## Files Built

| File | Purpose |
|------|---------|
| `intent_classifier.py` | Main module |
| `test_intent_classifier.py` | Unit tests (40+) |
| `test_classifier_cli.py` | Interactive CLI |
| `intent-classifier-prompt.md` | Strategy & rules |
| `README.md` | Full docs |
| `.env` | Your config |

---

## That's It! 🚀

Run the batch test and let me know what you see:

```bash
cd backend/app/orchestrator
python test_classifier_cli.py --batch
```

Copy/paste the output here and we'll verify everything works!
