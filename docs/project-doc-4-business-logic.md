# QbotzChatbot - Complete Project Documentation
## Part 4: Business Logic & Workflows

[← Back to Part 3: Data Storage](project-doc-3-data-storage.md) | [Part 5: APIs & Interfaces →](project-doc-5-apis-interfaces.md)

---

## 📋 Table of Contents

1. [Complete Request Workflow](#complete-request-workflow)
2. [Intent-Based Routing Logic](#intent-based-routing-logic)
3. [Conversation Continuity](#conversation-continuity)
4. [Visualization Pipeline](#visualization-pipeline)
5. [State Management](#state-management)
6. [Error Handling & Fallbacks](#error-handling--fallbacks)

---

## 🔄 Complete Request Workflow

### End-to-End Flow Diagram

```
USER: "Who are the top 5 customers in the EAST region?"

┌────────────────────────────────────────────────────────────┐
│ STEP 1: ENTRY POINT (Streamlit or FastAPI)                │
│                                                             │
│ Streamlit:                                                  │
│   user_input = st.chat_input()                             │
│   supervisor.run(user_input, conversation_history)         │
│                                                             │
│ Fast API:                                                    │
│   POST /v1/chat/completions                                │
│   body: {messages: [{role, content}, ...]}                │
│   chatbot_graph.invoke(initial_state)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 2: INITIALIZE STATE                                   │
│                                                             │
│ ChatbotState = {                                            │
│   "query": "Who are the top 5 customers in EAST region?",  │
│   "conversation_history": [],                              │
│   "intent": None,                    # ← To be determined  │
│   "sql": None,                       # ← To be generated   │
│   "sql_results": None,               # ← To be populated   │
│   "vector_results": None,                                  │
│   "hybrid_results": None,                                  │
│   "summary": None,                   # ← Final output      │
│   "error": None                                            │
│ }                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 3: CONVERSATION RESOLUTION                            │
│ Agent: ConversationResolverAgent                            │
│                                                             │
│ Input: query + conversation_history                        │
│                                                             │
│ Logic:                                                      │
│ • Check for follow-up indicators ("those", "them", "also") │
│ • If first turn → is_follow_up = False                     │
│ • If follow-up → expand vague references                   │
│                                                             │
│ Output:                                                     │
│ {                                                           │
│   "is_follow_up": False,                                   │
│   "expanded_query": "Who are the top 5 customers in EAST   │
│                      region?",  # (unchanged)              │
│   "reasoning": "First question, no context needed"         │
│ }                                                           │
│                                                             │
│ State Update:                                               │
│   state["is_follow_up"] = False                            │
│   state["expanded_query"] = expanded_query                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 4: INTENT CLASSIFICATION                              │
│ Agent: IntentClassifierAgent                                │
│                                                             │
│ Input: "Who are the top 5 customers in EAST region?"       │
│                                                             │
│ Analysis:                                                   │
│ • Contains aggregation? YES ("top 5")                      │
│ • Contains filter?  YES ("in EAST region")                 │
│ • Needs SQL precision? YES                                 │
│ • Needs semantic search? NO                                │
│                                                             │
│ LLM Decision:                                               │
│ {                                                           │
│   "intent": "ANALYTICAL",                                  │
│   "confidence": 0.95,                                      │
│   "reasoning": "Requires precise SQL aggregation and       │
│                 filtering - top N ranking"                 │
│ }                                                           │
│                                                             │
│ State Update:                                               │
│   state["intent"] = "ANALYTICAL"                           │
│   state["intent_confidence"] = 0.95                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 5: ROUTING DECISION                                   │
│ Function: SupervisorGraph._route()                          │
│                                                             │
│ if intent == "ANALYTICAL":                                  │
│     return "sql_flow"                                       │
│ elif intent == "SEMANTIC":                                  │
│     return "vector_flow"                                    │
│ elif intent == "HYBRID":                                    │
│     return "hybrid_flow"                                    │
│ else: # CHITCHAT                                            │
│     return "chitchat"                                       │
│                                                             │
│ Routed to: "sql_flow" ✓                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 6: SQL FLOW EXECUTION                                 │
│ Flow: SQLExecutionFlow                                      │
│                                                             │
│ 6.1: SQLAgent - Generate SQL                               │
│ ─────────────────────────────────────────                  │
│                                                             │
│ Process:                                                    │
│ 1. Load dynamic schema from PostgreSQL                     │
│ 2. Categorize columns (Revenue, Customer, Geography)       │
│ 3. Retrieve few-shot examples (semantic similarity)        │
│ 4. Build LLM prompt with schema + examples                 │
│ 5. Generate SQL                                            │
│ 6. Validate columns exist                                  │
│ 7. Auto-correct if needed                                  │
│ 8. Policy check (no DROP/DELETE)                           │
│ 9. Dry-run with EXPLAIN                                    │
│                                                             │
│ Generated SQL:                                              │
│ ```sql                                                      │
│ SELECT                                                      │
│     sold_to_party_name,                                    │
│     SUM(total_net_amount) as total_revenue                 │
│ FROM sales_orders                                           │
│ WHERE sales_district = 'EAST'                              │
│ GROUP BY sold_to_party_name                                │
│ ORDER BY total_revenue DESC                                │
│ LIMIT 5;                                                    │
│ ```                                                         │
│                                                             │
│ 6.2: Execute SQL                                            │
│ ─────────────────────────────────────────────              │
│                                                             │
│ Tool: sql_executor.execute_sql(sql)                        │
│                                                             │
│ Results:                                                    │
│ [                                                           │
│   {"sold_to_party_name": "ABC Corp", "total_revenue": 500000},│
│   {"sold_to_party_name": "XYZ Inc", "total_revenue": 450000}, │
│   {"sold_to_party_name": "Acme Ltd", "total_revenue": 400000},│
│   {"sold_to_party_name": "TechCo", "total_revenue": 380000},  │
│   {"sold_to_party_name": "GlobalSales", "total_revenue": 350000}│
│ ]                                                           │
│                                                             │
│ State Update:                                               │
│   state["sql"] = "SELECT sold_to_party_name..."           │
│   state["sql_results"] = [...]                            │
│   state["last_sql_context"] = {                            │
│       "sql": "...",                                         │
│       "result_count": 5,                                   │
│       "columns": ["sold_to_party_name", "total_revenue"]  │
│   }                                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 7: VISUALIZATION DETECTION                            │
│ Agent: VisualizationAgent                                   │
│                                                             │
│ Input: query + sql_results                                  │
│                                                             │
│ Detection:                                                  │
│ • Query contains viz keywords? NO                          │
│   (no "chart", "graph", "plot", "visualize")              │
│ • Is follow-up viz request? NO                             │
│ • Should visualize? NO                                     │
│                                                             │
│ Output:                                                     │
│ {                                                           │
│   "should_visualize": False,                               │
│   "viz_config": None                                       │
│ }                                                           │
│                                                             │
│ State Update:                                               │
│   state["should_visualize"] = False                        │
│   state["visualization_config"] = None                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 8: SUMMARIZATION                                      │
│ Agent: SummarizerAgent                                      │
│                                                             │
│ Input:                                                      │
│ • query: "Who are the top 5 customers in EAST region?"    │
│ • sql_results: [{...}, {...}, ...]                        │
│                                                             │
│ LLM Prompt:                                                 │
│ "Convert this data into natural language answer.           │
│  Format numbers with commas and currency symbols.          │
│  Be concise and professional."                             │
│                                                             │
│ Generated Summary:                                          │
│ "The top 5 customers in the EAST region are:               │
│  1. ABC Corp - $500,000                                    │
│  2. XYZ Inc - $450,000                                     │
│  3. Acme Ltd - $400,000                                    │
│  4. TechCo - $380,000                                      │
│  5. GlobalSales - $350,000                                 │
│                                                             │
│  Total revenue from these customers: $2,080,000"           │
│                                                             │
│ State Update:                                               │
│   state["summary"] = "The top 5 customers..."             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ STEP 9: RETURN FINAL STATE                                │
│                                                             │
│ Final ChatbotState:                                         │
│ {                                                           │
│   "query": "Who are the top 5 customers in EAST region?",  │
│   "conversation_history": [],                              │
│   "intent": "ANALYTICAL",                                  │
│   "intent_confidence": 0.95,                               │
│   "is_follow_up": False,                                   │
│   "sql": "SELECT sold_to_party_name...",                   │
│   "sql_results": [{...}, {...}, ...],                      │
│   "last_sql_context": {...},                              │
│   "vector_results": None,                                  │
│   "hybrid_results": None,                                  │
│   "should_visualize": False,                               │
│   "visualization_config": None,                            │
│   "summary": "The top 5 customers in the EAST region...",  │
│   "error": None                                            │
│ }                                                           │
│                                                             │
│ Returned to: Streamlit UI or FastAPI response              │
└─────────────────────────────────────────────────────────────┘

USER SEES:
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Assistant                                                │
│                                                             │
│ The top 5 customers in the EAST region are:                 │
│ 1. ABC Corp - $500,000                                      │
│ 2. XYZ Inc - $450,000                                       │
│ 3. Acme Ltd - $400,000                                      │
│ 4. TechCo - $380,000                                        │
│ 5. GlobalSales - $350,000                                   │
│                                                             │
│ Total revenue from these customers: $2,080,000              │
│                                                             │
│ ▼ Details                                                   │
│   Intent: ANALYTICAL                                        │
│   SQL: SELECT sold_to_party_name...                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Intent-Based Routing Logic

### Intent Decision Tree

```
                      ┌─────────────────┐
                      │ Classify Query  │
                      └────────┬────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  Is greeting/                 │                Contains
  help/thanks?                 │                data query?
        │                      │                      │
       YES                    NO                     YES
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐      ┌────────────┐        ┌────────────────┐
│  CHITCHAT    │      │ CHITCHAT   │        │ Analyze query  │
│              │      │            │        │ characteristics│
│ Examples:    │      │ Default if │        └───────┬────────┘
│ • "Hello"    │      │ unclear    │                │
│ • "Thanks"   │      └────────────┘      ┌─────────┴─────────┐
│ • "What can  │                          │                   │
│   you do?"   │                   Needs precise        Needs semantic
└──────────────┘                   aggregation?         understanding?
                                          │                   │
                                         YES                 YES
                                          │                   │
                              ┌───────────┴──────┐            │
                              │                  │            │
                        Only SQL          Both SQL &      Only semantic
                         needed?          semantic?         needed?
                              │                  │            │
                             YES                YES          YES
                              │                  │            │
                              ▼                  ▼            ▼
                      ┌──────────────┐  ┌────────────┐  ┌──────────┐
                      │ ANALYTICAL   │  │  HYBRID    │  │ SEMANTIC │
                      │              │  │            │  │          │
                      │ Examples:    │  │ Examples:  │  │Examples: │
                      │ • Top 10     │  │ • High-val │  │• Trends  │
                      │   customers  │  │   customers│  │• Patterns│
                      │ • Revenue    │  │   with     │  │• Quality │
                      │   total      │  │   delivery │  │  issues  │
                      │ • Count by   │  │   issues   │  │          │
                      │   region     │  │            │  │          │
                      └──────┬───────┘  └─────┬──────┘  └────┬─────┘
                             │                │               │
                             ▼                ▼               ▼
                      ┌──────────────┐  ┌────────────┐  ┌──────────┐
                      │  SQL Flow    │  │ Hybrid Flow│  │Vector Flw│
                      └──────────────┘  └────────────┘  └──────────┘
```

### Intent Classification Prompt

```python
INTENT_CLASSIFICATION_PROMPT = """
You are an intent classifier for a sales analytics chatbot.

USER QUERY: "{query}"

CLASSIFY AS ONE OF:
1. ANALYTICAL - Requires precise SQL (aggregations, counts, rankings, filters)
2. SEMANTIC - Requires conceptual understanding (trends, quality, patterns)
3. HYBRID - Requires BOTH SQL precision AND semantic understanding
4. CHITCHAT - Not a data query (greetings, thanks, help requests)

DECISION CRITERIA:

ANALYTICAL if:
✓ Has numeric requirements (top N, count, sum, average)
✓ Has specific filters (region, date range, customer)
✓ Needs exact calculations
✓ Examples: "top 10", "total revenue", "count by region"

SEMANTIC if:
✓ Asks about patterns, trends, quality
✓ Uses subjective terms (good, bad, unusual, problematic)
✓ Needs contextual understanding
✓ Examples: "delivery issues", "quality trends", "customer satisfaction"

HYBRID if:
✓ Combines analytical constraints with semantic concepts
✓ Examples: "high-value customers with delivery problems"
✓ "Top products by revenue that have quality issues"

CHITCHAT if:
✓ Greeting, thanks, small talk
✓ Questions about system capabilities
✓ Examples: "hello", "what can you do?", "thanks"

Respond in JSON:
{{
    "intent": "ANALYTICAL|SEMANTIC|HYBRID|CHITCHAT",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""
```

### Classification Examples

```python
# Clear ANALYTICAL
classify("Top 10 customers by revenue")
→ {"intent": "ANALYTICAL", "confidence": 0.95}

classify("Total sales in EAST region for Jan 2024")
→ {"intent": "ANALYTICAL", "confidence": 0.98}

# Clear SEMANTIC
classify("Show me delivery quality trends")
→ {"intent": "SEMANTIC", "confidence": 0.92}

classify("Which customers have complained about quality?")
→ {"intent": "SEMANTIC", "confidence": 0.88}

# HYBRID
classify("Top 5 products by revenue with the most delivery issues")
→ {"intent": "HYBRID", "confidence": 0.90}

classify("High-value customers in EAST region who had billing problems")
→ {"intent": "HYBRID", "confidence": 0.87}

# CHITCHAT
classify("Hello")
→ {"intent": "CHITCHAT", "confidence": 0.99}

classify("What kind of questions can you answer?")
→ {"intent": "CHITCHAT", "confidence": 0.96}
```

---

## 💬 Conversation Continuity

### Follow-Up Detection Logic

```python
def detect_follow_up(query: str, conversation_history: List[Dict]) -> bool:
    """
    Detects if current query is a follow-up.
    
    Indicators:
    1. Pronouns (it, that, those, them)
    2. References (same, similar, previous)
    3. Comparatives (more, less, different)
    4. Implicit continuity (also, too, as well)
    """
    
    # No history = can't be follow-up
    if not conversation_history:
        return False
    
    # Check for indicators
    query_lower = query.lower()
    
    pronouns = ["it", "that", "this", "those", "these", "they", "them"]
    references = ["same", "similar", "above", "previous", "last"]
    comparatives = ["more", "less", "different", "other", "another"]
    continuity = ["also", "too", "as well", "additionally"]
    
    all_indicators = pronouns + references + comparatives + continuity
    
    # Count indicator words
    indicator_count = sum(1 for word in all_indicators if word in query_lower)
    
    # Strong signal: multiple indicators
    if indicator_count >= 2:
        return True
    
    # Weak signal: use LLM for final decision
    if indicator_count == 1:
        return llm_confirm_follow_up(query, conversation_history)
    
    return False
```

### Context Expansion Examples

#### Example 1: Pronoun Resolution

```
Conversation:
Turn 1:
  User: "Who are the top customers in EAST region?"
  Bot: "The top customers are ABC Corp ($500K) and XYZ Inc ($450K)."
  
Turn 2:
  User: "Show me their order counts"
        ↓
  Detected: "their" → pronoun reference
        ↓
  Expanded: "Show me order counts for ABC Corp and XYZ Inc"
        ↓
  Context Added:
    - Entities: ["ABC Corp", "XYZ Inc"]
    - Region: "EAST"
    - Previous intent: ANALYTICAL
```

#### Example 2: Implicit Reference

```
Conversation:
Turn 1:
  User: "Total revenue by region"
  Bot: "EAST: $2M, WEST: $1.5M, NORTH: $1.2M, SOUTH: $800K"
  
Turn 2:
  User: "Break it down by month"
        ↓
  Detected: "it" → refers to previous context
        ↓
  Expanded: "Show total revenue by region broken down by month"
        ↓
  Context Preserved:
    - Metrics: ["total_revenue"]
    - Grouping: ["region", "month"]  ← Added
    - Previous SQL available for reference
```

#### Example 3: Visualization Follow-Up

```
Conversation:
Turn 1:
  User: "Top 10 products by revenue"
  Bot: "1. Product A: $50K, 2. Product B: $45K, ..."
  Metadata: {
    "sql": "SELECT material_description, SUM(...)...",
    "sql_results": [{...}, {...}, ...]  ← CACHED
  }
  
Turn 2:
  User: "Show me that as a bar chart"
        ↓
  Detected: "that" → refers to previous results
        ↓
  Resolved: Use cached sql_results from last_turn_metadata
        ↓
  No new SQL execution needed!
        ↓
  Visualization Agent:
    - data = last_turn_metadata["sql_results"]
    - chart_type = "bar"
    - Generate Plotly chart
```

### Conversation State Tracking

```python
class ConversationTracker:
    """
    Tracks conversation state across multiple turns.
    Stored in session (Streamlit) or sent by client (FastAPI).
    """
    
    def __init__(self):
        self.history: List[ConversationTurn] = []
        self.last_turn_metadata: Dict = {}
    
    def add_turn(self, role: str, content: str, metadata: Dict = None):
        """Add a conversation turn."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        if role == "assistant" and metadata:
            # Store metadata for follow-up questions
            self.last_turn_metadata = {
                "user_query": self.history[-2]["content"] if len(self.history) >= 2 else "",
                "intent": metadata.get("intent"),
                "sql": metadata.get("sql"),
                "sql_results": metadata.get("sql_results", [])[:10],  # Store last 10 rows
                "entities": metadata.get("entities", {}),
                "filters": self._extract_filters(metadata),
                "had_results": bool(metadata.get("sql_results") or metadata.get("vector_results"))
            }
    
    def get_context_for_resolution(self) -> Dict:
        """Get relevant context for ConversationResolverAgent."""
        return {
            "conversation_history": self.history[-6:],  # Last 3 turns (user + bot)
            "last_turn": self.last_turn_metadata
        }
    
    def _extract_filters(self, metadata: Dict) -> Dict:
        """Extract filters from SQL for context tracking."""
        sql = metadata.get("sql", "")
        filters = {}
        
        # Simple regex-based extraction (could be improved)
        if "sales_district" in sql:
            match = re.search(r"sales_district\s*=\s*'([^']+)'", sql)
            if match:
                filters["region"] = match.group(1)
        
        if "sales_order_date" in sql:
            # Extract date range if present
            pass
        
        return filters
```

---

## 📊 Visualization Pipeline

### Complete Visualization Workflow

```
┌────────────────────────────────────────────────────────────┐
│ SCENARIO 1: Simultaneous Request                          │
│ "Show me sales trend over time as a line chart"           │
└──────────────────────┬─────────────────────────────────────┘
                       │
                ┌──────▼──────┐
                │ Intent      │
                │Classification│
                │             │
                │ANALYTICAL   │
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │ SQL Flow    │
                │             │
                │ Generates:  │
                │ sql_results │
                └──────┬──────┘
                       │
                ┌──────▼─────────────────────────────────┐
                │ VisualizationAgent                     │
                │                                        │
                │ 1. Detect Intent                       │
                │    ✓ "as a line chart" → explicit     │
                │    ✓ "trend over time" → implicit     │
                │                                        │
                │ 2. Extract User Preference             │
                │    chart_type = "line"                 │
                │                                        │
                │ 3. Validate Data Structure             │
                │    ✓ Has date column                  │
                │    ✓ Has numeric column               │
                │                                        │
                │ 4. Suggest Chart Config (LLM)          │
                │    x = "month"                         │
                │    y = "revenue"                       │
                │    chart_type = "line"                 │
                │                                        │
                │ 5. Generate Chart                      │
                │    ChartGeneratorTool.generate(...)    │
                └──────┬─────────────────────────────────┘
                       │
                ┌──────▼──────────────────────────────┐
                │ Chart Artifacts                    │
                │                                     │
                │ • chart_html (Plotly interactive)  │
                │ • chart_base64 (PNG static)        │
                │ • chart_json (Plotly spec)         │
                └─────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ SCENARIO 2: Follow-Up Visualization                       │
│ Turn 1: "Top 10 products by revenue"                      │
│ Turn 2: "Visualize that"                                  │
└──────────────────────┬─────────────────────────────────────┘
                       │
                ┌──────▼──────────────────────────┐
                │ Turn 1 Response                │
                │                                 │
                │ state["sql_results"] = [...]   │
                │                                 │
                │ last_turn_metadata = {          │
                │   "sql_results": [...],  ← CACHED│
                │   "user_query": "Top 10..."    │
                │ }                                │
                └──────┬──────────────────────────┘
                       │
                ┌──────▼──────────────────────────┐
                │ Turn 2: "Visualize that"       │
                │                                 │
                │ ConversationResolver:           │
                │   is_follow_up = True           │
                │                                 │
                │ IntentClassifier:               │
                │   intent = ?                    │
                │   (Could be ANALYTICAL or       │
                │    special VISUALIZATION)       │
                └──────┬──────────────────────────┘
                       │
                ┌──────▼─────────────────────────────┐
                │ VisualizationAgent                 │
                │                                     │
                │ 1. Detect "visualize" keyword      │
                │    ✓ Visualization intent          │
                │                                     │
                │ 2. Check for data source            │
                │    ✓ is_follow_up = True           │
                │    ✓ last_turn_metadata.sql_results│
                │                                     │
                │ 3. Use CACHED results (no SQL!)    │
                │    data = last_turn_metadata[...]  │
                │                                     │
                │ 4. Suggest chart type (LLM)         │
                │    "Top 10 products" → bar chart   │
                │                                     │
                │ 5. Generate chart                   │
                └─────────────────────────────────────┘
```

### Chart Type Selection Logic

```python
def suggest_chart_type(query: str, data: List[Dict]) -> str:
    """
    LLM-based chart type suggestion.
    
    Considers:
    1. User's explicit preference ("bar chart", "line graph")
    2. Data structure (time series, categorical, numeric)
    3. Query semantics ("trend" → line, "distribution" → pie)
    """
    
    # Check explicit preference first
    explicit_type = extract_chart_preference(query)
    if explicit_type:
        return explicit_type
    
    # Analyze data structure
    first_row = data[0] if data else {}
    columns = list(first_row.keys())
    
    has_date = any('date' in col.lower() for col in columns)
    has_time = any('time' in col.lower() or 'month' in col.lower() for col in columns)
    
    # Rule-based heuristics
    if has_date or has_time or 'trend' in query.lower():
        return 'line'
    
    if 'distribution' in query.lower() or 'share' in query.lower():
        return 'pie'
    
    if 'over time' in query.lower():
        return 'area'
    
    # Default: bar chart (safest, most versatile)
    return 'bar'
```

### Chart Configuration Structure

```python
VisualizationConfig = {
    "chart_type": "bar|line|pie|area|none",
    
    # Data mapping
    "x": "column_name",          # X-axis (categorical or date)
    "y": "column_name",          # Y-axis (numeric)
    "data": [...],               # Raw data rows
    
    # Rendered outputs
    "chart_html": str,           # Interactive Plotly HTML (for Streamlit, web)
    "chart_base64": str,         # Static PNG as base64 (for API, mobile)
    "chart_json": dict,          # Plotly figure spec (for programmatic use)
    
    # Metadata
    "theme": "plotly_dark",      # Visual theme
    "error": None                # Error message if generation failed
}
```

---

## 📦 State Management

### ChatbotState Structure (Complete)

```python
from typing import TypedDict, Optional, List, Dict, Any, Literal

class ChatbotState(TypedDict):
    """
    Complete state object that flows through all LangGraph nodes.
    """
    
    # ===== User Input =====
    query: str                                    # Current user question
    
    # ===== Intent Classification =====
    intent: Optional[Literal["ANALYTICAL", "SEMANTIC", "HYBRID", "CHITCHAT"]]
    intent_confidence: Optional[float]            # 0-1 confidence score
    is_follow_up: Optional[bool]                  # True if references history
    
    # ===== SQL Path =====
    sql: Optional[str]                            # Generated SQL query
    sql_results: Optional[List[Dict[str, Any]]]   # Query results
    last_sql_context: Optional[Dict]              # Metadata about last SQL execution
    
    # ===== Vector Path =====
    expanded_query: Optional[str]                 # Resolved query with context
    vector_results: Optional[List[Dict]]          # Vector search results
    vector_confidence: Optional[Literal["HIGH", "MEDIUM", "LOW"]]
    
    # ===== Hybrid Path =====
    hybrid_results: Optional[List[Dict]]          # Merged SQL + Vector results
    result_sources: Optional[Dict]                # Tracking which source each result came from
    
    # ===== Conversation Memory =====
    conversation_history: List[Dict]              # Previous turns
    entities: Optional[Dict]                      # Extracted entities (future use)
    
    # ===== Visualization =====
    should_visualize: Optional[bool]              # True if chart needed
    visualization_config: Optional[Dict]          # Chart configuration
    
    # ===== Output =====
    summary: Optional[str]                        # Final natural language response
    
    # ===== Error Handling =====
    error: Optional[str]                          # Error message if any step failed
```

### State Transitions

```python
# Example state evolution through pipeline:

# Initial State
{
    "query": "Top 5 customers in EAST",
    "intent": None,
    "sql": None,
    "summary": None,
    # ... all others None/empty
}

# After Conversation Resolution
{
    "query": "Top 5 customers in EAST",
    "is_follow_up": False,             # ← Added
    "expanded_query": "...",            # ← Added
    # ... rest unchanged
}

# After Intent Classification
{
    # ...
    "intent": "ANALYTICAL",             # ← Set
    "intent_confidence": 0.95,          # ← Set
    # ...
}

# After SQL Flow
{
    # ...
    "sql": "SELECT ...",                # ← Generated
    "sql_results": [{...}, ...],        # ← Populated
    "last_sql_context": {...},          # ← Metadata
    # ...
}

# Final State
{
    # ... all previous fields set
    " summary": "The top 5 customers..."  # ← Final output
}
```

---

## ⚠️ Error Handling & Fallbacks

### Error Handling Strategy

```
┌────────────────────────────────────────┐
│ Error Occurs in Any Node              │
└──────────────┬─────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
   Recoverable    Fatal
        │             │
        ▼             ▼
┌──────────────┐  ┌────────────────┐
│ Retry Logic  │  │ Set state[     │
│              │  │  "error"]      │
│ Examples:    │  │                │
│ • SQL regen  │  │ Short-circuit  │
│ • Column fix │  │ remaining nodes│
│ • Auto-corrtn│  │                │
└──────┬───────┘  └────────┬───────┘
       │                   │
       ▼                   ▼
┌──────────────┐  ┌────────────────┐
│ Success?     │  │ Fallback       │
│              │  │ Response       │
│ YES → Proceed│  │                │
│ NO → Fallback│  │ "I encountered │
└──────────────┘  │ an error..."   │
                  └────────────────┘
```

### Specific Error Handlers

#### 1. SQL Generation Failures

```python
try:
    sql = sql_agent.run(query)
except ColumnValidationError as e:
    # Auto-correction attempt
    if settings.SQL_AUTO_CORRECT_COLUMNS:
        corrected_sql = auto_correct_sql(sql, e.invalid_columns)
        return corrected_sql
    else:
        # Regenerate with error feedback
        return regenerate_with_feedback(query, sql, e.invalid_columns)

except PolicyViolationError as e:
    # Never retry - security violation
    state["error"] = f"SQL policy violation: {e}"
    return state

except SQLSyntaxError as e:
    # Regenerate attempt
    if attempt < MAX_ATTEMPTS:
        return regenerate_with_feedback(query, sql, str(e))
    else:
        state["error"] = "Failed to generate valid SQL after max attempts"
        return state
```

#### 2. Database Connection Errors

```python
try:
    results = execute_sql(sql)
except psycopg2.OperationalError as e:
    # Connection pool exhausted
    logger.error("db_connection_failed", error=str(e))
    state["error"] = "Database temporarily unavailable. Please try again."
    return state

except psycopg2.ProgrammingError as e:
    # SQL error (shouldn't happen after validation, but just in case)
    logger.error("sql_execution_failed", sql=sql, error=str(e))
    state["error"] = "Query execution failed. Please rephrase your question."
    return state
```

#### 3. LLM API Failures

```python
try:
    response = groq_client.chat.completions.create(...)
except groq.RateLimitError:
    # Rate limit hit
    logger.warning("rate_limit_exceeded")
    time.sleep(2)  # Brief retry
    response = groq_client.chat.completions.create(...)  # Retry once

except groq.APIError as e:
    # API down
    logger.error("llm_api_failed", error=str(e))
    state["error"] = "AI service temporarily unavailable."
    return state
```

#### 4. Embedding Model Errors

```python
try:
    embedding = embedding_model.encode_single(query)
except Exception as e:
    # Model not loaded or encoding failed
    logger.error("embedding_failed", error=str(e))
    
    # Fallback: switch to SQL-only mode
    state["intent"] = "ANALYTICAL"  # Force SQL flow
    return state
```

### Graceful Degradation

```python
# If visualization fails, still return text summary
if viz_generation_error:
    state["should_visualize"] = False
    state["visualization_config"] = {
        "error": "Chart generation failed",
        "fallback": "text_summary_available"
    }
    # Proceeding to summarization (text response still works)

# If vector search fails in HYBRID mode, fall back to SQL-only
if vector_search_error and state["intent"] == "HYBRID":
    logger.warning("hybrid_degraded_to_sql")
    state["hybrid_results"] = state["sql_results"]  # Use SQL results only
    state["result_sources"] = {"source": "SQL_ONLY"}
```

---

## 🔍 Summary: Business Logic Highlights

✅ **Intent-Based Routing**: 4 execution paths (SQL, Vector, Hybrid, Chitchat)  
✅ **Conversation Continuity**: Follow-up detection and context expansion  
✅ **Multi-Attempt Validation**: SQL regeneration with error feedback  
✅ **Cached Results**: Efficient follow-up visualizations without re-execution  
✅ **Graceful Degradation**: Fallbacks for every failure scenario  
✅ **State Flow**: Immutable state transitions through LangGraph  

---

[← Back to Part 3: Data Storage](project-doc-3-data-storage.md) | [Continue to Part 5: APIs & Interfaces →](project-doc-5-apis-interfaces.md)

**Document Version**: 1.0  
**Last Updated**: 2026-02-02
