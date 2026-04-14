# SmartPark City Center - Parking Chatbot

An intelligent conversational AI system for parking facility management using RAG (Retrieval-Augmented Generation) and LangGraph.

**Current Status:** ✅ Stage 4 Complete - Full Multi-Agent Orchestration

## ✨ Stage 4: Orchestration Layer

The system now features a comprehensive orchestration layer:
- 🎯 **Supervisor Pattern** - Master orchestrator coordinates user and admin agents
- 🔔 **Event System** - Real-time pub/sub for cross-agent communication
- 🏗️ **Shared Services** - Database pooling, LLM singletons, centralized config
- 📊 **Monitoring** - Metrics collection, performance tracking, health checks
- ✅ **Backward Compatible** - All Stage 1-3 functionality preserved

**See [STAGE4_README.md](STAGE4_README.md) for complete documentation.**

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

**Two-Agent System:**

```
USER AGENT (Non-Blocking):
User Input → Router → [Q&A | Reservation | Status] → Response
                         ↓         ↓
                   Milvus DB   SQLite DB → Creates pending reservation
                                              ↓
                                        User continues chatting

ADMIN AGENT (With Interrupt + Confirmation):
Admin Input → Router → [List Pending | Approve/Reject]
                              ↓              ↓
                         Shows list    [INTERRUPT] → REST API confirms
                                              ↓
                                       Execute action → Update DB
                                              ↓ (if approved)
                                   Write confirmation node (LLM + bind_tools)
                                              ↓
                                       Confirmation file written
```

**Key Technologies:**

- **LangGraph** - Two separate conversation graphs with interrupt pattern
- **Milvus Lite** - Semantic search over policies
- **SQLite** - Shared database for coordination between agents
- **SqliteSaver** - Separate checkpoint storage for each agent
- **FastAPI** - REST API to resume admin agent after confirmation
- **Azure OpenAI** - Language understanding and generation (gpt-5.1)
- **HuggingFace** - Embeddings (all-MiniLM-L6-v2) and reranking (bge-reranker-base)

**Stage 2-3 Two-Agent Flow:**

1. User completes reservation details in User Agent
2. User Agent creates pending reservation in database and continues conversation
3. Admin uses Admin Agent CLI to list pending reservations
4. Admin types "approve ID" - Admin Agent pauses at interrupt
5. Admin runs curl command to REST API
6. API resumes Admin Agent graph, updates database, marks spot as occupied
7. **Stage 3:** Graph routes to write_confirmation_node (LLM with bind_tools)
8. **Stage 3:** Confirmation written to file with audit trail
9. Admin Agent automatically shows completion message
10. User can check status via User Agent chatbot

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
cd rag-and-chatbot
source ../.venv/bin/activate
python -m src.chatbot.main
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

### Run the Admin System (Stage 2)

Stage 2 provides a way for administrators to manage reservations:

**Terminal 1: Admin CLI (Recommended)**

Interactive conversational interface for admins:

```bash
cd rag-and-chatbot
source ../.venv/bin/activate
python -m src.chatbot.admin_main
```

Commands:

- `list` - Show pending reservations
- `approve ID` - Approve a reservation (triggers interrupt)
- `reject ID` - Reject a reservation (triggers interrupt)
- `reset` - Start new conversation
- `exit` - Quit

The CLI automatically polls for completion after triggering an approval/rejection.

**Terminal 2: REST API**

Start the API server for programmatic access:

```bash
cd rag-and-chatbot
source ../.venv/bin/activate
python -m src.api.admin_api
```

The API will be available at:

- Server: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json

To discrover more go to STAGE2_QUICKSTART.md

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

1. Terminal 1: Start the User Agent chatbot

   ```bash
   python -m src.chatbot.main
   ```

2. Terminal 2: Start the Admin Agent CLI

   ```bash
   python -m src.chatbot.admin_main
   ```

3. Terminal 3: Start the REST API

   ```bash
   python -m src.api.admin_api
   ```

4. In Terminal 1, make a reservation via chatbot

5. In Terminal 2, list and approve:

   ```
   Admin: list
   Admin: approve 1
   [Wait for polling dots...]
   ```

6. In Terminal 4, run the curl command shown in Terminal 2

7. Terminal 2 will automatically show completion message

8. In Terminal 1, check status: "What's my reservation status?"

---

## Project Structure

```
rag-and-chatbot/
├── data/
│   ├── parking.db              # Vector database (policy knowledge)
│   ├── parking_db.sqlite       # SQL database (reservations & spots)
│   ├── checkpoints.sqlite      # LangGraph state persistence
│   ├── confirmed_reservations.txt  # Stage 3: Confirmation file (auto-created)
│   └── parking_policy.md       # Source policy document
│
├── src/
│   ├── chatbot/
│   │   ├── state.py            # User agent conversation state
│   │   ├── nodes.py            # User agent nodes (router, Q&A, reservation, status)
│   │   ├── graph.py            # User agent graph (no interrupt)
│   │   ├── main.py             # User agent CLI entry point
│   │   ├── admin_state.py      # Admin agent conversation state
│   │   ├── admin_nodes.py      # Admin agent nodes (with write_confirmation_node)
│   │   ├── admin_graph.py      # Admin agent graph (with conditional routing)
│   │   ├── admin_main.py       # Admin agent CLI with polling
│   │   ├── mcp_tools.py        # Stage 3: LangChain tools for confirmation
│   │   ├── guardrails.py       # Data protection & security
│   │   └── evaluation.py       # RAG performance metrics
│   │
│   ├── mcp/                    # Stage 3: Confirmation writer module
│   │   └── confirmation_writer.py  # File writer with sanitization
│   │
│   ├── api/                    # Stage 2: Admin REST API
│   │   └── admin_api.py        # FastAPI server for resuming admin agent
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

### Stage 2: Two-Agent Architecture with Human-in-the-Loop

| Feature                         | Description                                                          |
| ------------------------------- | -------------------------------------------------------------------- |
| **Two Separate Agents**         | User Agent (non-blocking) and Admin Agent (with interrupt)           |
| **User Agent Continuity**       | Users can continue chatting after creating reservation               |
| **Admin Conversational CLI**    | Natural language interface: "list", "approve 5", "reject 3"          |
| **Automatic Polling**           | Admin CLI polls for completion and shows result automatically        |
| **Spot Type Preference**        | User selects preferred spot type (Standard, EV, Accessible)          |
| **Database Coordination**       | SQLite database shared between both agents as single source of truth |
| **Separate Checkpoints**        | Each agent has independent conversation state storage                |
| **LangGraph Interrupt Pattern** | Admin Agent pauses at execute_action, waits for API confirmation     |
| **Admin REST API**              | FastAPI server resumes admin agent graph after human confirmation    |
| **Status Checking**             | Users query reservation status via User Agent chatbot                |
| **Automatic Spot Assignment**   | Assigns specific spot based on user preference                       |
| **Admin Decision Tracking**     | Records approval time and admin notes in database                    |
| **Spot Occupancy Management**   | Updates spot status to "occupied" on approval                        |
| **Detailed API Logging**        | Logs graph execution and database updates for debugging              |

### Stage 3: Confirmation File Writer with LangGraph bind_tools

| Feature                         | Description                                                          |
| ------------------------------- | -------------------------------------------------------------------- |
| **Separate Confirmation Node**  | Dedicated graph node for writing confirmations (not mixed with DB)   |
| **LLM with bind_tools Pattern** | Uses proper LangGraph `.bind_tools()` for tool calling               |
| **Conditional Routing**         | Routes to confirmation node only for approvals, not rejections       |
| **File-Based Audit Trail**      | Writes approved reservations to pipe-delimited text file             |
| **Input Sanitization**          | Prevents file format corruption from special characters              |
| **Graceful Degradation**        | Approval succeeds even if file writing fails                         |
| **Tool Message History**        | Proper ToolMessage records in conversation state                     |
| **Extensible Architecture**     | Easy to add more tools (email, audit logs, notifications)            |

**File Format:**
```
Name | Car Number | Period | Approval Time | Reservation ID
John Smith | ABC-1234 | 2026-04-03 09:00:00 to 2026-04-03 17:00:00 | 2026-04-02 14:35:22 | Res#1
```

For detailed Stage 3 architecture and implementation details, see [STAGE3_BIND_TOOLS_UPDATE.md](./rag-and-chatbot/STAGE3_BIND_TOOLS_UPDATE.md)

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

# Test Stage 3 confirmation writer (unit tests)
cd rag-and-chatbot && python test_mcp_server.py

# Test Stage 3 integration (end-to-end with bind_tools)
cd rag-and-chatbot && python test_stage3_integration.py

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
- **[STAGE2_QUICKSTART.md](./STAGE2_QUICKSTART.md)** - Stage 2 quick start guide
- **[STAGE3_BIND_TOOLS_UPDATE.md](./rag-and-chatbot/STAGE3_BIND_TOOLS_UPDATE.md)** - Stage 3 architecture and bind_tools pattern
- **[STAGE3_README.md](./rag-and-chatbot/STAGE3_README.md)** - Stage 3 detailed implementation guide
- **[PROJECT_SCHEMA.md](./PROJECT_SCHEMA.md)** - Complete architecture overview
- **API Documentation** - Interactive docs at http://localhost:8000/docs (when API server is running)
- **Inline Code Comments** - Throughout all Python files

### Key Concepts

**Two-Agent Architecture (Stage 2):**

- User Agent has no interrupts - conversation flows freely
- Admin Agent has interrupt at execute_action node
- Both agents coordinate via shared SQLite database
- Database is the single source of truth for reservations

**LangGraph Interrupt Pattern:**

- Admin Agent execution pauses at designated interrupt node
- REST API inspects state, updates action_data, and resumes graph
- State updates trigger graph resumption and database updates
- Enables human-in-the-loop workflows for administrative actions

**Independent State Management:**

- Each agent has separate SqliteSaver checkpoint database
- User Agent: checkpoints.sqlite
- Admin Agent: admin_checkpoints.sqlite
- Prevents state conflicts between concurrent agent operations

**Automatic Polling:**

- Admin CLI detects interrupt in response
- Polls graph state every 2 seconds for new messages
- Automatically displays completion message when API resumes graph
- 120-second timeout with clear error messages

**LangGraph bind_tools Pattern (Stage 3):**

- Separate graph node dedicated to confirmation writing
- Uses `.bind_tools()` to bind confirmation tool to LLM
- LLM decides when to call the tool based on prompt
- Proper ToolMessage records in conversation history
- Conditional routing: approvals → confirmation node, rejections → END
- Clean separation: execute_action_node handles DB, write_confirmation_node handles file
