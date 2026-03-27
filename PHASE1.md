# Phase 1: RAG-Based Q&A + Pre-Reservation System

**Status:** ✅ Complete
**Date Completed:** March 25, 2026
**Stage:** 1 - Phase 1 of 3

---

## 📋 Overview

Phase 1 implements a conversational AI system for SmartPark City Center that can:

1. Answer parking policy questions using RAG (Retrieval-Augmented Generation)
2. Collect pre-reservation data from users
3. Check real-time parking availability
4. Maintain conversation state across multiple turns

This is a **pre-reservation system** - it collects and validates booking information but does NOT yet persist reservations to the database or send admin notifications (planned for future phases).

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                           │
│         CLI / Jupyter Notebook / Python API                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  LANGGRAPH STATE MACHINE                    │
│                                                             │
│    START → Router → [RAG Node | Reservation Node] → END   │
│                                                             │
│  State: {messages, intent, reservation_data, next_action}  │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
┌────────────────────────┐  ┌────────────────────────┐
│   MILVUS VECTOR DB     │  │   SQLITE DATABASE      │
│   (Policy Knowledge)   │  │   (Operational Data)   │
│                        │  │                        │
│ • parking.db           │  │ • parking_db.sqlite    │
│ • 8 policy chunks      │  │ • 9 parking spots      │
│ • Semantic search      │  │ • 0 reservations       │
│ • Cross-encoder        │  │ • Real-time status     │
│   reranking            │  │                        │
└────────────────────────┘  └────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Azure Claude Model  │
              │  (claude-3-5-haiku)  │
              └──────────────────────┘
```

---

## 🗂️ Project Structure

```
rag-and-chatbot/
├── data/
│   ├── parking.db              # Milvus Lite vector database
│   ├── parking_db.sqlite       # SQLite operational database
│   └── parking_policy.md       # Source policy document
│
├── src/
│   ├── chatbot/
│   │   ├── __init__.py         # Package exports
│   │   ├── state.py            # GraphState & ReservationData definitions
│   │   ├── nodes.py            # Node implementations (4 nodes)
│   │   ├── graph.py            # LangGraph assembly
│   │   ├── main.py             # CLI + ParkingChatbot class
│   │   └── verify_setup.py     # Setup verification utility
│   │
│   └── notebooks/
│       ├── generate_data.ipynb      # Database initialization
│       ├── test_retrieval.ipynb     # RAG pipeline testing
│       └── test_chatbot.ipynb       # Full chatbot testing
│
└── [Root]
    ├── .env.example             # Environment template
    ├── pyproject.toml           # Dependencies
    ├── PHASE1.md                # This document
    └── README.md                # User documentation
```

**Total Code:** ~950 lines of Python across 6 modules

---

## 💾 Data Layer

### 1. Milvus Vector Database (`parking.db`)

**Purpose:** Semantic search over parking policy documents

**Configuration:**

- **Collection:** `parking_policy_collection`
- **Source:** `parking_policy.md` (47 lines)
- **Chunking Strategy:**
  - Method: RecursiveCharacterTextSplitter
  - Chunk size: 500 characters
  - Overlap: 100 characters
  - Result: 8 document chunks
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Reranking Model:** `BAAI/bge-reranker-base`

**Content Indexed:**

- General information (address, vehicle restrictions, height limits)
- Operating hours (24/7, staffed hours, after-hours access)
- Pricing ($5/hr, $35 daily max, $15 overnight)
- Reservation process (modifications, cancellations, grace periods)
- Amenities (EV charging, accessibility, security)
- Rules of conduct (speed limits, parking discipline)

**Retrieval Pipeline:**

```
Query → Embed → Milvus Search (k=10) → Cross-Encoder Rerank (top 3) → Context
```

---

### 2. SQLite Database (`parking_db.sqlite`)

**Purpose:** Store parking spot inventory and availability

#### Schema

**Table: `parking_spots`**

```sql
CREATE TABLE parking_spots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_number TEXT NOT NULL UNIQUE,       -- e.g., "G-01", "L2-A1"
    spot_type TEXT NOT NULL,                -- 'Standard', 'EV', 'Accessible'
    floor TEXT NOT NULL,                    -- 'Ground', 'Level 1', 'Level 2'
    status TEXT DEFAULT 'available',        -- 'available', 'occupied', 'maintenance'
    price_per_hour REAL DEFAULT 5.00
);
```

**Current Data (9 spots):**

```
Ground Floor:
  G-01, G-02  → Accessible (available)
  G-03        → Standard (available)

Level 1:
  L1-A1, L1-A2 → Standard (available)
  L1-A3        → Standard (maintenance)

Level 2:
  L2-A1, L2-A2 → EV (available)
  L2-B1        → Standard (available)
```

**Table: `reservations`**

```sql
CREATE TABLE reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_id INTEGER,
    user_name TEXT NOT NULL,
    car_number TEXT NOT NULL,
    reservation_time TEXT DEFAULT CURRENT_TIMESTAMP,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT DEFAULT 'pending',          -- 'pending', 'confirmed', 'cancelled'
    FOREIGN KEY (spot_id) REFERENCES parking_spots (id)
);
```

**Current Data:** Empty (no reservations persisted yet - Phase 2 feature)

---

## 🤖 LangGraph Implementation

### State Definition (`state.py`)

```python
class ReservationData(TypedDict, total=False):
    name: Optional[str]
    car_number: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    availability_checked: Optional[bool]
    available_spots: Optional[list]
    count_by_type: Optional[dict]

class GraphState(TypedDict):
    messages: Annotated[List, add_messages]  # Conversation history (with reducer)
    intent: Optional[str]                     # 'question' or 'reservation'
    reservation_data: ReservationData         # Collected booking data
    next_action: Optional[str]                # Flow control
```

**Key Design Decision:**

- `messages` uses `add_messages` reducer → appends new messages to history
- Other fields have no reducer → must be handled carefully to avoid overwrites
- `reservation_data` persists via checkpoint (not passed in invoke)

---

### Graph Structure (`graph.py`)

```
                    ┌──────────┐
                    │  START   │
                    └────┬─────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Router Node  │ ← Classifies intent
                  └──────┬───────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
    intent="question"          intent="reservation"
           │                           │
           ▼                           ▼
    ┌─────────────┐            ┌─────────────────────┐
    │  RAG Node   │            │ Reservation Node    │
    │             │            │                     │
    │ • Query     │            │ Flow:               │
    │   Milvus    │            │ 1. Ask start_time   │
    │ • Rerank    │            │ 2. Ask end_time     │
    │ • Check DB  │            │ 3. Check available  │
    │   (if about │            │ 4. Ask name         │
    │   avail.)   │            │ 5. Ask car_number   │
    │ • Generate  │            │ 6. Show summary     │
    │   answer    │            │                     │
    └─────┬───────┘            └─────────┬───────────┘
          │                              │
          └──────────────┬───────────────┘
                         │
                         ▼
                    ┌────────┐
                    │  END   │
                    └────────┘
```

**Checkpointing:** Uses `MemorySaver` to persist state across conversation turns

---

## 📦 Node Implementations (`nodes.py`)

### Node 1: Router Node

**Purpose:** Intent classification

**Process:**

1. Extract user's last message
2. Send to LLM with classification prompt
3. Parse response: "question" or "reservation"
4. Update state with intent

**Prompt Structure:**

```
Classify user message into:
- "question": Policy, pricing, amenities, availability queries
- "reservation": Booking requests or providing booking details

Respond with ONLY: "question" or "reservation"
```

**LLM:** Azure-hosted Claude 3.5 Haiku

---

### Node 2: RAG Node

**Purpose:** Answer policy questions with semantic search + real-time data

**Process:**

1. Take user's question
2. Query Milvus → Get top 10 chunks
3. Rerank with cross-encoder → Keep top 3
4. **Check if availability query** using LLM
5. If yes: Query SQLite for real-time spot counts
6. Combine policy context + real-time data
7. Generate natural language answer

**Example Output:**

```
User: "Are there EV charging spots available?"

Response: "Yes! We have Level 2 EV chargers on Level 2, Row A.

Current Real-Time Availability:
- EV: 2 spot(s) available

Standard parking rates apply while charging."
```

**Key Feature:** Automatically augments policy answers with live database data

---

### Node 3: Reservation Collector Node

**Purpose:** Collect pre-reservation data step-by-step

**Optimized Flow:**

```
Step 1: Ask start_time
Step 2: Ask end_time
Step 3: CHECK AVAILABILITY
   ├─ Available? → Show counts, continue
   └─ Full? → Inform user, reset, stop
Step 4: Ask name (only if available)
Step 5: Ask car_number (only if available)
Step 6: Show pre-reservation summary
```

**Why Times First?**

- Time is the constraint, not personal info
- Fail fast - don't collect unnecessary data if facility is full
- Better UX - user knows if booking is possible before sharing details

**Data Extraction:**

- Uses LLM to parse free-form user input
- Can extract multiple fields from one message
- Example: "John Smith, ABC-123, tomorrow 9 AM to 5 PM"

**Availability Checking:**

```python
def _check_parking_availability(start_time, end_time):
    """
    Phase 1: Simple check - status='available'
    Phase 2: Add time-range conflict checking with reservations table
    """
    SELECT spot_type, COUNT(*)
    FROM parking_spots
    WHERE status = 'available'
    GROUP BY spot_type
```

**Output:**

```
📋 Pre-Reservation Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Name: John Smith
🚗 License Plate: ABC-1234
📅 Start Time: 2026-03-17 09:00:00
📅 End Time: 2026-03-17 17:00:00
✅ Available Spots:
  • Standard: 4 spot(s)
  • EV: 2 spot(s)
  • Accessible: 2 spot(s)

✅ Status: Awaiting Admin Approval
```

**Important:** Data is collected but NOT saved to database in Phase 1

---

### Node 4: Check Availability Node (Deleted)

**Status:** Deleted

---

## 🔄 Conversation Flow Examples

### Example 1: Policy Question

```
User: "What are your operating hours?"
  ↓
Router: Classifies as "question"
  ↓
RAG Node:
  1. Embeds query
  2. Searches Milvus → Finds policy chunk
  3. Reranks results
  4. Checks if availability query → No
  5. Generates answer from policy context
  ↓
Bot: "SmartPark is open 24/7. Staff available 8 AM - 8 PM..."
```

### Example 2: Availability Question

```
User: "Do you have any EV spots free?"
  ↓
Router: Classifies as "question"
  ↓
RAG Node:
  1. Retrieves policy context about EV charging
  2. Detects availability query → Yes
  3. Queries SQLite: 2 EV spots available
  4. Combines both sources
  ↓
Bot: "Yes! Level 2 chargers on L2-A. Currently 2 EV spots available."
```

### Example 3: Successful Reservation

```
User: "I want to make a reservation"
  ↓ Router: "reservation"
  ↓ Reservation Node: No start_time
Bot: "When would you like to start parking?"

User: "Tomorrow at 9 AM"
  ↓ Reservation Node: Extract start_time, no end_time
Bot: "And when do you plan to leave?"

User: "5 PM"
  ↓ Reservation Node: Extract end_time, check availability
  ↓ SQLite Query: 8 spots available
Bot: "Great! We have spots available:
     • Standard: 4, EV: 2, Accessible: 2
     What is your full name?"

User: "John Smith"
  ↓ Reservation Node: Extract name
Bot: "What's your license plate?"

User: "ABC-1234"
  ↓ Reservation Node: Extract car_number, all data collected
Bot: "Pre-reservation recorded. Awaiting admin approval."
```

### Example 4: No Availability

```
User: "Book a spot"
Bot: "When would you like to start?"

User: "Tomorrow 9 AM"
Bot: "When will you leave?"

User: "5 PM"
  ↓ Check availability: 0 spots available
Bot: "Sorry, no spots for that time.
     Would you like to try a different time?"

[Conversation ends, no personal info collected]
```

---

## 🚀 Usage

### Installation

```bash
# Install dependencies
uv sync
# or: pip install -e .

# Set up environment
cp .env.example .env
# Edit .env and add:
#   AZURE_OPENAI_API_KEY=your-key
#   AZURE_OPENAI_ENDPOINT=your-endpoint
```

### CLI Interface

```bash
python -m rag_and_chatbot.src.chatbot.main

# Commands:
#   <message>  - Chat with bot
#   reset      - Start new conversation
#   history    - View conversation
#   exit       - Quit
```

### Python API

```python
from rag_and_chatbot.src.chatbot.main import ParkingChatbot

chatbot = ParkingChatbot()

# Ask questions
response = chatbot.chat("What are your hours?")
print(response)

# Make reservation
chatbot.chat("I want to book a spot")
chatbot.chat("Tomorrow at 9 AM")
chatbot.chat("5 PM")
chatbot.chat("John Smith")
chatbot.chat("ABC-1234")

# Get conversation history
history = chatbot.get_conversation_history()

# Reset conversation
chatbot.reset()
```

### Jupyter Notebook

```bash
jupyter notebook rag-and-chatbot/src/notebooks/test_chatbot.ipynb
```

**Notebook Contents:**

- Setup and initialization
- RAG Q&A testing
- Reservation flow testing
- Mixed conversation testing
- Conversation history viewing
- Graph visualization

---

## ✅ What Works (Phase 1 Complete)

### Core Features

- ✅ **Intent classification** - Accurate routing between Q&A and reservations
- ✅ **RAG-based Q&A** - Semantic search with reranking for policy questions
- ✅ **Real-time availability** - Augments answers with live database data
- ✅ **Pre-reservation collection** - Step-by-step data gathering with validation
- ✅ **Availability checking** - Verifies spots available before collecting personal info
- ✅ **Conversation state** - Persists data across multiple turns via checkpointing
- ✅ **Multi-turn conversations** - Natural dialogue flow
- ✅ **LLM extraction** - Intelligently parses free-form user input
- ✅ **Fail-fast design** - Stops early if no availability
- ✅ **Multiple interfaces** - CLI, Python API, Jupyter notebook

### Technical Implementation

- ✅ **LangGraph state machine** - Proper state management and routing
- ✅ **Checkpoint persistence** - Correct use of reducers and checkpoint loading
- ✅ **Azure Claude integration** - Working with Azure-hosted models
- ✅ **Vector + SQL hybrid** - Combines semantic search with structured data
- ✅ **Two-stage retrieval** - Initial retrieval + reranking for accuracy

---

## 🧪 Testing

### Test Suite

1. **`test_chatbot.ipynb`** - Full system testing
   - RAG Q&A scenarios
   - Reservation flow (happy path)
   - Mixed conversations
   - Conversation history

2. **`test_retrieval.ipynb`** - RAG pipeline testing
   - Vector search accuracy
   - Reranking effectiveness
   - SQLite queries

3. **`verify_setup.py`** - Environment validation
   - Dependency checking
   - API key verification
   - Database existence
   - Model loading

### Running Tests

```bash
# Verify setup
python rag-and-chatbot/src/chatbot/verify_setup.py

# Run Jupyter tests
jupyter notebook rag-and-chatbot/src/notebooks/test_chatbot.ipynb
```

---

## 📚 References

### Technologies Used

- **LangChain** - LLM application framework
- **LangGraph** - State machine orchestration
- **Milvus Lite** - Vector database
- **SQLite** - Relational database
- **HuggingFace** - Embedding and reranking models
- **Azure OpenAI** - Claude model hosting
- **Jupyter** - Interactive testing

### Key Libraries

```toml
langgraph = ">=0.2.70"
langchain = ">=1.2.10"
langchain-milvus = ">=0.3.3"
langchain-openai = ">=1.1.10"
sentence-transformers = ">=5.2.3"
```

---

**Status:** Phase 1 Complete ✅
