# Stage 2 Quick Start Guide

## Quick Commands

### 1. Run Verification Tests

```bash
cd rag-and-chatbot
source ../.venv/bin/activate
python test_stage2.py
```

Expected output: `All Tests Passed!`

---

### 2. Start All Services

**Terminal 1: User Agent**

```bash
cd rag-and-chatbot
source ../.venv/bin/activate
python -m src.chatbot.main
```

**Terminal 2: Admin Agent**

```bash
cd rag-and-chatbot
source ../.venv/bin/activate
python -m src.chatbot.admin_main
```

**Terminal 3: REST API**

```bash
cd rag-and-chatbot
source ../.venv/bin/activate
python -m src.api.admin_api
```

API docs at: http://localhost:8000/docs

---

### 3. Quick Test Flow

**In Terminal 1 (User):**

```
User: I want to make a reservation
[Follow prompts...]
Bot: Reservation created successfully! I'll continue to assist you!
User: What are your hours?
[User can continue chatting]
```

**In Terminal 2 (Admin):**

```
Admin: show pending
[See list of pending reservations]

Admin: approve 1
[Gets curl command with [INTERRUPT] message]
[Shows: "Waiting for API confirmation........"]
```

**In Terminal 4:**

```bash
curl -X POST http://localhost:8000/reservations/1/approve \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve", "admin_notes": "Approved"}' | jq
```

**Back in Terminal 2 (Automatic):**

```
Agent: Reservation #1 has been approved.
       Notes: Approved

Admin:
```

The admin CLI automatically polls for completion and displays the result. No manual action needed.

**Back in Terminal 1:**

```
User: What's my reservation status?
Bot: Status: APPROVED [details...]
```

End-to-end flow complete.
