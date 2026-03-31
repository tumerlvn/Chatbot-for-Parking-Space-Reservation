# SmartPark City Center - Parking Chatbot

An intelligent conversational AI system for parking facility management using RAG (Retrieval-Augmented Generation) and LangGraph.

**Current Status:** Stage 2 Complete (Human-in-the-Loop Admin Approval System)

---

## What It Does

SmartPark Chatbot is a conversational AI assistant that helps users:

1. **Get Information** - Ask questions about parking policies, pricing, amenities, and hours
2. **Check Availability** - See real-time parking spot availability
3. **Make Reservations** - Complete reservation flow with admin approval
4. **Check Status** - Query reservation status and approval decisions

### Example Conversations

**Getting Information:**

```
You: What are your operating hours?
Bot: SmartPark is open 24/7. Staff available 8 AM - 8 PM...

You: Do you have EV charging?
Bot: Yes! Level 2 EV chargers on Level 2, Row A.
     Currently 2 EV spots available.
```

**Making a Reservation:**

```
You: I want to make a reservation
Bot: When would you like to start parking?

You: Tomorrow at 9 AM
Bot: And when do you plan to leave?

You: 5 PM
Bot: Great! We have spots available:
     • Standard: 4, EV: 2, Accessible: 2
     What is your full name?

You: John Smith
Bot: What's your license plate?

You: ABC-1234
Bot: Which spot type would you prefer? (Standard, EV, or Accessible)

You: EV
Bot: Pre-reservation created successfully!
     Reservation ID: #1
     Assigned Spot: L2-A1 (EV)
     Floor: Level 2
     Your reservation is now pending admin approval.
```

**Checking Reservation Status:**

```
You: What's my reservation status?
Bot: Reservation Status
     Reservation ID: #1
     Status: APPROVED
     Assigned Spot: L2-A1 (EV)
     Floor: Level 2
     Start: Tomorrow at 9 AM
     End: Tomorrow at 5 PM
     Your reservation has been approved! See you soon.
```

---

## Architecture

```
User Input → LangGraph Router → [Q&A | Reservation | Status Check] → Response
                                  ↓           ↓                ↓
                      Milvus Vector DB    SQLite Database    Checkpoint Store
                      (Policy Knowledge)  (Availability)     (Conversation State)
                                                ↓
                                          [INTERRUPT] ← Admin REST API
                                                ↓
                                        Resume & Finalize
```

**Key Technologies:**

- **LangGraph** - Conversation flow with interrupt pattern for human-in-the-loop
- **Milvus Lite** - Semantic search over policies
- **SQLite** - Real-time spot availability and reservation persistence
- **SqliteSaver** - Cross-process checkpoint storage for state management
- **FastAPI** - REST API for admin approval/rejection
- **Azure OpenAI** - Language understanding and generation (GPT-4o-mini)
- **HuggingFace** - Embeddings (all-MiniLM-L6-v2) and reranking (bge-reranker-base)

**Stage 2 Human-in-the-Loop Flow:**

1. User completes reservation details
2. Chatbot creates pending reservation in database
3. Graph execution **pauses** at interrupt point (await_approval node)
4. Admin reviews via REST API and approves/rejects
5. API updates graph state and resumes execution
6. Chatbot finalizes reservation (updates DB, marks spot as occupied)
7. User can check status via chatbot

---

## Quick Start

### Prerequisites

- Python 3.11+
- Azure OpenAI access (with Claude model)

### Installation

1. **Clone and navigate to project**

```bash
cd Chatbot-for-Parking-Space-Reservation
```

2. **Install dependencies**

```bash
uv sync
# or: pip install -e .
```

3. **Set up environment**

```bash
cp .env.example .env
```

Edit `.env` and add:

```bash
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

You can also use DIAL API key and endpoint.

4. **Verify setup**

```bash
python rag-and-chatbot/src/chatbot/verify_setup.py
```

### Run the Chatbot

**Option 1: Command Line Interface**

```bash
python -m rag_and_chatbot.src.chatbot.main
```

Commands:

- Type your message to chat
- `reset` - Start new conversation
- `history` - View conversation
- `exit` - Quit

**Option 2: Python API**

```python
from rag_and_chatbot.src.chatbot.main import ParkingChatbot

chatbot = ParkingChatbot()
response = chatbot.chat("What are your hours?")
print(response)
```

**Option 3: Jupyter Notebook**

```bash
jupyter notebook rag-and-chatbot/src/notebooks/test_stage2.ipynb
```

### Run the Admin API (Stage 2)

The Admin API allows administrators to approve or reject pending reservations.

**Start the API server:**

```bash
python rag-and-chatbot/src/api/run_api.py
```

Or with custom settings:

```bash
python rag-and-chatbot/src/api/run_api.py --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:

- Server: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json

**Available Endpoints:**

```bash
GET  /health                         # Health check
GET  /reservations/pending           # List pending reservations
POST /reservations/{id}/approve      # Approve a reservation
POST /reservations/{id}/reject       # Reject a reservation
GET  /reservations/{id}              # Get reservation details
```

**Example: Approve a reservation**

```bash
curl -X POST http://localhost:8000/reservations/1/approve \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve", "admin_notes": "Approved for regular customer"}'
```

Response:

```json
{
  "success": true,
  "reservation_id": 1,
  "status": "approved",
  "user_name": "John Smith",
  "car_number": "ABC-1234",
  "message": "Reservation approved and finalized successfully"
}
```

**Example: List pending reservations**

```bash
curl http://localhost:8000/reservations/pending
```

Response:

```json
{
  "pending_count": 2,
  "reservations": [
    {
      "id": 1,
      "user_name": "John Smith",
      "car_number": "ABC-1234",
      "start_time": "2026-04-01 09:00:00",
      "end_time": "2026-04-01 17:00:00",
      "requested_at": "2026-03-31 14:30:00",
      "assigned_spot": {
        "number": "L2-A1",
        "type": "EV",
        "floor": "Level 2"
      },
      "thread_id": "default_thread"
    }
  ]
}
```

**Testing the full flow:**

1. Start the chatbot in one terminal
2. Start the Admin API in another terminal
3. Make a reservation via chatbot
4. Check pending reservations: `curl http://localhost:8000/reservations/pending`
5. Approve via API
6. Check status in chatbot: "What's my reservation status?"

Alternatively you can do all the testing in `test_stage2.ipynb`

---

## Project Structure

```
rag-and-chatbot/
├── data/
│   ├── parking.db              # Vector database (policy knowledge)
│   ├── parking_db.sqlite       # SQL database (reservations & spots)
│   ├── checkpoints.sqlite      # LangGraph state persistence
│   └── parking_policy.md       # Source policy document
│
├── src/
│   ├── chatbot/
│   │   ├── state.py            # Conversation state (Stage 2: added thread_id, reservation fields)
│   │   ├── nodes.py            # Bot logic (router, Q&A, reservation, status checker)
│   │   ├── graph.py            # Flow orchestration (Stage 2: interrupt pattern, SqliteSaver)
│   │   ├── main.py             # Entry point
│   │   ├── guardrails.py       # Data protection & security
│   │   └── evaluation.py       # RAG performance metrics
│   │
│   ├── api/                    # Stage 2: Admin REST API
│   │   ├── admin_api.py        # FastAPI server with approval endpoints
│   │   └── run_api.py          # API launcher script
│   │
│   └── notebooks/
│       ├── generate_data.ipynb     # Setup databases (Stage 2: added thread_id column)
│       ├── test_chatbot.ipynb      # Interactive testing
│       ├── test_stage2.ipynb       # Stage 2 integration tests (NEW)
│       ├── test_retrieval.ipynb    # RAG pipeline testing
│       ├── test_guardrails.ipynb   # Security & PII protection tests
│       └── evaluate_rag.ipynb      # Performance evaluation suite
```

---

## Features

### Stage 1: RAG-Based Q&A and Pre-Reservation

| Feature                    | Description                                                         |
| -------------------------- | ------------------------------------------------------------------- |
| **Policy Q&A**             | Semantic search over parking policies with reranking                |
| **Real-Time Availability** | Live database queries for spot counts                               |
| **Time Conflict Checking** | Prevents double-bookings by detecting overlapping reservations      |
| **Intent Classification**  | Automatically routes between Q&A and reservations                   |
| **Pre-Reservation**        | Collects: times, name, license plate, checks availability           |
| **Smart Data Collection**  | Checks availability BEFORE asking for personal info                 |
| **Guard Rails System**     | Input validation & output filtering for security and PII protection |
| **RAG Evaluation**         | Automated testing with Recall@K, Precision@K, MRR metrics           |
| **Conversation Memory**    | Maintains context across multiple messages                          |
| **Multi-Interface**        | CLI, Python API, and Jupyter notebook support                       |

### Stage 2: Human-in-the-Loop Admin Approval

| Feature                         | Description                                                      |
| ------------------------------- | ---------------------------------------------------------------- |
| **Spot Type Preference**        | User selects preferred spot type (Standard, EV, Accessible)      |
| **Database Persistence**        | Reservations stored in SQLite with status tracking               |
| **LangGraph Interrupt Pattern** | Graph pauses at approval node, waits for admin action            |
| **Cross-Process State Sharing** | SqliteSaver enables notebook and API to share conversation state |
| **Admin REST API**              | FastAPI server with approve/reject endpoints                     |
| **Thread ID Management**        | Links reservations to conversation threads for resumption        |
| **Status Checking**             | Users can query reservation status via chatbot                   |
| **Automatic Spot Assignment**   | Assigns specific spot based on user preference                   |
| **Admin Decision Tracking**     | Records approval time and admin notes in state                   |
| **Spot Occupancy Management**   | Updates spot status to "occupied" on approval                    |

### Security & Data Protection

**Guard Rails System:**

- **Input Validation** - Blocks SQL injection, command injection, path traversal attacks
- **Output Filtering** - Automatically redacts PII (emails, phone numbers, SSN, credit cards)
- **System Protection** - Prevents exposure of database paths, API keys, IP addresses
- **Performance** - <1ms overhead per interaction

**Time Conflict Detection:**

- Checks for overlapping reservations before confirming availability
- Prevents double-bookings across all time ranges
- SQL-based conflict detection with 6 overlap scenarios

### Evaluation & Quality Assurance

**RAG Performance Metrics:**

- **Recall@K** - Coverage of relevant documents in top K results
- **Precision@K** - Relevance of retrieved documents
- **MRR (Mean Reciprocal Rank)** - Position of first relevant result
- **Response Time** - End-to-end latency measurement
- **Quality Scoring** - Answer accuracy assessment

**Automated Testing:**

- 10-query test dataset with ground truth
- JSON reports with performance breakdown
- Visualization charts for metrics analysis

---

## Current Parking Facility

**Available Spots: 9 total**

| Floor   | Type        | Spots        | Status      |
| ------- | ----------- | ------------ | ----------- |
| Ground  | Accessible  | G-01, G-02   | Available   |
| Ground  | Standard    | G-03         | Available   |
| Level 1 | Standard    | L1-A1, L1-A2 | Available   |
| Level 1 | Standard    | L1-A3        | Maintenance |
| Level 2 | EV Charging | L2-A1, L2-A2 | Available   |
| Level 2 | Standard    | L2-B1        | Available   |

**Pricing:**

- Hourly: $5.00/hour
- Daily Max: $35.00
- Overnight: $15.00 (enter after 6 PM, exit before 8 AM)

---

## Testing

### Automated Tests

```bash
# Verify environment setup
python rag-and-chatbot/src/chatbot/verify_setup.py

# Run interactive test suite (Stage 1)
jupyter notebook rag-and-chatbot/src/notebooks/test_chatbot.ipynb

# Test Stage 2 integration (human-in-the-loop flow)
jupyter notebook rag-and-chatbot/src/notebooks/test_stage2.ipynb

# Test guard rails (security & PII protection)
jupyter notebook rag-and-chatbot/src/notebooks/test_guardrails.ipynb

# Evaluate RAG performance (Recall, Precision, MRR)
jupyter notebook rag-and-chatbot/src/notebooks/evaluate_rag.ipynb
```

### Manual Testing Scenarios

**Stage 1: Q&A and Pre-Reservation**

1. **Policy Questions**
   - "What are your hours?"
   - "How much does parking cost?"
   - "Can I park my RV?"
   - "What's the cancellation policy?"

2. **Availability Questions**
   - "Are there any spots free?"
   - "Do you have EV charging available?"
   - "Are accessible spots available?"

**Stage 2: Full Reservation Flow with Admin Approval**

1. **Create Reservation**
   - User: "I want to make a reservation"
   - Provide times, name, license plate, spot type preference
   - Note the reservation ID

2. **Admin Approval (via API)**

   ```bash
   # List pending reservations
   curl http://localhost:8000/reservations/pending

   # Approve reservation
   curl -X POST http://localhost:8000/reservations/1/approve \
     -H "Content-Type: application/json" \
     -d '{"decision": "approve", "admin_notes": "Approved"}'
   ```

3. **Check Status**
   - User: "What's my reservation status?"
   - Should see "APPROVED" status

4. **Test Rejection Flow**
   - Create another reservation
   - Reject via API endpoint
   - Check status shows "REJECTED"

**Mixed Conversations**

- Ask questions, then make reservation
- Make reservation, check status, ask more questions
- Test router handling of incomplete reservations

---

### Database Configuration

Databases are pre-populated. To regenerate:

```bash
jupyter notebook rag-and-chatbot/src/notebooks/generate_data.ipynb
```

## Documentation

- **[PHASE1.md](./PHASE1.md)** - Stage 1 technical documentation
- **[STAGE1_COMPLETE.md](./STAGE1_COMPLETE.md)** - Stage 1 completion summary
- **[PROJECT_SCHEMA.md](./PROJECT_SCHEMA.md)** - Complete architecture overview
- **API Documentation** - Interactive docs at http://localhost:8000/docs (when API server is running)
- **Inline Code Comments** - Throughout all Python files

### Key Concepts

**LangGraph Interrupt Pattern (Stage 2):**

- Graph execution pauses at designated interrupt nodes
- External systems (Admin API) can inspect and modify state
- State updates trigger graph resumption
- Enables human-in-the-loop workflows without blocking

**Cross-Process State Management:**

- SqliteSaver stores checkpoints in file-based SQLite database
- Multiple processes (notebook, API) can access same conversation state
- Thread ID links database reservations to conversation threads
- Enables async admin approval while maintaining conversation context
