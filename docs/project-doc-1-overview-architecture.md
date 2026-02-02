# QbotzChatbot - Complete Project Documentation
## Part 1: Overview & Architecture

---

## 📋 Table of Contents - Complete Documentation Series

1. **Part 1: Overview & Architecture** (This Document)
   - Project Overview
   - System Architecture
   - Technology Stack
   - High-Level Flow

2. **Part 2: Core Components - Agents & Flows** → `project-doc-2-agents-flows.md`
   - All 8 Agents Detailed
   - Execution Flows
   - Agent Interactions

3. **Part 3: Data Layer & Storage** → `project-doc-3-data-storage.md`
   - PostgreSQL Database
   - Vector Storage (pgvector)
   - Embedding Management
   - SAP Synchronization

4. **Part 4: Business Logic & Workflows** → `project-doc-4-business-logic.md`
   - Request Processing Flow
   - Intent Routing
   - Conversation Continuity
   - Visualization Pipeline

5. **Part 5: APIs & Interfaces** → `project-doc-5-apis-interfaces.md`
   - FastAPI REST API
   - Streamlit UI
   - Schemas & Data Models

---

## 🎯 Project Overview

### What is QbotzChatbot?

**QbotzChatbot** is an enterprise-grade, multi-agent AI system built to provide intelligent analytics over SAP sales data. It combines multiple AI techniques to deliver accurate, context-aware responses to natural language questions about business data.

### Core Value Proposition

- **Natural Language to SQL**: Ask questions in plain English, get precise SQL-powered analytics
- **Semantic Search**: Find patterns, trends, and insights beyond structured queries
- **Hybrid Intelligence**: Combines precision of SQL with contextual understanding of vector search
- **Conversation Memory**: Maintains context across multiple turns for natural dialogue
- **Auto-Visualization**: Automatically generates interactive charts when relevant
- **Production-Ready**: FastAPI backend, stateless design, ready for deployment

### Business Use Cases

1. **Sales Analytics**
   - "What are our top 10 customers by revenue this quarter?"
   - "Show me sales trends over the last 6 months"
   - "Which regions have the highest delivery issues?"

2. **Follow-up Questions**
   - Initial: "Who are our top customers in the EAST region?"
   - Follow-up: "Show me their order counts" (context preserved)
   - Follow-up: "Visualize this as a bar chart"

3. **Exploratory Analysis**
   - "Tell me about delivery quality trends"
   - "What patterns do you see in customer complaints?"
   - "Find sales orders with unusual characteristics"

---

## 🏗️ System Architecture

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│  ┌──────────────────────────┐    ┌─────────────────────────┐   │
│  │   Streamlit Web UI       │    │   FastAPI REST API      │   │
│  │   (Development/Testing)  │    │   (Production/Stateless)│   │
│  └────────────┬─────────────┘    └──────────┬──────────────┘   │
└───────────────┼──────────────────────────────┼──────────────────┘
                │                              │
                └──────────────┬───────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│                   ┌─────────────────────┐                        │
│                   │  SupervisorGraph    │                        │
│                   │  (LangGraph)        │                        │
│                   │  • State Management │                        │
│                   │  • Flow Control     │                        │
│                   │  • Agent Routing    │                        │
│                   └──────────┬──────────┘                        │
└──────────────────────────────┼─────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐  ┌──────────▼────────┐  ┌────────▼────────┐
│ CONVERSATION   │  │   INTENT          │  │   EXECUTION     │
│ RESOLUTION     │  │   CLASSIFICATION  │  │   FLOWS         │
│                │  │                   │  │                 │
│ • Follow-up    │  │ • ANALYTICAL      │  │ • SQL Flow      │
│   Detection    │  │ • SEMANTIC        │  │ • Vector Flow   │
│ • Context      │  │ • HYBRID          │  │ • Hybrid Flow   │
│   Expansion    │  │ • CHITCHAT        │  │ • Chitchat Flow │
└────────────────┘  └───────────────────┘  └────────┬────────┘
                                                     │
                           ┌─────────────────────────┼─────────┐
                           │                         │         │
                    ┌──────▼────────┐       ┌────────▼──────┐ │
                    │  VISUALIZATION│       │  SUMMARIZATION│ │
                    │  • Chart Gen  │       │  • NL Response│ │
                    │  • Plotly     │       │  • Formatting │ │
                    └───────────────┘       └───────────────┘ │
                                                     │         │
┌────────────────────────────────────────────────────▼─────────▼─┐
│                      AGENT LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  SQLAgent    │  │EmbeddingAgent│  │VisualizationAgent  │   │
│  │  • SQL Gen   │  │  • 768-dim   │  │  • Chart Detection │   │
│  │  • Validation│  │    Vectors   │  │  • Type Selection  │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │VectorVerifier│  │ Summarizer   │  │ConversationResolver│   │
│  │  • Quality   │  │  • NL Output │  │  • Context Tracking│   │
│  │    Scoring   │  │  • Formatting│  │  • Query Expansion │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      TOOLS LAYER                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  SQL Executor   │  │ Vector Search    │  │ Chart Generator│ │
│  │  • Query Exec   │  │ • Cosine Sim     │  │ • Plotly       │ │
│  │  • Result Parse │  │ • Top-K          │  │ • PNG Export   │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Few-Shot Store (Dynamic SQL Examples)                      ││
│  │  • Semantic Similarity Matching                             ││
│  │  • Query Pattern Library                                    ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │            PostgreSQL Database (Primary Storage)           │ │
│  │  ┌─────────────────────┐    ┌──────────────────────────┐  │ │
│  │  │  sales_orders       │    │ sales_order_embeddings   │  │ │
│  │  │  • Structured Data  │    │ • Vector Storage         │  │ │
│  │  │  • 30+ Columns      │    │ • pgvector Extension     │  │ │
│  │  │  • Indexed          │    │ • 768-dim Vectors        │  │ │
│  │  └─────────────────────┘    └──────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           Embedding Model (Singleton)                      │ │
│  │  • sentence-transformers/all-mpnet-base-v2                 │ │
│  │  • Thread-Safe Singleton Pattern                           │ │
│  │  • Loaded Once, Reused Forever (~7s load time)             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                   EXTERNAL INTEGRATIONS                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  Groq API       │  │  SAP OData API   │  │  PostgreSQL    │ │
│  │  • LLM Calls    │  │  • Data Source   │  │  • Connection  │ │
│  │  • llama-3.3    │  │  • Periodic Sync │  │    Pool        │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Agent-Based Design**: Each component has a single, well-defined responsibility
2. **State Management**: Immutable state flows through LangGraph nodes
3. **Stateless Backend**: FastAPI endpoints are stateless; all state sent by client
4. **Singleton Patterns**: Heavy resources (embedding model, DB pool) loaded once
5. **Separation of Concerns**: Clear boundaries between layers
6. **Fail-Safe Defaults**: Graceful degradation when components fail

---

## 🛠️ Technology Stack

### Core Framework & Orchestration

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **LangGraph** | 0.2.59 | Workflow orchestration | Best-in-class for multi-agent workflows, built-in state management |
| **LangChain Core** | 0.3.29 | LLM abstraction | Standard interface for LLM interactions |
| **Python** | 3.13+ | Primary language | Rich ecosystem, excellent AI/ML support |

### LLM & Embeddings

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **Groq API** | 0.13.0 | LLM provider | Extremely fast inference, cost-effective |
| **llama-3.3-70b-versatile** | Latest | Primary LLM | High accuracy, good reasoning, instruction following |
| **sentence-transformers** | 3.3.1 | Embedding generation | State-of-the-art semantic embeddings |
| **all-mpnet-base-v2** | Latest | Embedding model | 768-dim, excellent quality/speed tradeoff |

### Backend & API

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **FastAPI** | 0.115.6 | REST API framework | High performance, automatic OpenAPI docs, async support |
| **Uvicorn** | 0.34.0 | ASGI server | Production-grade, fast, supports WebSockets |
| **Pydantic** | 2.10.5 | Data validation | Type safety, automatic validation |
| **Pydantic Settings** | 2.7.1 | Configuration | Environment-aware config management |

### Database & Storage

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **PostgreSQL** | 14+ | Primary database | Robust, ACID compliant, excellent for structured data |
| **pgvector** | 0.3.7 | Vector storage | Native PostgreSQL extension, cosine similarity |
| **psycopg2-binary** | 2.9.10 | Database driver | De facto standard for PostgreSQL in Python |

### Frontend & Visualization

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **Streamlit** | 1.41.1 | Web UI | Rapid prototyping, perfect for demos and testing |
| **Plotly** | 5.18.0 | Charting library | Interactive charts, HTML export, professional quality |
| **Kaleido** | 0.2.1 | Static image export | Server-side PNG generation for charts |

### Data Processing

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **Pandas** | 2.2.3 | Data manipulation | Industry standard for tabular data |
| **NumPy** | 2.2.2 | Numerical operations | Foundation for scientific computing |

### Testing & HTTP

| Technology | Version | Purpose | Why Chosen |
|------------|---------|---------|------------|
| **Pytest** | 8.3.4 | Testing framework | Most popular Python testing framework |
| **HTTPX** | 0.28.1 | HTTP client | Async support, testing FastAPI |
| **Requests** | 2.32.3 | HTTP client | Simple, synchronous HTTP |

---

## 🔄 High-Level System Flow

### Request Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  1. USER INPUT                                                   │
│  "Show me the top 5 customers in EAST region by revenue"        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. CONVERSATION RESOLUTION (ConversationResolverAgent)          │
│  • Check if follow-up question (references previous context)    │
│  • Expand pronouns/vague references using history               │
│  • Example: "show me those customers" → "show me customers      │
│    from EAST region"                                            │
│  Output: expanded_query, is_follow_up=True/False                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. INTENT CLASSIFICATION (IntentClassifierAgent)                │
│  Analyzes query to determine execution path:                    │
│                                                                  │
│  • ANALYTICAL → Needs precise SQL (aggregations, rankings)      │
│  • SEMANTIC → Needs conceptual search (trends, patterns)        │
│  • HYBRID → Needs both (complex analytical + context)           │
│  • CHITCHAT → Casual conversation (greetings, help)             │
│                                                                  │
│  Output: intent="ANALYTICAL", confidence=0.95                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌────────────────┐
│  ANALYTICAL   │  │    SEMANTIC     │  │    HYBRID      │
│  (SQL Flow)   │  │  (Vector Flow)  │  │  (Both Flows)  │
└───────┬───────┘  └────────┬────────┘  └───────┬────────┘
        │                   │                    │
        ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. EXECUTION                                                    │
│                                                                  │
│  SQL PATH:                                                       │
│  ① SQLAgent generates PostgreSQL query                          │
│  ② Validates query (no DROP/DELETE, columns exist)              │
│  ③ Executes query → raw results                                 │
│                                                                  │
│  VECTOR PATH:                                                    │
│  ① EmbeddingAgent converts query to 768-dim vector              │
│  ② VectorSearchTool finds similar documents (cosine similarity) │
│  ③ VectorVerifierAgent scores result quality                    │
│                                                                  │
│  HYBRID PATH:                                                    │
│  ① Runs BOTH SQL + Vector flows                                 │
│  ② Merges results with weighted scoring (SQL=0.6, Vector=0.4)   │
│  ③ Deduplicates by sales_order                                  │
│                                                                  │
│  Output: sql_results=[] / vector_results=[] / hybrid_results=[] │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. VISUALIZATION (VisualizationAgent)                           │
│  • Detects if query needs visualization (keywords: chart, trend)│
│  • Determines chart type (bar, line, pie, area)                 │
│  • Calls ChartGeneratorTool to create Plotly chart              │
│  • Generates both HTML (interactive) and PNG (static) versions  │
│                                                                  │
│  Output: visualization_config={chart_html, chart_base64, ...}   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. SUMMARIZATION (SummarizerAgent)                              │
│  • Converts raw data to natural language                        │
│  • Formats numbers, dates, percentages                          │
│  • Creates user-friendly narrative                              │
│                                                                  │
│  Example Input:                                                  │
│  [{"customer": "ABC Corp", "revenue": 500000}, ...]              │
│                                                                  │
│  Example Output:                                                 │
│  "The top customer in the EAST region is ABC Corp with          │
│   $500,000 in revenue, followed by XYZ Inc with $450,000."      │
│                                                                  │
│  Output: summary="Natural language response"                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. RESPONSE                                                     │
│  {                                                               │
│    "summary": "Natural language answer",                         │
│    "intent": "ANALYTICAL",                                       │
│    "sql": "SELECT ...",                                          │
│    "visualization_config": {...},                                │
│    "metadata": {                                                 │
│      "intent_confidence": 0.95,                                  │
│      "is_follow_up": false,                                      │
│      "result_count": 5                                           │
│    }                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

### State Flow Through System

The `ChatbotState` object flows through all nodes:

```python
# Initial State (Entry)
{
    "query": "Show me top 5 customers in EAST region",
    "conversation_history": [],
    "intent": None,                    # ← To be determined
    "sql": None,                       # ← To be generated
    "sql_results": None,               # ← To be populated
    ...
}

# After Conversation Resolution
{
    "query": "Show me top 5 customers in EAST region",
    "expanded_query": "Show me top 5 customers in EAST region",  # ← Added
    "is_follow_up": False,              # ← Added
    ...
}

# After Intent Classification
{
    ...
    "intent": "ANALYTICAL",             # ← Determined
    "intent_confidence": 0.95,          # ← Scored
    ...
}

# After SQL Execution
{
    ...
    "sql": "SELECT sold_to_party_name, SUM(total_net_amount) ...",  # ← Generated
    "sql_results": [{...}, {...}, ...], # ← Populated
    ...
}

# After Visualization
{
    ...
    "should_visualize": False,          # ← Determined (no viz keywords)
    "visualization_config": None,
    ...
}

# Final State (Exit)
{
    ...
    "summary": "The top 5 customers in the EAST region are: ...",  # ← Generated
    "error": None
}
```

---

## 🎭 Multi-Agent Orchestration

### Agent Composition Pattern

Each agent follows a standard interface:

```python
class BaseAgent:
    def run(self, query: str, context: Dict) -> Dict:
        """
        Standard agent interface.
        
        Returns:
            {
                "success": True/False,
                "result": {...},          # Agent-specific output
                "error": None/str
            }
        """
```

### Supervisor Coordination

The `SupervisorGraph` orchestrates all agents:

1. **Sequential Nodes**: Conversation → Intent → Route
2. **Conditional Routing**: Based on intent, execute different flows
3. **Parallel Capable**: SQL and Vector flows can theoretically run in parallel (currently sequential)
4. **Error Handling**: Each node can set `state["error"]` to short-circuit

### Flow Composition

Flows are higher-level orchestrators that combine agents:

- **SQLFlow**: SQLAgent → Execute → Store Results
- **VectorFlow**: EmbeddingAgent → VectorSearch → VectorVerifier
- **HybridFlow**: SQLFlow + VectorFlow → Merge → Deduplicate

---

## 📊 Key System Metrics

### Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| Embedding Model Load | ~7 seconds | One-time cost (singleton) |
| Single Query Embedding | ~50-100ms | For query vectorization |
| SQL Generation | ~1-2 seconds | Depends on LLM API latency |
| SQL Execution | ~50-500ms | Depends on query complexity |
| Vector Search | ~100-300ms | Cosine similarity on 768-dim vectors |
| Visualization Generation | ~500ms-1s | Plotly chart creation + PNG export |
| Total End-to-End | ~3-5 seconds | For typical analytical query |

### Resource Requirements

| Resource | Requirement | Notes |
|----------|-------------|-------|
| Memory | ~2GB baseline | Embedding model ≈420MB, Python runtime ≈500MB |
| Database | PostgreSQL 14+ | With pgvector extension |
| CPU | 2+ cores | For concurrent request handling |
| Storage | ~500MB + data | Model weights + application code |

---

## 🔐 Security & Validation

### SQL Injection Prevention

1. **Policy Validation**: Block DROP, DELETE, UPDATE, ALTER
2. **Parameterized Queries**: All user data passed as parameters (future enhancement)
3. **Read-Only User**: Database user has SELECT-only permissions
4. **Query Limits**: Result limits enforced (configurable)

### Data Access Control

- Database credentials in environment variables (`.env`)
- API keys for Groq and SAP in secure storage
- No user data logged (privacy-first)

---

## 📁 Project Structure Overview

```
QbotzChatbot/
├── api/                          # FastAPI REST endpoints
│   ├── main.py                   # API server with /v1/chat/completions
│   └── schemas.py                # Request/Response models
│
├── config/                       # Configuration management
│   ├── settings.py               # Pydantic settings (all env vars)
│   └── dependencies.py           # Dependency injection
│
├── core/                         # Core business logic
│   ├── agents/                   # 8 specialized agents
│   ├── flows/                    # 4 execution flows
│   ├── graphs/                   # LangGraph orchestration
│   ├── storage/                  # Data layer
│   └── tools/                    # Utility tools
│
├── utility/                      # Cross-cutting concerns
│   ├── observability/            # Logging
│   └── services/                 # External integrations (SAP)
│
├── streamlit_app.py              # Web UI for testing
├── requirements.txt              # Python dependencies
└── .env                          # Environment configuration
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
PostgreSQL 14+ with pgvector extension
Python 3.13+
Groq API key

# Optional (for SAP sync)
SAP OData API access
```

### Installation

```bash
# Clone repository
cd QbotzChatbot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Running the Application

```bash
# Option 1: Streamlit UI (Development)
streamlit run streamlit_app.py

# Option 2: FastAPI Server (Production)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📚 Next Steps

Continue reading the detailed documentation:

- **Part 2: Core Components** → `project-doc-2-agents-flows.md`
  - Deep dive into all 8 agents
  - How each agent works internally
  - Flow orchestration patterns

- **Part 3: Data Layer** → `project-doc-3-data-storage.md`
  - Database schema
  - Vector storage architecture
  - Embedding generation pipeline
  - SAP synchronization

- **Part 4: Business Logic** → `project-doc-4-business-logic.md`
  - Complete request workflows
  - Intent routing logic
  - Conversation continuity
  - Visualization pipeline

- **Part 5: APIs & Interfaces** → `project-doc-5-apis-interfaces.md`
  - FastAPI endpoints
  - Streamlit UI architecture
  - Data schemas and validation

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-02  
**Authors**: QbotzChatbot Development Team
