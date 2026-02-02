# QbotzChatbot - Complete Project Documentation
## Part 5: APIs & User Interfaces

[← Back to Part 4: Business Logic](project-doc-4-business-logic.md) | [Back to Part 1: Overview](project-doc-1-overview-architecture.md)

---

## 📋 Table of Contents

1. [FastAPI Backend](#fastapi-backend)
2. [Streamlit UI](#streamlit-ui)
3. [API Endpoints](#api-endpoints)
4. [Request/Response Formats](#requestresponse-formats)
5. [Authentication & Security](#authentication--security)
6. [Deployment Guide](#deployment-guide)

---

## 🚀 FastAPI Backend

### Application Structure

**Location**: `api/main.py` (4,864 bytes)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

from core.graphs.supervisor import SupervisorGraph
from utility.observability.logger import get_logger

# Initialize FastAPI app
app = FastAPI(
    title="QbotzChatbot API",
    description="SAP Sales Analytics Chatbot API",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI at /docs
    redoc_url="/redoc"         # ReDoc at /redoc
)

# Logger
logger = get_logger("api")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # In production: specific origins only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Chatbot (Singleton Pattern)
chatbot_graph: Optional[SupervisorGraph] = None

@app.on_event("startup")
async def startup_event():
    """
    Application startup handler.
    Initializes the chatbot graph ONCE at startup.
    """
    global chatbot_graph
    logger.info("api_startup_begin")
    
    try:
        chatbot_graph = SupervisorGraph()
        logger.info("chatbot_initialized", success=True)
    except Exception as e:
        logger.error("chatbot_initialization_failed", error=str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler."""
    logger.info("api_shutdown")
    # Cleanup: close database connections, etc.
    from core.storage.sap_sync.db_queries import DatabaseConnection
    DatabaseConnection.close_all_connections()
```

---

## 📡 API Endpoints

### 1. Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers.
    
    Returns:
        {
            "status": "healthy",
            "version": "1.0.0",
            "chatbot_initialized": true
        }
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "chatbot_initialized": chatbot_graph is not None
    }
```

**Usage**:
```bash
curl http://localhost:8000/health
```

---

### 2. Main Chat Endpoint

```python
# Request Model
class ChatMessage(BaseModel):
    role: str              # "user" or "assistant"
    content: str           # Message text

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.0
    max_tokens: Optional[int] = None
    model: Optional[str] = "qbotz-chatbot-v1"

# Response Model
class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    
    Request:
        POST /v1/chat/completions
        {
            "messages": [
                {"role": "user", "content": "Top 5 customers by revenue"},
                {"role": "assistant", "content": "..."},
                {"role": "user", "content": "Show me their order counts"}
            ],
            "temperature": 0.0,
            "model": "qbotz-chatbot-v1"
        }
    
    Response:
        {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1704067200,
            "model": "qbotz-chatbot-v1",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Here are the order counts...",
                        "metadata": {
                            "intent": "ANALYTICAL",
                            "sql": "SELECT ...",
                            "result_count": 5
                        }
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150
            }
        }
    """
    try:
        # Validate chatbot initialized
        if chatbot_graph is None:
            raise HTTPException(status_code=503, detail="Chatbot not initialized")
        
        # Extract conversation
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages cannot be empty")
        
        # Get current user query (last message)
        current_message = request.messages[-1]
        if current_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")
        
        user_query = current_message.content
        
        # Build conversation history (previous turns)
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages[:-1]
        ]
        
        logger.info("chat_request_received",
                   query=user_query,
                   history_length=len(conversation_history))
        
        # Execute chatbot
        result = chatbot_graph.run(
            query=user_query,
            conversation_history=conversation_history
        )
        
        # Build response
        response = ChatCompletionResponse(
            id=f"chatcmpl-{generate_id()}",
            created=int(time.time()),
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("summary", "I couldn't process that request."),
                        "metadata": {
                            "intent": result.get("intent"),
                            "intent_confidence": result.get("intent_confidence"),
                            "sql": result.get("sql"),
                            "result_count": len(result.get("sql_results", [])),
                            "visualization": result.get("visualization_config"),
                            "error": result.get("error")
                        }
                    },
                    "finish_reason": "stop" if not result.get("error") else "error"
                }
            ],
            usage={
                "prompt_tokens": estimate_tokens(user_query),
                "completion_tokens": estimate_tokens(result.get("summary", "")),
                "total_tokens": 0  # Calculated later
            }
        )
        
        logger.info("chat_request_completed",
                   intent=result.get("intent"),
                   success=result.get("error") is None)
        
        return response
    
    except Exception as e:
        logger.error("chat_request_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def generate_id() -> str:
    """Generate unique chat completion ID."""
    import uuid
    return str(uuid.uuid4())[:12]

def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters)."""
    return len(text) // 4
```

---

### 3. SAP Sync Endpoint

```python
@app.post("/admin/sync-sap")
async def trigger_sap_sync(background_tasks: BackgroundTasks):
    """
    Manually trigger SAP data synchronization.
    
    Usage:
        POST /admin/sync-sap
        
    Response:
        {
            "status": "sync_started",
            "message": "SAP synchronization started in background"
        }
    
    Note: Requires admin authentication in production!
    """
    try:
        from utility.services.sap_sync_job import run_sap_sync
        
        # Run in background
        background_tasks.add_task(run_sap_sync)
        
        logger.info("sap_sync_triggered", source="api")
        
        return {
            "status": "sync_started",
            "message": "SAP synchronization started in background"
        }
    
    except Exception as e:
        logger.error("sap_sync_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 4. Metrics Endpoint

```python
@app.get("/admin/metrics")
async def get_metrics():
    """
    Get system metrics.
    
    Returns:
        {
            "database": {
                "total_orders": 10000,
                "total_embeddings": 10000,
                "last_sync": "2024-01-15T10:30:00Z"
            },
            "performance": {
                "avg_response_time_ms": 2500,
                "total_requests": 5000,
                "error_rate": 0.02
            }
        }
    """
    try:
        from core.storage.sap_sync.db_queries import DataAccess
        
        db = DataAccess()
        
        # Query metrics
        total_orders = db.execute_query("SELECT COUNT(*) as count FROM sales_orders")[0]["count"]
        total_embeddings = db.execute_query("SELECT COUNT(*) as count FROM sales_order_embeddings")[0]["count"]
        
        last_sync_result = db.execute_query(
            "SELECT MAX(updated_at) as last_sync FROM sales_orders"
        )
        last_sync = last_sync_result[0]["last_sync"] if last_sync_result else None
        
        return {
            "database": {
                "total_orders": total_orders,
                "total_embeddings": total_embeddings,
                "last_sync": last_sync.isoformat() if last_sync else None
            },
            "performance": {
                "avg_response_time_ms": 2500,  # TODO: Calculate from logs
                "total_requests": 5000,         # TODO: Track in metrics store
                "error_rate": 0.02              # TODO: Calculate from logs
            }
        }
    
    except Exception as e:
        logger.error("metrics_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🖥️ Streamlit UI

### Complete Streamlit Application

**Location**: `streamlit_app.py` (7,413 bytes)

```python
import streamlit as st
from typing import List, Dict
import time

from core.graphs.supervisor import SupervisorGraph
from core.storage.embedding.embedding_manager import EmbeddingModelManager
from utility.observability.logger import get_logger

# Page Configuration
st.set_page_config(
    page_title="QbotzChatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
    .metadata-expander {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

logger = get_logger("streamlit_app")

# Initialize Session State
if "chatbot" not in st.session_state:
    with st.spinner("🔄 Initializing chatbot..."):
        st.session_state.chatbot = SupervisorGraph()
        logger.info("streamlit_chatbot_initialized")

if "embedding_model" not in st.session_state:
    with st.spinner("🧠 Loading embedding model..."):
        st.session_state.embedding_model = EmbeddingModelManager.get_instance()
        logger.info("streamlit_embedding_loaded")

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "last_turn_metadata" not in st.session_state:
    st.session_state.last_turn_metadata = {}


# Sidebar
with st.sidebar:
    st.title("🤖 QbotzChatbot")
    st.markdown("### SAP Sales Analytics Assistant")
    
    st.divider()
    
    # Conversation Stats
    st.markdown("#### 📊 Conversation Stats")
    st.metric("Messages", len(st.session_state.conversation_history))
    
    if st.session_state.last_turn_metadata:
        st.metric("Last Intent", st.session_state.last_turn_metadata.get("intent", "N/A"))
        st.metric("Result Count", st.session_state.last_turn_metadata.get("result_count", 0))
    
    st.divider()
    
    # Clear Conversation
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.last_turn_metadata = {}
        st.rerun()
    
    st.divider()
    
    # Example Queries
    st.markdown("#### 💡 Example Queries")
    
    examples = [
        "Top 10 customers by revenue",
        "Sales trend over last 6 months",
        "Show me orders in EAST region",
        "Delivery quality issues",
        "High-value customers with delays"
    ]
    
    for example in examples:
        if st.button(example, key=f"example_{example}", use_container_width=True):
            st.session_state.example_query = example
            st.rerun()
    
    st.divider()
    
    # Settings
    st.markdown("#### ⚙️ Settings")
    show_metadata = st.checkbox("Show metadata", value=True)
    show_sql = st.checkbox("Show SQL queries", value=True)


# Main Chat Interface
st.title("💬 Chat with QbotzChatbot")

# Display Conversation History
for message in st.session_state.conversation_history:
    role = message["role"]
    content = message["content"]
    metadata = message.get("metadata", {})
    
    with st.chat_message(role):
        st.markdown(content)
        
        # Show metadata if enabled
        if show_metadata and role == "assistant" and metadata:
            with st.expander("🔍 Details", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Intent**: {metadata.get('intent', 'N/A')}")
                    st.markdown(f"**Confidence**: {metadata.get('intent_confidence', 'N/A')}")
                    st.markdown(f"**Result Count**: {metadata.get('result_count', 0)}")
                
                with col2:
                    if metadata.get('sql') and show_sql:
                        st.code(metadata['sql'], language='sql')
        
        # Show visualization if available
        if role == "assistant" and metadata.get("visualization_config"):
            viz_config = metadata["visualization_config"]
            if viz_config.get("chart_html"):
                st.components.v1.html(viz_config["chart_html"], height=500, scrolling=True)


# Chat Input
user_input = st.chat_input("Ask me about SAP sales data...")

# Handle example query from sidebar
if hasattr(st.session_state, 'example_query'):
    user_input = st.session_state.example_query
    delattr(st.session_state, 'example_query')

if user_input:
    # Add user message to UI
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Add to conversation history
    st.session_state.conversation_history.append({
        "role": "user",
        "content": user_input
    })
    
    # Show processing indicator
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            start_time = time.time()
            
            try:
                # Run chatbot
                result = st.session_state.chatbot.run(
                    query=user_input,
                    conversation_history=[
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in st.session_state.conversation_history[:-1]
                    ]
                )
                
                elapsed_time = time.time() - start_time
                
                # Extract response
                summary = result.get("summary", "I couldn't process that request.")
                error = result.get("error")
                
                if error:
                    st.error(f"❌ Error: {error}")
                    summary = f"I encountered an error: {error}"
                
                # Display response
                st.markdown(summary)
                
                # Prepare metadata
                metadata = {
                    "intent": result.get("intent"),
                    "intent_confidence": result.get("intent_confidence"),
                    "sql": result.get("sql"),
                    "result_count": len(result.get("sql_results", []) or result.get("vector_results", [])),
                    "visualization_config": result.get("visualization_config"),
                    "elapsed_time": f"{elapsed_time:.2f}s"
                }
                
                # Show metadata
                if show_metadata:
                    with st.expander("🔍 Details", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**Intent**: {metadata['intent']}")
                            st.markdown(f"**Confidence**: {metadata['intent_confidence']}")
                            st.markdown(f"**Result Count**: {metadata['result_count']}")
                            st.markdown(f"**Response Time**: {metadata['elapsed_time']}")
                        
                        with col2:
                            if metadata.get('sql') and show_sql:
                                st.code(metadata['sql'], language='sql')
                
                # Show visualization
                if metadata.get("visualization_config"):
                    viz_config = metadata["visualization_config"]
                    if viz_config.get("chart_html"):
                        st.components.v1.html(viz_config["chart_html"], height=500, scrolling=True)
                
                # Add to conversation history
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": summary,
                    "metadata": metadata
                })
                
                # Update last turn metadata (for follow-ups)
                st.session_state.last_turn_metadata = {
                    "intent": result.get("intent"),
                    "sql": result.get("sql"),
                    "sql_results": result.get("sql_results", [])[:10],
                    "result_count": len(result.get("sql_results", []) or [])
                }
                
                logger.info("streamlit_query_completed",
                          intent=metadata['intent'],
                          elapsed_time=elapsed_time)
            
            except Exception as e:
                logger.error("streamlit_query_failed", error=str(e))
                st.error(f"❌ An error occurred: {str(e)}")
                
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error: {str(e)}"
                })
```

### Streamlit Features

1. **Real-time Chat Interface**
   - Message history with scroll
   - User/Assistant message distinction
   - Typing indicators

2. **Metadata Display**
   - Intent classification
   - SQL queries
   - Result counts
   - Response times

3. **Interactive Visualizations**
   - Embedded Plotly charts
   - Full-screen support
   - Interactive tooltips

4. **Example Queries**
   - Sidebar with common queries
   - One-click to populate input

5. **Conversation Management**
   - Clear conversation button
   - Session state persistence
   - Conversation stats

---

## 📝 Request/Response Formats

### Chat Completion Request

```json
{
    "messages": [
        {
            "role": "user",
            "content": "Top 5 customers by revenue in EAST region"
        }
    ],
    "temperature": 0.0,
    "max_tokens": null,
    "model": "qbotz-chatbot-v1"
}
```

### Chat Completion Response

```json
{
    "id": "chatcmpl-a1b2c3d4",
    "object": "chat.completion",
    "created": 1704067200,
    "model": "qbotz-chatbot-v1",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "The top 5 customers in the EAST region are:\n1. ABC Corp - $500,000\n2. XYZ Inc - $450,000\n3. Acme Ltd - $400,000\n4. TechCo - $380,000\n5. GlobalSales - $350,000\n\nTotal revenue from these customers: $2,080,000",
                "metadata": {
                    "intent": "ANALYTICAL",
                    "intent_confidence": 0.95,
                    "sql": "SELECT sold_to_party_name, SUM(total_net_amount) as total_revenue FROM sales_orders WHERE sales_district = 'EAST' GROUP BY sold_to_party_name ORDER BY total_revenue DESC LIMIT 5;",
                    "result_count": 5,
                    "visualization": null,
                    "error": null
                }
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 20,
        "completion_tokens": 80,
        "total_tokens": 100
    }
}
```

### Error Response

```json
{
    "detail": "SQL generation failed: Invalid column 'customer_name'",
    "status_code": 500
}
```

---

## 🔒 Authentication & Security

### API Key Authentication (Production)

```python
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validate API key."""
    if api_key_header == settings.API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

# Protected endpoint
@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: str = Depends(get_api_key)  # ← Requires valid API key
):
    # ... implementation
```

### SQL Injection Prevention

Already implemented in `SQLAgent`:

1. **Column Validation**: Only allow columns that exist in schema
2. **Policy Checks**: Block DROP, DELETE, TRUNCATE, etc.
3. **Dry-run Validation**: Use EXPLAIN to validate before execution
4. **Parameterized Queries**: Use prepared statements where possible

### Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/v1/chat/completions")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def chat_completions(request: Request, ...):
    # ... implementation
```

---

## 🚢 Deployment Guide

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env with your credentials

# 3. Initialize database
python scripts/init_database.py

# 4. Run SAP sync (initial data load)
python utility/services/sap_sync_job.py

# 5. Start FastAPI
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start Streamlit (in another terminal)
streamlit run streamlit_app.py
```

### Docker Deployment

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download embedding model (cache in image)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"

# Copy application
COPY . .

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command (both FastAPI and Streamlit)
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 & streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  # PostgreSQL with pgvector
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: qbotz_db
      POSTGRES_USER: qbotz_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5466:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U qbotz_user"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # QbotzChatbot Application
  qbotz-app:
    build: .
    ports:
      - "8000:8000"  # FastAPI
      - "8501:8501"  # Streamlit
    environment:
      DATABASE_URL: postgresql://qbotz_user:${DB_PASSWORD}@postgres:5432/qbotz_db
      GROQ_API_KEY: ${GROQ_API_KEY}
      SAP_BASE_URL: ${SAP_BASE_URL}
      SAP_USERNAME: ${SAP_USERNAME}
      SAP_PASSWORD: ${SAP_PASSWORD}
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  postgres_data:
```

**Deployment Commands**:

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f qbotz-app

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Production Considerations

1. **Environment Variables**
   - Never commit `.env` to version control
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault)

2. **Database**
   - Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
   - Enable connection pooling (already implemented)
   - Regular backups

3. **Logging**
   - Centralized logging (ELK stack, CloudWatch)
   - Structured JSON logs
   - Log retention policies

4. **Monitoring**
   - Application metrics (Prometheus, Grafana)
   - Health checks and alerts
   - Response time tracking

5. **Scaling**
   - Horizontal scaling (multiple API instances behind load balancer)
   - Stateless design (already implemented)
   - Caching layer (Redis for frequent queries)

6. **Security**
   - HTTPS/TLS encryption
   - API key authentication
   - Rate limiting
   - Regular security audits

---

## 📊 API Usage Examples

### cURL Example

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "messages": [
      {"role": "user", "content": "Top 5 customers by revenue"}
    ]
  }'
```

### Python `requests` Example

```python
import requests

url = "http://localhost:8000/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key"
}

payload = {
    "messages": [
        {"role": "user", "content": "Show me sales trend over last 6 months"}
    ]
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### JavaScript `fetch` Example

```javascript
const response = await fetch('http://localhost:8000/v1/chat/completions', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key'
    },
    body: JSON.stringify({
        messages: [
            {role: 'user', content: 'Top customers in EAST region'}
        ]
    })
});

const data = await response.json();
console.log(data);
```

---

## 🎓 Summary: APIs & Interfaces

✅ **FastAPI Backend**: RESTful API with OpenAI-compatible endpoints  
✅ **Streamlit UI**: Interactive chat interface with visualizations  
✅ **Singleton Pattern**: Efficient resource management (chatbot, embedding model)  
✅ **CORS Support**: Cross-origin requests enabled  
✅ **Health Checks**: Load balancer compatibility  
✅ **Docker Ready**: Complete containerization support  
✅ **Production Features**: Authentication, rate limiting, monitoring  

---

## 🏁 Complete Documentation Series

This concludes the comprehensive QbotzChatbot documentation series:

1. **[Part 1: Overview & Architecture](project-doc-1-overview-architecture.md)**
   - System overview, tech stack, architecture

2. **[Part 2: Agents & Flows](project-doc-2-agents-flows.md)**
   - 8 specialized agents, 4 execution flows

3. **[Part 3: Data Layer & Storage](project-doc-3-data-storage.md)**
   - PostgreSQL, pgvector, embeddings, SAP sync

4. **[Part 4: Business Logic & Workflows](project-doc-4-business-logic.md)**
   - Request workflows, intent routing, error handling

5. **[Part 5: APIs & Interfaces](project-doc-5-apis-interfaces.md)** ← **You are here**
   - FastAPI, Streamlit, deployment

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-02  
**Total Documentation**: 5 comprehensive parts covering the entire codebase

[← Back to Part 4: Business Logic](project-doc-4-business-logic.md) | [Back to Part 1: Overview](project-doc-1-overview-architecture.md)
