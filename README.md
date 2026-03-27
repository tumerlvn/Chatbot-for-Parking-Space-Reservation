# 🚗 SmartPark City Center - Parking Chatbot

An intelligent conversational AI system for parking facility management using RAG (Retrieval-Augmented Generation) and LangGraph.

**Current Status:** Stage 1 Complete ✅ (Pre-Reservation with Security & Evaluation)

---

## 🎯 What It Does

SmartPark Chatbot is a conversational AI assistant that helps users:

1. **Get Information** - Ask questions about parking policies, pricing, amenities, and hours
2. **Check Availability** - See real-time parking spot availability
3. **Pre-Register Intent** - Collect reservation information for admin approval

### Example Conversations

**Getting Information:**

```
You: What are your operating hours?
Bot: SmartPark is open 24/7. Staff available 8 AM - 8 PM...

You: Do you have EV charging?
Bot: Yes! Level 2 EV chargers on Level 2, Row A.
     Currently 2 EV spots available.
```

**Making a Pre-Reservation:**

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
Bot: ✓ Pre-reservation recorded. Awaiting admin approval.
```

---

## 🏗️ Architecture

```
User Input → LangGraph Router → [Q&A | Reservation] → Response
                 ↓                    ↓
            Milvus Vector DB    SQLite Database
            (Policy Knowledge)  (Availability Data)
```

**Key Technologies:**

- **LangGraph** - Conversation flow management
- **Milvus Lite** - Semantic search over policies
- **SQLite** - Real-time spot availability
- **Azure Claude** - Language understanding and generation
- **HuggingFace** - Embeddings and reranking models

---

## 🚀 Quick Start

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
jupyter notebook rag-and-chatbot/src/notebooks/test_chatbot.ipynb
```

---

## 📂 Project Structure

```
rag-and-chatbot/
├── data/
│   ├── parking.db              # Vector database (policy knowledge)
│   ├── parking_db.sqlite       # SQL database (spot availability)
│   └── parking_policy.md       # Source policy document
│
├── src/
│   ├── chatbot/
│   │   ├── state.py            # Conversation state
│   │   ├── nodes.py            # Bot logic (router, Q&A, reservation)
│   │   ├── graph.py            # Flow orchestration
│   │   ├── main.py             # Entry point
│   │   ├── guardrails.py       # Data protection & security
│   │   └── evaluation.py       # RAG performance metrics
│   │
│   └── notebooks/
│       ├── generate_data.ipynb     # Setup databases
│       ├── test_chatbot.ipynb      # Interactive testing
│       ├── test_retrieval.ipynb    # RAG pipeline testing
│       ├── test_guardrails.ipynb   # Security & PII protection tests
│       └── evaluate_rag.ipynb      # Performance evaluation suite
```

---

## ✨ Features (Stage 1)

### ✅ Implemented

| Feature                    | Description                                               |
| -------------------------- | --------------------------------------------------------- |
| **Policy Q&A**             | Semantic search over parking policies with reranking      |
| **Real-Time Availability** | Live database queries for spot counts                     |
| **Time Conflict Checking** | Prevents double-bookings by detecting overlapping reservations |
| **Intent Classification**  | Automatically routes between Q&A and reservations         |
| **Pre-Reservation**        | Collects: times, name, license plate, checks availability |
| **Smart Data Collection**  | Checks availability BEFORE asking for personal info       |
| **Guard Rails System**     | Input validation & output filtering for security and PII protection |
| **RAG Evaluation**         | Automated testing with Recall@K, Precision@K, MRR metrics |
| **Conversation Memory**    | Maintains context across multiple messages                |
| **Multi-Interface**        | CLI, Python API, and Jupyter notebook support             |

### 🛡️ Security & Data Protection

**Guard Rails System:**
- **Input Validation** - Blocks SQL injection, command injection, path traversal attacks
- **Output Filtering** - Automatically redacts PII (emails, phone numbers, SSN, credit cards)
- **System Protection** - Prevents exposure of database paths, API keys, IP addresses
- **Performance** - <1ms overhead per interaction

**Time Conflict Detection:**
- Checks for overlapping reservations before confirming availability
- Prevents double-bookings across all time ranges
- SQL-based conflict detection with 6 overlap scenarios

### 📈 Evaluation & Quality Assurance

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

## 📊 Current Parking Facility

**Available Spots: 9 total**

| Floor   | Type        | Spots        | Status         |
| ------- | ----------- | ------------ | -------------- |
| Ground  | Accessible  | G-01, G-02   | ✅ Available   |
| Ground  | Standard    | G-03         | ✅ Available   |
| Level 1 | Standard    | L1-A1, L1-A2 | ✅ Available   |
| Level 1 | Standard    | L1-A3        | 🔧 Maintenance |
| Level 2 | EV Charging | L2-A1, L2-A2 | ✅ Available   |
| Level 2 | Standard    | L2-B1        | ✅ Available   |

**Pricing:**

- Hourly: $5.00/hour
- Daily Max: $35.00
- Overnight: $15.00 (enter after 6 PM, exit before 8 AM)

---

## 🧪 Testing

### Automated Tests

```bash
# Verify environment setup
python rag-and-chatbot/src/chatbot/verify_setup.py

# Run interactive test suite
jupyter notebook rag-and-chatbot/src/notebooks/test_chatbot.ipynb

# Test guard rails (security & PII protection)
jupyter notebook rag-and-chatbot/src/notebooks/test_guardrails.ipynb

# Evaluate RAG performance (Recall, Precision, MRR)
jupyter notebook rag-and-chatbot/src/notebooks/evaluate_rag.ipynb
```

### Manual Testing Scenarios

1. **Policy Questions**
   - "What are your hours?"
   - "How much does parking cost?"
   - "Can I park my RV?"
   - "What's the cancellation policy?"

2. **Availability Questions**
   - "Are there any spots free?"
   - "Do you have EV charging available?"
   - "Are accessible spots available?"

3. **Reservations**
   - "I want to make a reservation"
   - "Book a spot for tomorrow 9 AM to 5 PM"
   - "My name is John Smith, plate ABC-123"

4. **Mixed Conversations**
   - Ask questions, then make reservation
   - Switch between topics
   - Check history

---

### Database Configuration

Databases are pre-populated. To regenerate:

```bash
jupyter notebook rag-and-chatbot/src/notebooks/generate_data.ipynb
```

---

## 📚 Documentation

- **[PHASE1.md](./PHASE1.md)** - Detailed technical documentation
- **[STAGE1_COMPLETE.md](./STAGE1_COMPLETE.md)** - Stage 1 completion summary
- **[PROJECT_SCHEMA.md](./PROJECT_SCHEMA.md)** - Complete architecture overview
- **Inline Code Comments** - Throughout all Python files

---
