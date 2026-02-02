# QbotzChatbot - Complete Technical Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [System Flow](#system-flow)
4. [Core Components](#core-components)
5. [Detailed Component Reference](#detailed-component-reference)
6. [Storage & Data Layer](#storage--data-layer)
7. [APIs & Interfaces](#apis--interfaces)
8. [Configuration & Setup](#configuration--setup)
9. [Common Workflows](#common-workflows)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

### What is QbotzChatbot?

**QbotzChatbot** is a multi-agent AI system that answers questions about SAP sales analytics data using:
- **SQL queries** for precise analytical questions (top customers, revenue totals, etc.)
- **Vector search** for semantic/conceptual questions (trends, patterns, delivery issues)
- **Hybrid approach** combining both methods
- **Conversation memory** to handle follow-up questions

### Key Features

✅ **Multi-Agent Architecture**: Specialized agents handle different tasks  
✅ **Intent Classification**: Automatically routes queries to the right execution path  
✅ **Conversation Continuity**: Remembers context for follow-up questions  
✅ **Hybrid Search**: Combines SQL precision with semantic understanding  
✅ **Visualization**: Auto-generates charts for visual questions  
✅ **FastAPI Backend**: Stateless REST API for frontend integration  
✅ **Streamlit UI**: Interactive web interface for testing

### Tech Stack

| Layer | Technology | Version |
|-------|------------|--------|
| **Framework** | LangGraph (orchestration) | 0.2.59 |
| **API** | FastAPI | 0.115.6 |
| **Web Server** | Uvicorn | 0.34.0 |
| **LLM** | Groq API (llama-3.3-70b-versatile) | 0.13.0 |
| **Language Model Core** | LangChain Core | 0.3.29 |
| **Database** | PostgreSQL with pgvector | psycopg2-binary 2.9.10 |
| **Vector Store** | pgvector extension | 0.3.7 |
| **Embeddings** | sentence-transformers (all-mpnet-base-v2) | 3.3.1 |
| **UI** | Streamlit | 1.41.1 |
| **Data Processing** | Pandas, NumPy | 2.2.3, 2.2.2 |
| **HTTP Client** | Requests | 2.32.3 |
| **Configuration** | Pydantic Settings | 2.7.1 |
| **Testing** | Pytest, HTTPX | 8.3.4, 0.28.1 |
| **Languages** | Python | 3.13+ |

---

## Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│  ┌──────────────────┐              ┌───────────────────────┐ │
│  │  Streamlit UI    │              │   FastAPI REST API    │ │
│  │  (Interactive)   │              │   (Stateless)         │ │
│  └────────┬─────────┘              └───────────┬───────────┘ │
└───────────┼─────────────────────────────────────┼─────────────┘
            │                                     │
            └──────────────────┬──────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │  SUPERVISOR GRAPH    │
                    │  (LangGraph)         │
                    │  Orchestrates Flow   │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼─────┐         ┌─────▼──────┐        ┌─────▼─────┐
   │ Resolve  │────────▶│  Classify  │────────▶│   Route   │
   │Conversation        │  Intent    │         │ to Flow   │
   └──────────┘         └────────────┘         └─────┬─────┘
                                                      │
                        ┌─────────────────────────────┼──────────────┐
                        │                             │              │
                   ┌────▼────┐                  ┌─────▼─────┐  ┌────▼─────┐
                   │   SQL   │                  │  Vector   │  │ Hybrid   │
                   │  Flow   │                  │   Flow    │  │  Flow    │
                   └────┬────┘                  └─────┬─────┘  └────┬─────┘
                        │                             │             │
                        └─────────────┬───────────────┼─────────────┘
                                      │               │
                              ┌───────▼───────┐  ┌────▼─────┐
                              │  Visualize    │  │Summarize │
                              │  (Optional)   │──▶│ Results  │
                              └───────────────┘  └─────┬────┘
                                                       │
                                                  ┌────▼─────┐
                                                  │  RESPONSE│
                                                  │  to User │
                                                  └──────────┘
```

### Agent-Based Design

The system uses **8 specialized agents**, each with a single responsibility:

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **ConversationResolverAgent** | Resolves follow-up questions using context | User query + history | Expanded query + is_follow_up flag |
| **IntentClassifierAgent** | Classifies query type | User query | ANALYTICAL, SEMANTIC, HYBRID, or CHITCHAT |
| **SQLAgent** | Generates PostgreSQL queries | Natural language question | Valid SQL query |
| **EmbeddingAgent** | Converts text to vectors | Text query | 768-dim embedding vector |
| **VectorVerifierAgent** | Scores vector search quality | Query + search results | Confidence score (HIGH/MEDIUM/LOW) |
| **SummarizerAgent** | Converts raw data to natural language | Query + results | User-friendly summary |
| **VisualizationAgent** | Decides if/how to visualize | Query + results | Chart configuration |
| **ChitchatFlow** | Handles casual conversation | Greeting/small talk | Friendly response |

---

## System Flow

### Request Processing Flow

```
1. USER INPUT
   ↓
2. CONVERSATION RESOLUTION
   - Detects if follow-up question
   - Expands pronouns/references using history
   - Example: "Show me those customers" → "Show me customers from EAST region"
   ↓
3. INTENT CLASSIFICATION
   - Analyzes query type
   - Routes to appropriate flow
   ↓
4. EXECUTION (Based on intent)
   
   A. ANALYTICAL PATH (SQL)
      - Generate SQL query
      - Execute against PostgreSQL
      - Return structured results
   
   B. SEMANTIC PATH (Vector)
      - Generate embedding
      - Search vector database
      - Verify result quality
      - Return relevant documents
   
   C. HYBRID PATH
      - Run BOTH SQL + Vector
      - Merge results with weighted scoring
      - Return combined results
   
   D. CHITCHAT PATH
      - Generate friendly response
      - Skip data retrieval
   ↓
5. VISUALIZATION DETECTION
   - Check if query needs a chart
   - Generate config (bar/line/pie)
   ↓
6. SUMMARIZATION
   - Convert raw data to natural language
   - Format numbers, dates, etc.
   ↓
7. RETURN RESPONSE
   - Summary text
   - Metadata (intent, SQL, confidence)
   - Visualization config (if applicable)
```

### State Management

The system uses **LangGraph's StateGraph** with a `ChatbotState` object that flows through all nodes:

```python
ChatbotState = {
    # Input
    "query": str,                           # User's question
    "conversation_history": List[Turn],     # Previous messages
    
    # Intent
    "intent": "ANALYTICAL|SEMANTIC|HYBRID|CHITCHAT",
    "intent_confidence": float,
    "is_follow_up": bool,
    
    # SQL Path
    "sql": str,                             # Generated SQL
    "sql_results": List[Dict],              # Query results
    
    # Vector Path
    "expanded_query": str,                  # Resolved query
    "vector_results": List[Dict],           # Search results
    "vector_confidence": "HIGH|MEDIUM|LOW",
    
    # Hybrid Path
    "hybrid_results": List[Dict],           # Merged results
    "result_sources": Dict,                 # Source tracking
    
    # Visualization
    "should_visualize": bool,
    "visualization_config": Dict,           # Chart spec
    
    # Output
    "summary": str,                         # Final response
    "error": Optional[str]                  # Error message
}
```

---

## Core Components

### 1. Supervisor Graph (`core/graphs/supervisor.py`)

**Purpose**: Orchestra conductor - routes requests through the system

**Key Methods**:
```python
def __init__(self):
    # Initialize all agents and flows
    self.conversation_resolver = ConversationResolverAgent()
    self.intent_classifier = IntentClassifier()
    self.sql_flow = SQLExecutionFlow(SQLAgent())
    self.vector_flow = VectorExecutionFlow(...)
    self.hybrid_flow = HybridExecutionFlow(...)
    self.summarizer = SummarizerAgent()
    self.visualization_agent = VisualizationAgent()
    
    # Build LangGraph workflow
    self.graph = self._build_graph()

def run(self, query, conversation_history=None, last_turn_metadata=None):
    # Execute the entire workflow
    # Returns final state with summary
```

**Workflow**:
1. Creates StateGraph with all nodes
2. Defines edges between nodes
3. Uses conditional routing based on intent
4. Executes graph and returns final state

**Graph Structure**:
```
resolve_conversation → classify_intent → [route based on intent]
                                          ↓
                              ┌───────────┼───────────┐
                              │           │           │
                           sql_flow  vector_flow  hybrid_flow
                              │           │           │
                              └───────────┼───────────┘
                                          ↓
                                    visualize
                                          ↓
                                     summarize
                                          ↓
                                        END
```

### 2. Agents (`core/agents/`)

All agents inherit from `BaseAgent` which provides:
- Standardized `run()` method signature
- Logging via `self.logger`
- Response creation via `self._create_response()`
- Error handling

#### 2.1 ConversationResolverAgent

**File**: `core/agents/conversation_resolver_agent.py`

**Purpose**: Resolves follow-up questions by expanding references using conversation history

**Example**:
```
History:
  User: "Who are the top customers in EAST region?"
  Bot: "The top customers are..."

Current Query: "Show me their order counts"
Resolved Query: "Show me order counts for top customers in EAST region"
is_follow_up: True
```

**How it works**:
1. Checks if query has vague references ("those", "that region", "the same")
2. Looks at conversation history (last 3 turns)
3. Uses LLM to expand the query with context
4. Returns expanded query + follow-up flag

#### 2.2 IntentClassifierAgent

**File**: `core/agents/intent_classifier_agent.py`

**Purpose**: Classifies user intent to route to correct execution path

**Intent Types**:
| Intent | Description | Example |
|--------|-------------|---------|
| **ANALYTICAL** | Needs precise SQL | "Top  10 customers by revenue" |
| **SEMANTIC** | Needs conceptual search | "Delivery quality trends" |
| **HYBRID** | Needs both | "High-value customers with delivery issues" |
| **CHITCHAT** | Casual conversation | "Hello", "Thank you" |

**Classification Logic**:
```python
def _classify(self, query, context):
    # Build prompt with examples
    # Call LLM with temperature=0 (deterministic)
    # Parse JSON response: {intent, confidence, reasoning}
    # Validate intent is one of 4 types
    # Return classification
```

#### 2.3 SQLAgent

**File**: `core/agents/sql_agent.py`

**Purpose**: Generates valid PostgreSQL queries from natural language

**Key Features**:
- **Dynamic schema loading**: Reads schema from information_schema
- **Smart column prioritization**: Identifies important columns automatically
- **Few-shot learning**: Uses reference patterns from `sql-reference/query_patterns.py`
- **Validation**: Policy check + dry-run with EXPLAIN
- **Temperature=0**: Deterministic SQL generation

**Workflow**:
```python
def run(self, query, context):
    1. Generate SQL using LLM + reference patterns
    2. Validate SQL (no DROP/DELETE/UPDATE)
    3. Dry-run validate with EXPLAIN
    4. Return SQL if valid
```

**Reference Patterns**:
The agent loads 5 few-shot examples showing:
- Time series aggregations
- Top N rankings
- Contribution analysis
- Period comparisons
- Customer analytics

These guide the LLM without being copied directly.

#### 2.4 EmbeddingAgent

**File**: `core/agents/embedding_agent.py`

**Purpose**: Converts text to 768-dimensional vectors for semantic search

**Model**: sentence-transformers/all-mpnet-base-v2

**Key Method**:
```python
def run(self, query, context):
    # Uses singleton EmbeddingModelManager
    # Encodes query to vector
    # Returns embedding
```

#### 2.5 VectorVerifierAgent

**File**: `core/agents/vector_verifier_agent.py`

**Purpose**: Scores quality of vector search results

**Scoring**:
```python
HIGH:    similarity > 0.7 and count >= 5
MEDIUM:  similarity > 0.5 and count >= 3
LOW:     else
```

#### 2.6 SummarizerAgent

**File**: `core/agents/summarizer_agent.py`

**Purpose**: Converts raw query results to natural language

**Example**:
```
Input: [{"customer": "ABC Corp", "revenue": 500000}, ...]
Output: "The top customer is ABC Corp with $500,000 in revenue."
```

#### 2.7 VisualizationAgent

**File**: `core/agents/visualization_agent.py`

**Purpose**: Detects if query needs visualization and generates chart config

**Logic**:
- Keywords: "trend", "over time", "chart", "graph", "visualize"
- Result structure: Needs x_col (category/date) + y_col (numeric)
- Returns: {should_visualize, viz_config: {chart_type, x, y, data}}

#### 2.8 ChitchatFlow (not really an agent, but acts like one)

**File**: `core/flows/chitchat_flow.py`

**Purpose**: Handles non-analytical queries (greetings, help, small talk)

**Examples**:
- "Hi" → "Hello! I can help you analyze your SAP sales data..."
- "Thank you" → "You're welcome! Let me know if you need anything else."

### 3. Execution Flows (`core/flows/`)

Flows combine agents with business logic for specific execution paths.

#### 3.1 SQLExecutionFlow

**File**: `core/flows/sql_flow.py`

**Responsibility**: Generate SQL → Execute → Store results

```python
def run(self, state):
    1. Call SQLAgent to generate SQL
    2. Execute SQL using execute_sql() tool
    3. Store results in state["sql_results"]
    4. Store metadata (columns, row count)
    5. Return state
```

#### 3.2 VectorExecutionFlow

**File**: `core/flows/vector_flow.py`

**Responsibility**: Embed query → Search → Verify quality

```python
def run(self, state):
    1. Call EmbeddingAgent to get query vector
    2. Call vector_search_tool() to find similar documents
    3. Call VectorVerifierAgent to score results
    4. Store in state["vector_results"]
    5. Return state
```

#### 3.3 HybridExecutionFlow

**File**: `core/flows/hybrid_flow.py`

**Responsibility**: Run both SQL + Vector → Merge results

```python
def run(self, state):
    1. Run sql_flow.run(state)
    2. Run vector_flow.run(state)
    3. Merge results with weighted scoring:
       - SQL weight: 0.7 (default)
       - Vector weight: 0.3 (default)
    4. Deduplicate based on IDs
    5. Store in state["hybrid_results"]
    6. Return state
```

**Merging Strategy**:
- SQL results get higher weight (more precise)
- Vector results add context
- Combined and sorted by weighted score

#### 3.4 ChitchatFlow

**File**: `core/flows/chitchat_flow.py`

**Responsibility**: Generate friendly responses

```python
def run(self, state):
    1. Call LLM with chitchat prompt
    2. Store response in state["summary"]
    3. Return state
```

---

## Storage & Data Layer

### 1. PostgreSQL Database

**Connection Management**: `core/storage/sap_sync/db_queries.py`

**Primary Table**: `sales_orders`

**Schema Structure**:
```sql
CREATE TABLE sales_orders (
    sales_order VARCHAR PRIMARY KEY,
    sales_order_date DATE,
    sold_to_party VARCHAR,              -- Customer ID  
    sold_to_party_name VARCHAR,         -- Customer name
    total_net_amount NUMERIC(15, 2),    -- Revenue
    sales_organization VARCHAR,
    sales_district VARCHAR,             -- Region
    distribution_channel VARCHAR,
    material VARCHAR,                   -- Product ID
    material_description VARCHAR,       -- Product name
    order_quantity NUMERIC(15, 3),
    sales_unit VARCHAR,
    delivery_status VARCHAR,
    billing_status VARCHAR,
    customer_group VARCHAR,
    sales_office VARCHAR,
    plant VARCHAR,
    shipping_point VARCHAR,
    -- ... additional SAP fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Connection Pooling**:
```python
class DatabaseConnection:
    """Thread-safe PostgreSQL connection pool manager."""
    
    _pool = None  # Global connection pool
    _lock = threading.Lock()
    
    @classmethod
    def initialize_pool(cls):
        """Initialize connection pool with settings from config."""
        if cls._pool is None:
            with cls._lock:
                if cls._pool is None:
                    cls._pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=1,
                        maxconn=settings.DB_POOL_SIZE,
                        dsn=settings.DATABASE_URL
                    )
    
    @classmethod
    def get_connection(cls):
        """Get connection from pool."""
        cls.initialize_pool()
        return cls._pool.getconn()
    
    @classmethod
    def return_connection(cls, conn):
        """Return connection to pool."""
        if cls._pool:
            cls._pool.putconn(conn)
```

**Key Operations** (in `db_queries.py`, 15632 bytes):
- `get_schema_info()` - Dynamically fetches table schema
- `get_sales_orders(filters)` - Query with dynamic WHERE clauses
- `upsert_sales_order(data)` - Insert or update records
- `bulk_upsert(records)` - Batch operations for performance

### 2. Vector Database (pgvector)

**Extension**: PostgreSQL with pgvector for vector similarity search

**Storage Table**: `sales_order_embeddings`

**Schema**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sales_order_embeddings (
    id SERIAL PRIMARY KEY,
    sales_order_id VARCHAR UNIQUE,      -- FK to sales_orders
    content TEXT,                       -- Formatted sales order text
    embedding VECTOR(768),              -- 768-dim embedding vector
    metadata JSONB,                     -- Additional searchable data
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast cosine similarity search
CREATE INDEX ON sales_order_embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
```

**Operations**: `core/storage/vector_operation/vector_operations.py` (2270 bytes)

```python
def search_similar_vectors(
    query_embedding: List[float], 
    limit: int = 10,
    threshold: float = 0.5
) -> List[Dict]:
    """
    Search for similar sales orders using cosine similarity.
    
    Args:
        query_embedding: 768-dim vector from user query
        limit: Max results to return
        threshold: Minimum similarity score (0-1)
    
    Returns:
        List of {sales_order_id, content, similarity, metadata}
    """
    sql = """
        SELECT 
            sales_order_id,
            content,
            metadata,
            1 - (embedding <=> %s::vector) AS similarity
        FROM sales_order_embeddings
        WHERE 1 - (embedding <=> %s::vector) > %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    # Execute and return results
```

**Similarity Operator**: `<=>` (cosine distance, lower = more similar)

### 3. Embedding Model Management (Singleton Pattern)

**Location**: `core/storage/embedding/`

**Why Singleton?**
- Model loading takes ~7 seconds
- Model is 420MB in memory
- Loading per-request would be prohibitively slow
- Singleton loads once, reuses forever

**Key Files**:

#### `embedding_manager.py` (1754 bytes) - Thread-Safe Singleton
```python
import threading
from typing import Optional

class EmbeddingModelManager:
    """Thread-safe singleton for embedding model."""
    
    _instance: Optional['EmbeddingModel'] = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'EmbeddingModel':
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:  # Double-checked locking
                if cls._instance is None:
                    from .embedding_model import EmbeddingModel
                    cls._instance = EmbeddingModel()
        return cls._instance
```

#### `embedding_model.py` (2005 bytes) - SentenceTransformer Wrapper
```python
from sentence_transformers import SentenceTransformer
from config.settings import settings

class EmbeddingModel:
    """Wrapper around sentence-transformers model."""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.model = SentenceTransformer(self.model_name)
        self.dimension = settings.EMBEDDING_DIMENSION
    
    def encode_single(self, text: str) -> List[float]:
        """Encode single text to 768-dim vector."""
        return self.model.encode(text, convert_to_numpy=True).tolist()
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts efficiently."""
        embeddings = self.model.encode(
            texts, 
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            show_progress_bar=True
        )
        return embeddings.tolist()
```

#### `text_formatter.py` (2127 bytes) - Sales Order Formatting
```python
def format_sales_order_for_embedding(order: Dict) -> str:
    """
    Format sales order into natural language for embedding.
    
    Example output:
    "Sales order 12345 from customer ABC Corp (region EAST) 
     for product Widget XL, quantity 100 units, 
     total amount $50,000 on 2024-01-15"
    """
    return f"""
    Sales order {order['sales_order']} from customer {order['sold_to_party_name']} 
    (region {order['sales_district']}) for product {order['material_description']}, 
    quantity {order['order_quantity']} {order['sales_unit']}, 
    total amount ${order['total_net_amount']:,.2f} on {order['sales_order_date']}
    """.strip()
```

#### `embedding_service.py` (4457 bytes) - Batch Operations
```python
def generate_and_store_embeddings(sales_orders: List[Dict]):
    """Generate embeddings for sales orders and store in DB."""
    model = EmbeddingModelManager.get_instance()
    
    # Format orders as text
    texts = [format_sales_order_for_embedding(order) for order in sales_orders]
    
    # Generate embeddings in batches
    embeddings = model.encode_batch(texts)
    
    # Upsert to vector DB
    for order, text, embedding in zip(sales_orders, texts, embeddings):
        upsert_embedding(
            sales_order_id=order['sales_order'],
            content=text,
            embedding=embedding,
            metadata={"customer": order['sold_to_party_name']}
        )
```

**Usage Throughout Codebase**:
```python
from core.storage.embedding import EmbeddingModelManager

# Get singleton instance (fast after first call)
model = EmbeddingModelManager.get_instance()

# Encode query
embedding = model.encode_single("Show me delivery issues")
```

### 4. SAP Data Synchronization

**Location**: `core/storage/sap_sync/`

**Purpose**: Periodically sync SAP sales data to local PostgreSQL

**Key Files**:

#### `sap_sync.py` (3844 bytes) - Main Orchestrator
```python
def sync_sales_data(
    lookback_days: int = 90,
    batch_size: int = 1000
):
    """Sync sales orders from SAP to local DB."""
    # 1. Fetch from SAP OData API
    sap_client = SAPClient()
    orders = sap_client.fetch_sales_orders(
        from_date=date.today() - timedelta(days=lookback_days)
    )
    
    # 2. Transform to local schema
    transformed = [transform_sap_order(order) for order in orders]
    
    # 3. Upsert to PostgreSQL
    bulk_upsert_sales_orders(transformed)
    
    # 4. Generate embeddings
    generate_and_store_embeddings(transformed)
```

#### `transformers.py` (11143 bytes) - Data Mapping
```python
def transform_sap_order(sap_data: Dict) -> Dict:
    """Transform SAP OData format to PostgreSQL schema."""
    return {
        'sales_order': sap_data['SalesOrder'],
        'sales_order_date': parse_sap_date(sap_data['SalesOrderDate']),
        'sold_to_party': sap_data['SoldToParty'],
        'sold_to_party_name': sap_data['SoldToPartyName'],
        'total_net_amount': Decimal(sap_data['TotalNetAmount']),
        'sales_district': sap_data['SalesDistrict'],
        # ... map all 30+ fields
    }
```

#### `upsert_operations.py` (7873 bytes) - Bulk Database Operations
```python
def bulk_upsert_sales_orders(records: List[Dict]):
    """Efficiently upsert many records using COPY or INSERT ON CONFLICT."""
    sql = """
        INSERT INTO sales_orders (
            sales_order, sales_order_date, sold_to_party, ...
        ) VALUES %s
        ON CONFLICT (sales_order) DO UPDATE SET
            total_net_amount = EXCLUDED.total_net_amount,
            updated_at = NOW()
    """
    # Use psycopg2.extras.execute_values for performance
```

**Sync Workflow**:
```
1. SAP OData API  →  Fetch recent sales orders
2. Transformers   →  Map SAP fields to local schema
3. DB Upsert      →  Insert new or update existing orders
4. Embedding Gen  →  Create vectors for semantic search
5. Vector Store   →  Save embeddings to pgvector
```

### 5. Utility Modules

**Location**: `utility/`

#### Structured Logging (`utility/observability/logger.py` - 4546 bytes)

**Purpose**: Centralized, structured logging for all components

**Key Features**:
- **Environment-aware formatting**: JSON in production, human-readable in development
- **Contextual logging**: Add arbitrary key-value pairs to logs
- **Color-coded console**: Different colors for DEBUG/INFO/WARNING/ERROR
- **Component tagging**: Every log tagged with component name

**Implementation**:
```python
class StructuredLogger:
    """Structured logger with JSON and human-readable formatters."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        self.name = name
        
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        handler = logging.StreamHandler(sys.stdout)
        
        # Choose formatter based on environment
        if settings.ENVIRONMENT == "production":
            handler.setFormatter(JSONFormatter())       # Machine-readable
        else:
            handler.setFormatter(HumanReadableFormatter())  # Human-readable
        
        self.logger.addHandler(handler)
    
    def info(self, event: str, **kwargs):
        """Log info with arbitrary context."""
        self._log("INFO", event, kwargs)
    
    def error(self, event: str, error: Optional[Exception] = None, **kwargs):
        """Log error with exception details."""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
        self._log("ERROR", event, kwargs)
    
    def debug(self, event: str, **kwargs):
        """Log debug information."""
        self._log("DEBUG", event, kwargs)
    
    def warning(self, event: str, **kwargs):
        """Log warning."""
        self._log("WARNING", event, kwargs)
    
    def _log(self, level: str, event: str, context: Dict[str, Any]):
        """Internal logging method."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "component": self.name,
            "event": event,
            **context  # Merge in extra context
        }
        log_method = getattr(self.logger, level.lower())
        log_method(event, extra=log_data)
```

**JSON Formatter** (Production):
```python
class JSONFormatter(logging.Formatter):
    """Formats logs as JSON for log aggregation systems."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": getattr(record, "timestamp", ""),
            "level": record.levelname,
            "component": getattr(record, "component", ""),
            "event": record.getMessage(),
        }
        # Add all extra fields from logger.info(event, key=value)
        for key, value in record.__dict__.items():
            if key not in [standard_python_logging_fields]:
                log_obj[key] = value
        return json.dumps(log_obj)
```

**Human-Readable Formatter** (Development):
```python
class HumanReadableFormatter(logging.Formatter):
    """Color-coded, human-friendly log formatter."""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "RESET": "\033[0m",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = getattr(record, "timestamp", datetime.utcnow().isoformat())
        component = getattr(record, "component", "unknown")
        event = record.getMessage()
        
        # Collect extra fields
        extras = []
        for key, value in record.__dict__.items():
            if key not in [standard_fields]:
                extras.append(f"{key}={value}")
        
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        
        return f"{color}[{timestamp[:19]}] {record.levelname:8} [{component}] {event} {' '.join(extras)}{reset}"
```

**Usage Examples**:
```python
from utility.observability.logger import get_logger

logger = get_logger("sql_agent")

# Simple logging
logger.info("sql_generated")

# With context
logger.info("sql_generated", query="top customers", sql_length=250)

# Error logging
logger.error("sql_execution_failed", error=exception, query="SELECT...")

# Debug logging
logger.debug("agent_state", state_keys=list(state.keys()))
```

**Example Output** (Development):
```
[2024-01-26T11:20:45] INFO     [sql_agent] sql_generated query=top customers sql_length=250
[2024-01-26T11:20:46] ERROR    [sql_agent] sql_execution_failed error_type=PostgresError error_message=column not found
```

**Example Output** (Production):
```json
{"timestamp":"2024-01-26T11:20:45Z","level":"INFO","component":"sql_agent","event":"sql_generated","query":"top customers","sql_length":250}
```

#### SAP Client (`utility/services/sap_client.py` - 4441 bytes)

**Purpose**: HTTP client for SAP OData API

**Implementation**:
```python
import requests
from requests.auth import HTTPBasicAuth
from config.settings import settings
from utility.observability.logger import get_logger

logger = get_logger("sap_client")

class SAPClient:
    """Client for SAP OData API."""
    
    def __init__(self):
        self.base_url = settings.SAP_BASE_URL
        self.auth = HTTPBasicAuth(
            settings.SAP_USERNAME, 
            settings.SAP_PASSWORD
        )
        self.client = settings.SAP_CLIENT
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def fetch_sales_orders(
        self, 
        from_date: date = None,
        to_date: date = None,
        batch_size: int = 1000
    ) -> List[Dict]:
        """
        Fetch sales orders from SAP OData API with pagination.
        
        Args:
            from_date: Start date filter
            to_date: End date filter  
            batch_size: Records per API call
        
        Returns:
            List of sales order dictionaries
        """
        endpoint = f"{self.base_url}/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder"
        
        # Build OData filter
        filters = []
        if from_date:
            filters.append(f"SalesOrderDate ge '{from_date.isoformat()}'")
        if to_date:
            filters.append(f"SalesOrderDate le '{to_date.isoformat()}'")
        
        params = {
            'sap-client': self.client,
            '$top': batch_size,
            '$skip': 0,
            '$format': 'json'
        }
        if filters:
            params['$filter'] = ' and '.join(filters)
        
        all_orders = []
        while True:
            logger.debug("sap_fetch_batch", skip=params['$skip'], top=params['$top'])
            
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            orders = data.get('d', {}).get('results', [])
            
            if not orders:
                break
            
            all_orders.extend(orders)
            logger.info("sap_batch_fetched", count=len(orders), total=len(all_orders))
            
            # Pagination
            params['$skip'] += batch_size
        
        logger.info("sap_fetch_complete", total_orders=len(all_orders))
        return all_orders
```

**Features**:
- **Authentication**: HTTP Basic Auth
- **Pagination**: Handles large result sets with `$skip` and `$top`
- **Filtering**: OData date range filters
- **Error Handling**: Raises HTTP errors automatically
- **Logging**: Structured logs at each step

---

## APIs & Interfaces

### 1. FastAPI Backend

**File**: `api/main.py`

**Endpoint**: `POST /v1/chat/completions`

**Request**:
```json
{
    "messages": [
        {"role": "user", "content": "Show me top customers"},
        {"role": "assistant", "content": "The top customers are..."},
        {"role": "user", "content": "What about EAST region?"}
    ]
}
```

**Response**:
```json
{
    "role": "assistant",
    "content": "In EAST region, the top customers are...",
    "intent": "ANALYTICAL",
    "sql": "SELECT ...",
    "metadata": {
        "intent_confidence": 0.95,
        "sql_results_count": 10
    }
}
```

**Architecture**: **Stateless**
- Client sends full conversation history
- Server processes and returns response
- No session management on backend
- Scalable and cloud-friendly

### 2. Streamlit UI

**File**: `streamlit_app.py`

**Features**:
- Chat interface
- Conversation history (last 10 messages)
- Metadata expansion (intent, SQL, follow-up status)
- Visualization rendering
- Clear chat button

**State Management**:
```python
st.session_state.conversation_history = []  # List of messages
st.session_state.last_turn_metadata = {}    # For follow-up context
st.session_state.supervisor = SupervisorGraph()  # Singleton
```

**Flow**:
1. User types message
2. Call supervisor.run()
3. Display response
4. Render visualization if needed
5. Store in history
6. Update metadata for next turn

---

## Configuration & Setup

### Environment Variables

**File**: `.env`

```bash
# ========== Database Configuration ==========
DATABASE_URL="postgresql://user:pass@localhost:5466/qbotz_db"  # Required
DB_POOL_SIZE=10                          # Default: 10
DB_MAX_OVERFLOW=20                       # Default: 20

# ========== Vector Database ==========
VECTOR_DIMENSION=768                     # Default: 768 (matches all-mpnet-base-v2)

# ========== Groq LLM Configuration ==========
GROQ_API_KEY="gsk_..."                   # Required - Get from https://console.groq.com
GROQ_MODEL="llama-3.3-70b-versatile"    # Default: llama-3.3-70b-versatile
GROQ_RATE_LIMIT=30                       # Default: 30 requests/minute

# ========== Embedding Model ==========
EMBEDDING_MODEL="all-mpnet-base-v2"     # Default: all-mpnet-base-v2
EMBEDDING_DIMENSION=768                  # Default: 768
EMBEDDING_BATCH_SIZE=32                  # Default: 32 (for batch operations)

# ========== SAP Connection ==========
SAP_BASE_URL="https://your-sap-server.com"  # Required
SAP_USERNAME="your_username"             # Required
SAP_PASSWORD="your_password"             # Required
SAP_CLIENT="140"                         # Default: 140

# ========== SAP Sync Configuration ==========
SAP_SYNC_INTERVAL_HOURS=6                # Default: 6 (sync every 6 hours)
SAP_SYNC_LOOKBACK_DAYS=90                # Default: 90 (sync last 90 days of data)

# ========== Observability ==========
LOG_LEVEL="INFO"                         # Default: INFO (DEBUG|INFO|WARNING|ERROR)
ENABLE_QUERY_LOGGING=true                # Default: true (set false in production)

# ========== Caching ==========
CACHE_TTL_SECONDS=300                    # Default: 300 (5 minutes)

# ========== Hybrid Search Weights ==========
HYBRID_SQL_WEIGHT=0.6                    # Default: 0.6 (60% weight to SQL results)
HYBRID_VECTOR_WEIGHT=0.4                 # Default: 0.4 (40% weight to vector results)
HYBRID_MAX_RESULTS=20                    # Default: 20 (max combined results)
HYBRID_DEDUP_ENABLED=true                # Default: true (deduplicate by sales_order)

# ========== Application ==========
APP_NAME="Qbotz-Chatbot"                 # Default: Qbotz-Chatbot
ENVIRONMENT="development"                # Default: development (development|staging|production)
```

### Settings Module

**File**: `config/settings.py`

**Purpose**: Centralized configuration using Pydantic Settings with automatic `.env` loading

**All Configuration Variables**:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal

class Settings(BaseSettings):
    # ===== Database Configuration =====
    DATABASE_URL: str                      # PostgreSQL connection string (REQUIRED)
    DB_POOL_SIZE: int = 10                 # Connection pool size
    DB_MAX_OVERFLOW: int = 20              # Max connections beyond pool size
    
    # ===== PgVector Configuration =====
    VECTOR_DIMENSION: int = 768            # Embedding vector dimensions
    
    # ===== GROQ Configuration =====
    GROQ_API_KEY: str                      # Groq API key (REQUIRED)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # LLM model name
    GROQ_RATE_LIMIT: int = 30              # API rate limit (requests/min)
    
    # ===== Embedding Configuration =====
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"  # Sentence transformer model
    EMBEDDING_DIMENSION: int = 768          # Must match VECTOR_DIMENSION
    EMBEDDING_BATCH_SIZE: int = 32          # Batch size for bulk embedding
    
    # ===== SAP Configuration =====
    SAP_BASE_URL: str                       # SAP OData base URL (REQUIRED)
    SAP_USERNAME: str                       # SAP username (REQUIRED)
    SAP_PASSWORD: str                       # SAP password (REQUIRED)
    SAP_CLIENT: str = "140"                 # SAP client number
    
    # ===== SyncJob Configuration =====
    SAP_SYNC_INTERVAL_HOURS: int = 6        # Hours between sync jobs
    SAP_SYNC_LOOKBACK_DAYS: int = 90        # Days of historical data to sync
    
    # ===== Observability =====
    LOG_LEVEL: str = "INFO"                 # Logging level (DEBUG|INFO|WARNING|ERROR)
    ENABLE_QUERY_LOGGING: bool = True       # Log all SQL queries (disable in prod)
    
    # ===== Cache Configuration =====
    CACHE_TTL_SECONDS: int = 300            # Cache time-to-live (5 minutes)
    
    # ===== Hybrid Search Configuration =====
    HYBRID_SQL_WEIGHT: float = 0.6          # Weight for SQL results (0.0 - 1.0)
    HYBRID_VECTOR_WEIGHT: float = 0.4       # Weight for vector results (0.0 - 1.0)
    HYBRID_MAX_RESULTS: int = 20            # Max results from hybrid search
    HYBRID_DEDUP_ENABLED: bool = True       # Enable deduplication by sales_order
    
    # ===== Application =====
    APP_NAME: str = "Qbotz-Chatbot"         # Application name
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    
    # Pydantic V2 Configuration
    model_config = SettingsConfigDict(
        env_file=".env",              # Auto-load from .env file
        env_file_encoding="utf-8",    # UTF-8 encoding
        case_sensitive=False,         # Case-insensitive env vars
        extra="ignore"                # Ignore extra env vars
    )

# Global settings instance
settings = Settings()
```

**Usage Throughout Codebase**:
```python
from config.settings import settings

# Access any setting
model = settings.GROQ_MODEL                    # "llama-3.3-70b-versatile"
db_url = settings.DATABASE_URL                 # "postgresql://..."
sql_weight = settings.HYBRID_SQL_WEIGHT        # 0.6
```

### Installation

```bash
# 1. Clone repository
git clone <repo-url>
cd QbotzChatbot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up PostgreSQL
# - Install PostgreSQL 14+
# - Install pgvector extension
# - Create database: qbotz_db

# 5. Configure .env
cp .env.example .env
# Edit .env with your credentials

# 6. Run migrations (if any)
# python scripts/init_db.py

# 7. Sync SAP data
python -m core.storage.sap_sync.sap_sync

# 8. Start application
# Option A: Streamlit UI
streamlit run streamlit_app.py

# Option B: FastAPI
python api/main.py
```

---

## Common Workflows

### Workflow 1: Adding a New Agent

1. **Create agent file** in `core/agents/`
```python
from core.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("my_agent")
        # Initialize resources
    
    def run(self, query, context=None):
        try:
            # Your logic here
            result = self._process(query)
            return self._create_response(success=True, result=result)
        except Exception as e:
            return self._handle_error(e, query)
```

2. **Import in supervisor** (`core/graphs/supervisor.py`)
```python
from core.agents.my_agent import MyAgent

class SupervisorGraph:
    def __init__(self):
        self.my_agent = MyAgent()
```

3. **Use in workflow**
```python
def _my_node(self, state):
    result = self.my_agent.run(state["query"])
    if result["success"]:
        state["my_result"] = result["result"]
    return state
```

### Workflow 2: Adding a New Execution Flow

1. **Create flow file** in `core/flows/`
```python
class MyFlow:
    def __init__(self, agent1, agent2):
        self.agent1 = agent1
        self.agent2 = agent2
    
    def run(self, state):
        # Step 1: Agent 1
        result1 = self.agent1.run(state["query"])
        
        # Step 2: Agent 2
        result2 = self.agent2.run(result1)
        
        # Update state
        state["my_results"] = result2
        return state
```

2. **Initialize in supervisor**
```python
self.my_flow = MyFlow(Agent1(), Agent2())
```

3. **Add to routing**
```python
def _route(self, state):
    intent = state.get("intent")
    if intent == "MY_INTENT":
        return "my_flow"
    # ... other routes
```

### Workflow 3: Modifying Intent Classification

**File**: `core/agents/intent_classifier_agent.py`

1. **Add new intent type**
```python
# In prompt
"""
5. MY_NEW_INTENT - Description:
   - Use case 1
   - Use case 2
   Examples: "..."
"""
```

2. **Update validation**
```python
if classification["intent"] not in [
    "ANALYTICAL", "SEMANTIC", "HYBRID", "CHITCHAT", "MY_NEW_INTENT"
]:
    # error handling
```

3. **Add route in supervisor**
```python
def _route(self, state):
    intent_map = {
        "MY_NEW_INTENT": "my_new_flow",
        # ... existing mappings
    }
    return intent_map.get(intent, "chitchat")
```

### Workflow 4: Adding SQL Reference Patterns

**File**: `sql-reference/query_patterns.py`

1. **Add pattern template**
```python
QUERY_PATTERNS["12_my_pattern"] = {
    "description": "What this pattern does",
    "pattern": """
    SELECT ...
    FROM ...
    WHERE ...
    """,
    "use_cases": ["use case 1", "use case 2"]
}
```

2. **Add few-shot example**
```python
FEW_SHOT_EXAMPLES.append({
    "question": "Example question",
    "sql": """
    SELECT col1, SUM(col2) as total
    FROM table
    GROUP BY col1
    ORDER BY total DESC
    LIMIT 10;
    """,
    "pattern_used": "12_my_pattern"
})
```

3. **Adjust number of examples** (optional)

In `core/agents/sql_agent.py`:
```python
self.few_shot_examples = get_few_shot_examples_text(max_examples=7)
```

---

## Troubleshooting

### Common Issues

#### 1. "DatabaseConnection error: Connection refused"

**Cause**: PostgreSQL not running or wrong credentials

**Fix**:
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Check .env has correct DATABASE_URL
DATABASE_URL="postgresql://user:pass@localhost:5432/qbotz_db"
```

#### 2. "ModuleNotFoundError: No module named 'core'"

**Cause**: Running from wrong directory or PYTHONPATH not set

**Fix**:
```bash
# Run from project root
cd QbotzChatbot

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/QbotzChatbot"
```

#### 3. "Embedding model loading takes too long"

**Cause**: Model loading on every request, singleton not working

**Fix**:
```python
# Pre-load in __init__
from core.storage.embedding import EmbeddingModelManager
EmbeddingModelManager.get_instance()  # Load once at startup
```

#### 4. "SQL generation is inconsistent"

**Cause**: Temperature not set to 0

**Fix**: Verify in `core/agents/sql_agent.py` line ~552:
```python
response = self.llm.chat.completions.create(
    model=settings.GROQ_MODEL,
    messages=[...],
    temperature=0,  # Must be 0 for deterministic output
    max_tokens=1500
)
```

#### 5. "Intent classification failing"

**Cause**: LLM returning non-JSON or invalid intent

**Fix**: Check logs for JSON parse errors, add better error handling:
```python
try:
    classification = json.loads(result_text)
except json.JSONDecodeError:
    # Fallback to ANALYTICAL
    return {"intent": "ANALYTICAL", "confidence": 0.5, ...}
```

### Debugging Tips

1. **Enable debug logging**
```bash
LOG_LEVEL="DEBUG"
```

2. **Check agent outputs**
```python
result = agent.run(query)
print("Success:", result["success"])
print("Result:", result.get("result"))
print("Error:", result.get("error"))
```

3. **Inspect state at each node**
```python
def _my_node(self, state):
    print("State before:", state)
    # ... process
    print("State after:", state)
    return state
```

4. **Test individual components**
```python
# Test SQL agent standalone
from core.agents.sql_agent import SQLAgent
agent = SQLAgent()
result = agent.run("Show me top 10 customers")
print(result)
```

---

## Appendix: Complete File Structure

```
QbotzChatbot/
│
├── .env                                    # Environment variables (DATABASE_URL, GROQ_API_KEY, etc.)
├── .gitignore                             # Git ignore rules
├── requirements.txt                        # Python dependencies (30 packages)
├── streamlit_app.py                       # Streamlit UI (176 lines)
├── test_api_stateless.py                  # API integration tests
├── CODEBASE_DOCUMENTATION.md              # This file - comprehensive technical documentation
├── SYSTEM_ANALYSIS_AND_CACHING_STRATEGY.md # System analysis and caching architecture
│
├── api/                                   # FastAPI REST API Backend
│   ├── __init__.py
│   ├── main.py                           # API endpoints (/health, /v1/chat/completions)
│   └── schemas.py                        # Pydantic models (ChatRequest, ChatResponse, Message)
│
├── config/                                # Application Configuration
│   ├── __init__.py
│   ├── settings.py                       # Pydantic Settings (58 lines, 20+ config variables)
│   └── dependencies.py                   # Dependency injection patterns
│
├── core/                                  # Core Business Logic (62 files total)
│   │
│   ├── agents/                           # 8 Specialized AI Agents (16 files)
│   │   ├── __init__.py
│   │   ├── base_agent.py                # Abstract base class (1453 bytes)
│   │   ├── conversation_resolver_agent.py  # Resolves follow-up questions (6592 bytes)
│   │   ├── intent_classifier_agent.py   # Routes to SQL/Vector/Hybrid/Chitchat (5530 bytes)
│   │   ├── sql_agent.py                 # Generates PostgreSQL queries (22257 bytes)
│   │   ├── embedding_agent.py           # Converts text to 768-dim vectors (3502 bytes)
│   │   ├── vector_verifier_agent.py     # Validates vector search quality (6585 bytes)
│   │   ├── summarizer_agent.py          # Converts data to natural language (7506 bytes)
│   │   └── visualization_agent.py       # Generates chart configs (7900 bytes)
│   │
│   ├── flows/                            # 4 Execution Flow Orchestrators (8 files)
│   │   ├── __init__.py
│   │   ├── sql_flow.py                  # SQL execution pipeline (1581 bytes)
│   │   ├── vector_flow.py               # Vector search pipeline (1444 bytes)
│   │   ├── hybrid_flow.py               # Merges SQL + Vector results (6185 bytes)
│   │   └── chitchat_flow.py             # Handles casual conversation (1167 bytes)
│   │
│   ├── graphs/                           # LangGraph State Management (6 files)
│   │   ├── __init__.py
│   │   ├── supervisor.py                # Main orchestration graph (8088 bytes, 225 lines)
│   │   ├── state.py                     # ChatbotState TypedDict (1823 bytes, 67 lines)
│   │   └── conversation_utils.py        # Conversation history utilities (4309 bytes)
│   │
│   ├── storage/                          # Data Persistence Layer (26 files)
│   │   │
│   │   ├── embedding/                   # Embedding Model Management (10 files)
│   │   │   ├── __init__.py             # Exports EmbeddingModelManager
│   │   │   ├── embedding_manager.py    # Thread-safe singleton (1754 bytes)
│   │   │   ├── embedding_model.py      # SentenceTransformer wrapper (2005 bytes)
│   │   │   ├── embedding_service.py    # Batch embedding operations (4457 bytes)
│   │   │   └── text_formatter.py       # Formats sales orders for embedding (2127 bytes)
│   │   │
│   │   ├── sap_sync/                   # SAP Data Synchronization (10 files)
│   │   │   ├── __init__.py            # Exports sync functions
│   │   │   ├── sap_sync.py            # Main sync orchestrator (3844 bytes)
│   │   │   ├── db_queries.py          # PostgreSQL CRUD operations (15632 bytes)
│   │   │   ├── transformers.py        # SAP → PostgreSQL data transformation (11143 bytes)
│   │   │   └── upsert_operations.py   # Insert/update logic (7873 bytes)
│   │   │
│   │   └── vector_operation/           # Vector Database Operations (2 files)
│   │       └── vector_operations.py   # pgvector cosine similarity search (2270 bytes)
│   │
│   └── tools/                           # Execution Tools (6 files)
│       ├── __init__.py                 # Exports execute_sql, vector_search
│       ├── sql_executor.py            # PostgreSQL query execution (1331 bytes)
│       └── vector_search_tool.py      # Vector similarity search (2217 bytes)
│
├── sql-reference/                        # SQL Query Reference Library
│   └── query_patterns.py                # 11 pattern templates + 5 few-shot examples (14817 bytes)
│
└── utility/                              # Shared Infrastructure (8 files)
    │
    ├── observability/                   # Logging Infrastructure (4 files)
    │   ├── __init__.py
    │   └── logger.py                   # Structured logging with JSON/Human formatters (4546 bytes)
    │
    └── services/                        # External Service Clients (4 files)
        ├── __init__.py
        └── sap_client.py               # SAP OData API client (4441 bytes)
```

### File Count Summary

| Directory | Files | Purpose |
|-----------|-------|--------|
| **api/** | 3 | FastAPI REST endpoints |
| **config/** | 3 | Application settings |
| **core/agents/** | 8 | AI agents (SQL, embedding, intent, etc.) |
| **core/flows/** | 4 | Execution pipelines |
| **core/graphs/** | 3 | LangGraph orchestration |
| **core/storage/embedding/** | 4 | Embedding model management |
| **core/storage/sap_sync/** | 4 | SAP data synchronization |
| **core/storage/vector_operation/** | 1 | Vector search operations |
| **core/tools/** | 2 | SQL and vector tools |
| **sql-reference/** | 1 | SQL query patterns |
| **utility/observability/** | 1 | Logging framework |
| **utility/services/** | 1 | SAP client |
| **Root** | 5 | Streamlit UI, tests, config |
| **TOTAL** | **40+ files** | Complete chatbot system |

---

## Key Concepts for Junior Developers

### 1. Multi-Agent Systems

**What**: Breaking a complex task into specialized sub-tasks handled by different agents

**Why**: 
- Easier to test individual components
- Can swap/upgrade agents independently
- Clear separation of concerns
- Easier to debug

**Example**: Instead of one "do everything" function, we have:
- ConversationResolver: Handles context
- IntentClassifier: Routes requests
- SQLAgent: Generates queries
- Summarizer: Formats output

### 2. State Management with LangGraph

**What**: LangGraph passes a `state` dictionary through a series of nodes

**Why**:
- Each node adds/modifies state
- State flows through the graph
- Easy to track what happened  at each step
- Built-in retry and error handling

**Example**:
```
State after resolve:  {"query": "...", "is_follow_up": True}
State after classify: {"query": "...", "is_follow_up": True, "intent": "ANALYTICAL"}
State after SQL:      {"query": "...", ..., "sql": "SELECT...", "sql_results": [...]}
State after summarize: {..., "summary": "The top customers are..."}
```

### 3. Singleton Pattern for Expensive Resources

**What**: Create object once, reuse everywhere

**Why**:
- Embedding model loads in 7 seconds
- Loading on every request = too slow
- Singleton loads once on startup

**Implementation**:
```python
class Manager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ExpensiveObject()  # Load once
        return cls._instance  # Reuse
```

### 4. Few-Shot Learning vs Training

**What**: Showing the LLM examples instead of fine-tuning

**Why**:
- No training data needed
- No GPU required
- Update examples instantly
- Free (uses existing model)

**Example**: Instead of training SQL model, we show it:
```
Example 1: "top customers" → SELECT ... ORDER BY revenue DESC LIMIT 10
Example 2: "monthly trend" → SELECT DATE_TRUNC('month', ...) ...

Now: "top regions" → Agent learns the pattern: SELECT ... ORDER BY ... LIMIT
```

### 5. Hybrid Search

**What**: Combining SQL (precise) + Vector (semantic)

**Why**:
- SQL: Fast, precise, structured
- Vector: Understands meaning, fuzzy matching
- Hybrid: Best of both worlds

**Example**:
```
Query: "High-value customers with delivery problems"

SQL finds: Customers with revenue > $100K
Vector finds: Documents mentioning "delivery", "shipping", "delay"
Hybrid merges: Customers meeting both criteria
```

---

## Next Steps for Learning

1. **Start Simple**: Understand `streamlit_app.py` → `supervisor.py` → one agent
2. **Trace a Request**: Set breakpoints, follow state through each node
3. **Modify an Agent**: Change prompt in SQLAgent, see how output changes
4. **Add a Feature**: Create new intent or add visualization type
5. **Read Logs**: Every action is logged - follow the trail

**Pro Tip**: Start by asking simple questions in Streamlit and watching the Details panel - you'll see intent, SQL, etc. Then correlate that with the code.

---

*This documentation is a living document. Update it as the codebase evolves!*

---

## 11. Advanced Implementation Details

### 11.1 Visualization Workflow (Deep Dive)

This section details the end-to-end flow of how a chart is requested, generated, and rendered, which is critical for understanding the visualization agent's role.

#### 1. Intent Detection
- **Component**: `VisualizationAgent._detect_viz_intent`
- **Logic**: The agent scans the user query for specific keywords defined in `VIZ_KEYWORDS` (e.g., "graph", "chart", "plot", "visualize", "show me a", "bar chart", "trend").
- **Example**: A query like "Show me a bar chart of top customers" triggers `wants_viz = True`.

#### 2. Data Retrieval Strategy
The agent intelligently sources data from two potential contexts:
- **Current Execution**: If the user asks a data-fetching question (e.g., "Sales by region in a bar chart"), the `sql_flow` executes first, populating `state["sql_results"]`. The VisualizationAgent uses this fresh data.
- **Context Cache (Follow-up)**: If the user says "Visualise that" (referring to a previous analytical answer), the agent retrieves `last_turn_metadata["sql_results"]` from the session state, enabling seamless follow-up visualizations without re-running SQL.

#### 3. Configuration Generation (LLM-Driven)
- **Component**: `VisualizationAgent._suggest_visualization`
- **Process**: The agent constructs a specific prompt for the LLM (Groq), providing:
    - User Query
    - Available Data Columns
    - A Data Sample (first 5 rows) to help identify data types.
- **Prompt Rules**:
    - Use `bar` for categorical comparisons.
    - Use `line` for time series/trends.
    - Use `pie` for parts-of-a-whole.
    - Explicitly select `x` and `y` columns that exist in the data.
- **Output**: A JSON configuration object, e.g.:
    ```json
    { "chart_type": "bar", "x": "sold_to_party_name", "y": "total_net_amount" }
    ```

#### 4. Frontend Rendering (Streamlit)
- **File**: `streamlit_app.py`
- **Logic**: The frontend receives the final state. If `should_visualize` is true:
    1.  It extracts the `visualization_config`.
    2.  Converts the raw result data into a Pandas DataFrame.
    3.  Calls the appropriate Streamlit widget based on `chart_type`:
        -   `st.bar_chart(df.set_index(x)[y])`
        -   `st.line_chart(df.set_index(x)[y])`
        -   `st.area_chart` (as a fallback for area/pie representations).
    4.  Handles errors gracefully (e.g., missing columns) with user-friendly warnings.

### 11.2 SQLAgent Internals

The SQLAgent goes beyond simple prompting by actively understanding the database:

1.  **Dynamic Schema Fetching**: Instead of hardcoding table definitions, it queries `information_schema.columns` at startup. This allows the agent to adapt to schema changes (e.g., new columns) without code modifications.
2.  **Smart Column Prioritization**: To optimize context window usage, it identifies "important" columns using keyword matching (e.g., "amount", "date", "customer") and prioritizes them in the prompt, ensuring the LLM focuses on relevant fields.
3.  **Validation Logic**:
    -   **Policy Check**: Regex validation forbids dangerous keywords (`DROP`, `DELETE`, `UPDATE`) to ensure read-only safety.
    -   **Dry-Run Validation**: Before returning the SQL, it executes `EXPLAIN [query]` against the database. This catches syntax errors efficiently without running expensive queries.

### 11.3 VectorVerifier Confidence Logic

The `VectorVerifierAgent` (`core/agents/vector_verifier_agent.py`) uses a heuristic algorithm to assign confidence:

-   **HIGH Confidence**:
    -   Average Similarity ≥ 0.75 AND Count ≥ 3 AND Variance < 0.05 (Strong, consistent matches).
    -   OR Average Similarity ≥ 0.85 (Exceptional individual matches).
-   **LOW Confidence**:
    -   Average Similarity < 0.50 (Poor matches).
    -   OR Count < 2 (Insufficient data).
    -   OR Variance > 0.15 (Results are too scattered).
-   **MEDIUM Confidence**: All other cases.

### 11.4 Hybrid Search Merging Strategy

The `HybridFlow` (`core/flows/hybrid_flow.py`) combines results using a weighted scoring system:

1.  **SQL Scoring**: Results are scored by Inverse Rank (`1 / (position + 1)`).
2.  **Vector Scoring**: Results are scored by Cosine Similarity (0-1).
3.  **Combination**: `Final Score = (SQL_Score * 0.6) + (Vector_Score * 0.4)`.
    -   *(Weights are configurable in `settings.py`)*.
4.  **Deduplication**: Results are merged by `sales_order` ID to prevent duplicates, with the highest score retained.
