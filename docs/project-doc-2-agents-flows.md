# QbotzChatbot - Complete Project Documentation
## Part 2: Core Components - Agents & Flows

[← Back to Part 1: Overview](project-doc-1-overview-architecture.md) | [Part 3: Data Layer →](project-doc-3-data-storage.md)

---

## 📋 Table of Contents

1. [Agent Architecture](#agent-architecture)
2. [The 8 Specialized Agents](#the-8-specialized-agents)
3. [Execution Flows](#execution-flows)
4. [Agent Interactions](#agent-interactions)

---

## 🏗️ Agent Architecture

### Base Agent Pattern

All agents inherit from `BaseAgent` (`core/agents/base_agent.py`):

```python
class BaseAgent:
    """
    Base class for all agents in the system.
    Provides standardized interface and utilities.
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_logger(agent_name)
    
    def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Standard agent interface method.
        All agents MUST implement this.
        
        Args:
            query: User's question or input
            context: Additional context (conversation history, metadata, etc.)
        
        Returns:
            {
                "success": bool,      # True if agent completed successfully
                "result": Any,        # Agent-specific output data
                "error": Optional[str] # Error message if failed
            }
        """
        raise NotImplementedError("Subclasses must implement run()")
    
    def _create_response(self, success: bool, result: Any = None, error: str = None):
        """Helper to create standardized response"""
        return {
            "success": success,
            "result": result,
            "error": error
        }
```

### Agent Design Principles

1. **Single Responsibility**: Each agent does ONE thing well
2. **Standardized Interface**: All agents use same `run()` signature
3. **Stateless**: Agents don't store state between calls
4. **Error Handling**: Always return structured response with error info
5. **Logging**: All agents log operations for observability
6. **Testing**: Easy to test in isolation (unit tests)

---

## 🎭 The 8 Specialized Agents

### 1. ConversationResolverAgent

**File**: `core/agents/conversation_resolver_agent.py` (6,994 bytes)

**Purpose**: Resolves follow-up questions by expanding vague references using conversation history.

**When It Runs**: FIRST node in the pipeline, before intent classification.

#### How It Works

```python
# Example Conversation
User: "Who are the top customers in EAST region?"
Bot: "The top customers are ABC Corp ($500K) and XYZ Inc ($450K)."

User: "Show me their order counts"
       ↓
ConversationResolver expands to:
       ↓
"Show me order counts for ABC Corp and XYZ Inc in EAST region"
```

#### Implementation Details

```python
class ConversationResolverAgent(BaseAgent):
    def __init__(self):
        super().__init__("conversation_resolver")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
    
    def run(self, query: str, context: Dict) -> Dict:
        """
        Args:
            query: Current user question
            context: {
                "conversation_history": List[{role, content}],
                "last_turn": {user_query, intent, entities, ...}
            }
        
        Returns:
            {
                "success": True,
                "result": {
                    "resolved_query": str,    # Expanded query
                    "is_follow_up": bool,      # True if references history
                    "reasoning": str           # Why it's follow-up
                }
            }
        """
```

#### Detection Logic

The agent checks for follow-up indicators:

```python
FOLLOW_UP_INDICATORS = [
    # Pronouns
    "it", "that", "this", "those", "these", "they", "them",
    
    # References
    "same", "similar", "above", "previous", "last",
    
    # Comparatives
    "more", "less", "different", "other", "another",
    
    # Implicit references
    "also", "too", "as well"
]
```

#### LLM Prompt Structure

```python
prompt = f"""
You are a conversation analyst. Determine if this query is a follow-up.

CONVERSATION HISTORY:
{format_history(conversation_history)}

CURRENT QUERY: "{query}"

TASK:
1. Is this a follow-up question? (references previous context)
2. If yes, expand the query with necessary context
3. If no, return the query unchanged

Respond in JSON:
{{
    "is_follow_up": true/false,
    "resolved_query": "...",
    "reasoning": "..."
}}
"""
```

#### Edge Cases Handled

1. **No History**: First question = always `is_follow_up=False`
2. **Chitchat After Analytics**: "Thank you" after data query = chitchat, not follow-up
3. **New Topic**: "What about deliveries?" after "Show revenue" = not follow-up
4. **Implicit References**: "Break it down by region" = follow-up

---

### 2. IntentClassifierAgent

**File**: `core/agents/intent_classifier_agent.py` (5,530 bytes)

**Purpose**: Classifies user intent to route to correct execution path.

**When It Runs**: SECOND node, after conversation resolution.

#### The 4 Intent Types

```python
IntentType = Literal["ANALYTICAL", "SEMANTIC", "HYBRID", "CHITCHAT"]
```

| Intent | Description | Example Queries | Execution Path |
|--------|-------------|-----------------|----------------|
| **ANALYTICAL** | Precise, measurable questions requiring SQL | "Top 10 customers by revenue"<br>"Sales total in Q1 2024"<br>"Average order value" | SQL Flow |
| **SEMANTIC** | Conceptual, pattern-based questions | "Delivery quality trends"<br>"Customer satisfaction issues"<br>"Unusual orders" | Vector Flow |
| **HYBRID** | Needs both precision AND context | "High-value customers with delivery problems"<br>"Top products by revenue with quality issues" | Hybrid Flow |
| **CHITCHAT** | Casual conversation, greetings, help | "Hello"<br>"Thank you"<br>"What can you do?" | Chitchat Flow |

#### Classification Logic

```python
def _classify(self, query: str, context: Dict) -> Dict:
    """
    Uses LLM with few-shot examples to classify intent.
    
    Temperature: 0 (deterministic)
    Model: llama-3.3-70b-versatile
    
    Returns:
        {
            "intent": "ANALYTICAL|SEMANTIC|HYBRID|CHITCHAT",
            "confidence": float (0-1),
            "reasoning": str
        }
    """
```

#### Classification Prompt

```python
prompt = f"""
Classify the user's intent for this sales analytics query.

INTENT TYPES:
1. ANALYTICAL - Needs precise SQL (counts, sums, rankings, filters)
2. SEMANTIC - Needs conceptual search (trends, patterns, quality)
3. HYBRID - Needs both SQL precision AND semantic context
4. CHITCHAT - Casual conversation, not a data query

FEW-SHOT EXAMPLES:
- "Top 5 customers" → ANALYTICAL (simple aggregation)
- "Delivery issues" → SEMANTIC (pattern/quality search)
- "High-revenue customers with delays" → HYBRID (both)
- "Hello" → CHITCHAT

QUERY: "{query}"

Respond in JSON:
{{
    "intent": "ANALYTICAL",
    "confidence": 0.95,
    "reasoning": "Requires SQL aggregation..."
}}
"""
```

#### Confidence Scoring

- **0.9-1.0**: Very clear intent
- **0.7-0.9**: Confident classification
- **0.5-0.7**: Ambiguous (might need HYBRID)
- **<0.5**: Unclear (defaults to CHITCHAT)

---

### 3. SQLAgent

**File**: `core/agents/sql_agent.py` (43,400 bytes) - Most complex agent

**Purpose**: Generates valid PostgreSQL queries from natural language.

**When It Runs**: During SQL Flow execution.

#### Multi-Layer Architecture

```
┌─────────────────────────────────────────────┐
│  1. SCHEMA MANAGEMENT                       │
│  • Dynamic schema fetching                  │
│  • Column categorization                    │
│  • Important column identification          │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  2. FEW-SHOT LEARNING                       │
│  • Dynamic example retrieval                │
│  • Semantic similarity matching             │
│  • Query pattern library                    │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  3. SQL GENERATION (LLM)                    │
│  • Prompt with schema + examples            │
│  • Temperature 0 (deterministic)            │
│  • Anti-hallucination instructions          │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  4. VALIDATION LAYERS                       │
│  ① Policy Check (no DROP/DELETE)            │
│  ② Column Validation (exists in schema)     │
│  ③ Auto-Correction (fuzzy matching)         │
│  ④ Dry-Run Validation (EXPLAIN)             │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  5. REGENERATION (if validation fails)      │
│  • Error feedback to LLM                    │
│  • Up to 2 regeneration attempts            │
└──────────────────┬──────────────────────────┘
                   ↓
              Valid SQL ✓
```

#### 1. Dynamic Schema Management

```python
def _fetch_dynamic_schema(self) -> Dict[str, str]:
    """
    Fetches schema from information_schema at runtime.
    No hardcoded schemas!
    
    Query:
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_name = 'sales_orders'
        ORDER BY ordinal_position;
    
    Returns:
        {
            "sales_order": "VARCHAR(20)",
            "total_net_amount": "DECIMAL(15,2)",
            "sales_order_date": "DATE",
            ...
        }
    """
```

#### 2. Smart Column Categorization

```python
def _get_categorized_columns(self) -> Dict[str, List[str]]:
    """
    Organizes columns by business domain.
    Helps LLM understand schema structure.
    
    Returns:
        {
            "Revenue & Financial": [
                "total_net_amount",
                "billing_status"
            ],
            "Customer Information": [
                "sold_to_party",
                "sold_to_party_name",
                "customer_group"
            ],
            "Product & Material": [
                "material",
                "material_description",
                "order_quantity"
            ],
            "Geography & Organization": [
                "sales_district",
                "sales_organization",
                "plant"
            ],
            "Dates & Timestamps": [
                "sales_order_date",
                "created_at",
                "updated_at"
            ],
            "Status & Tracking": [
                "delivery_status",
                "billing_status"
            ]
        }
    """
```

#### 3. Few-Shot Learning

The agent uses a semantic few-shot store:

```python
def _get_relevant_examples(self, query: str) -> List[Dict]:
    """
    Retrieves most relevant SQL examples based on semantic similarity.
    
    Process:
    1. Embed user query → 768-dim vector
    2. Compare to stored example embeddings
    3. Return top-K most similar examples
    
    Example Library (sql-reference/query_patterns.py):
    - Time series aggregations
    - Top N rankings
    - Contribution analysis
    - Period comparisons
    - Customer analytics
    """
```

Example patterns stored:

```python
QUERY_PATTERNS = [
    {
        "description": "Monthly sales trend",
        "natural_language": "Show me sales trend over last 6 months",
        "sql": """
            SELECT 
                DATE_TRUNC('month', sales_order_date) as month,
                SUM(total_net_amount) as revenue
            FROM sales_orders
            WHERE sales_order_date >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY month
            ORDER BY month
        """
    },
    {
        "description": "Top customers by revenue",
        "natural_language": "Who are the top 10 customers by revenue?",
        "sql": """
            SELECT 
                sold_to_party_name,
                SUM(total_net_amount) as total_revenue
            FROM sales_orders
            GROUP BY sold_to_party_name
            ORDER BY total_revenue DESC
            LIMIT 10
        """
    },
    # ... 20+ more patterns
]
```

#### 4. Column Validation & Auto-Correction

```python
def _validate_columns(self, sql: str) -> Tuple[bool, List[str], List[str]]:
    """
    Validates all column references in SQL.
    
    Returns:
        (is_valid, invalid_columns, suggestions)
    
    Example:
        SQL: "SELECT customer_name FROM sales_orders"
        Returns: (False, ["customer_name"], ["sold_to_party_name"])
    """

def _find_similar_column(self, invalid_col: str, threshold: float = 0.6) -> Optional[str]:
    """
    Fuzzy matching using SequenceMatcher.
    
    Examples:
        "customer_name" → "sold_to_party_name" (0.65 similarity)
        "revenue" → "total_net_amount" (0.45 similarity)
        "order_date" → "sales_order_date" (0.85 similarity)
    """

def _auto_correct_sql(self, sql: str, invalid_columns: List[str], suggestions: List[str]):
    """
    Automatically replaces invalid columns with suggestions.
    
    Example:
        Input:  "SELECT customer_name, revenue FROM sales_orders"
        Output: "SELECT sold_to_party_name, total_net_amount FROM sales_orders"
        
        Corrections: [
            {"from": "customer_name", "to": "sold_to_party_name"},
            {"from": "revenue", "to": "total_net_amount"}
        ]
    """
```

#### 5. SQL Generation Prompt

```python
prompt = f"""
You are an expert PostgreSQL query generator for SAP sales data.

⚠️ CRITICAL: Use ONLY columns that exist in the schema below.

DATABASE SCHEMA:
{categorized_schema}

FEW-SHOT EXAMPLES:
{relevant_examples}

USER QUERY: "{query}"

REQUIREMENTS:
1. Generate PostgreSQL-compatible SQL
2. Use ONLY columns from the schema above
3. Include proper JOINs if needed (self-join on sales_orders)
4. Apply appropriate filters, GROUP BY, ORDER BY
5. Limit results to reasonable size (add LIMIT if no limit specified)
6. Use proper date functions (DATE_TRUNC, INTERVAL)
7. Return ONLY the SQL query, no explanations

RESPOND WITH ONLY THE SQL QUERY:
"""
```

#### 6. Multi-Attempt Validation Flow

```python
def _generate_sql(self, query: str, context: Dict) -> str:
    """
    Generate SQL with multi-layer validation.
    
    Flow:
    1. Generate SQL using LLM
    2. Validate columns exist
    3. If invalid:
       a. Try auto-correction
       b. If still invalid, regenerate with error feedback
    4. Policy validation (no DROP/DELETE)
    5. Dry-run validation (EXPLAIN)
    6. Return valid SQL or raise error
    
    Max attempts: 3 (1 initial + 2 regenerations)
    """
    
    for attempt in range(settings.SQL_MAX_REGENERATION_ATTEMPTS):
        sql = self._call_llm(query, schema, examples)
        
        # Validate columns
        is_valid, invalid_cols, suggestions = self._validate_columns(sql)
        
        if not is_valid:
            if settings.SQL_AUTO_CORRECT_COLUMNS:
                sql, corrections = self._auto_correct_sql(sql, invalid_cols, suggestions)
                self.logger.info("auto_corrected_sql", corrections=corrections)
            else:
                # Regenerate with error feedback
                sql = self._regenerate_with_error_feedback(
                    query, sql, invalid_cols, schema
                )
        
        # Policy check
        validation = self._validate_sql(sql)
        if not validation["valid"]:
            raise ValueError(f"SQL policy violation: {validation['reason']}")
        
        # Dry-run check
        if self._dry_run_validate(sql):
            return sql
    
    raise ValueError("Failed to generate valid SQL after max attempts")
```

#### Error Handling

```python
def _handle_error(self, e: Exception, query: str) -> Dict:
    """
    Standardized error handler.
    
    Returns:
        {
            "success": False,
            "result": {
                "sql": None,
                "results": [],
                "error_type": "GENERATION_ERROR",
                "error_message": str(e)
            },
            "error": str(e)
        }
    """
```

---

### 4. EmbeddingAgent

**File**: `core/agents/embedding_agent.py` (3,502 bytes)

**Purpose**: Converts text queries to 768-dimensional vectors for semantic search.

**When It Runs**: During Vector Flow execution.

#### Implementation

```python
class EmbeddingAgent(BaseAgent):
    def __init__(self):
        super().__init__("embedding_agent")
        # Uses singleton pattern - model loaded once globally
        self.embedding_model = EmbeddingModelManager.get_instance()
    
    def run(self, query: str, context: Dict = None) -> Dict:
        """
        Args:
            query: Text to embed
            context: (unused, for interface consistency)
        
        Returns:
            {
                "success": True,
                "result": {
                    "embedding": List[float],  # 768 dimensions
                    "dimension": 768,
                    "model": "all-mpnet-base-v2"
                }
            }
        """
        try:
            embedding = self.embedding_model.encode_single(query)
            
            return self._create_response(
                success=True,
                result={
                    "embedding": embedding,
                    "dimension": len(embedding),
                    "model": settings.EMBEDDING_MODEL
                }
            )
        except Exception as e:
            return self._handle_error(e)
```

#### Why Singleton Pattern?

```
Model Loading Time: ~7 seconds
Model Size: ~420MB in memory
Requests/day: Thousands

Without Singleton:
- 7s delay per request ❌
- Memory thrashing ❌

With Singleton:
- 7s delay on first request only ✅
- Constant memory usage ✅
- Sub-100ms embeddings ✅
```

---

### 5. VectorVerifierAgent

**File**: `core/agents/vector_verifier_agent.py` (6,585 bytes)

**Purpose**: Scores the quality of vector search results.

**When It Runs**: After vector search, before returning results.

#### Scoring Logic

```python
class VectorVerifier(BaseAgent):
    def run(self, query: str, context: Dict) -> Dict:
        """
        Args:
            query: Original user query
            context: {
                "vector_results": List[Dict],  # Results from vector search
                "threshold": float              # Optional custom threshold
            }
        
        Returns:
            {
                "success": True,
                "result": {
                    "confidence": "HIGH|MEDIUM|LOW",
                    "avg_similarity": float,
                    "result_count": int,
                    "reasoning": str
                }
            }
        """
        results = context.get("vector_results", [])
        
        # Calculate metrics
        similarities = [r.get("similarity", 0) for r in results]
        avg_sim = sum(similarities) / len(similarities) if similarities else 0
        count = len(results)
        
        # Determine confidence
        if avg_sim > 0.7 and count >= 5:
            confidence = "HIGH"
        elif avg_sim > 0.5 and count >= 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return self._create_response(
            success=True,
            result={
                "confidence": confidence,
                "avg_similarity": avg_sim,
                "result_count": count,
                "reasoning": self._generate_reasoning(confidence, avg_sim, count)
            }
        )
```

#### Confidence Thresholds

| Confidence | Criteria | Meaning |
|------------|----------|---------|
| **HIGH** | similarity > 0.7 AND count >= 5 | Excellent matches, trust results |
| **MEDIUM** | similarity > 0.5 AND count >= 3 | Good matches, likely relevant |
| **LOW** | Otherwise | Weak matches, may need SQL instead |

---

### 6. SummarizerAgent

**File**: `core/agents/summarizer_agent.py` (7,506 bytes)

**Purpose**: Converts raw query results into natural language responses.

**When It Runs**: FINAL node before returning response to user.

#### Implementation

```python
class SummarizerAgent(BaseAgent):
    def __init__(self):
        super().__init__("summarizer")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
    
    def run(self, query: str, context: Dict) -> Dict:
        """
        Args:
            query: User's original question
            context: {
                "sql_results": List[Dict],     # From SQL flow
                "vector_results": List[Dict],  # From vector flow
                "intent": str                  # Type of query
            }
        
        Returns:
            {
                "success": True,
                "result": {
                    "summary": str,           # Natural language response
                    "result_count": int,
                    "formatted": bool
                }
            }
        """
```

#### Summarization Prompt

```python
prompt = f"""
You are a business analyst presenting data insights.

USER QUESTION: "{query}"

DATA RESULTS:
{format_results(results)}

TASK: Create a natural language answer that:
1. Directly answers the user's question
2. Highlights key insights
3. Uses proper formatting (numbers with commas, currency symbols)
4. Mentions result count if relevant
5. Keeps tone professional but friendly
6. Is concise (2-3 sentences max)

RESPONSE:
"""
```

#### Example Transformations

```python
# Input
query = "Top 5 customers by revenue"
results = [
    {"sold_to_party_name": "ABC Corp", "total_revenue": 500000},
    {"sold_to_party_name": "XYZ Inc", "total_revenue": 450000},
    {"sold_to_party_name": "Acme Ltd", "total_revenue": 400000},
    {"sold_to_party_name": "TechCo", "total_revenue": 380000},
    {"sold_to_party_name": "GlobalSales", "total_revenue": 350000}
]

# Output
summary = """
The top 5 customers by revenue are:
1. ABC Corp - $500,000
2. XYZ Inc - $450,000
3. Acme Ltd - $400,000
4. TechCo - $380,000
5. GlobalSales - $350,000

Total revenue from these customers: $2,080,000
"""
```

---

### 7. VisualizationAgent

**File**: `core/agents/visualization_agent.py` (17,143 bytes)

**Purpose**: Determines if/how to visualize data and generates charts.

**When It Runs**: After execution flows, before summarization.

#### Two Use Cases

1. **Simultaneous**: "Show me sales trend as a line chart"
   - Query contains visualization keyword AND data request
   - Generate chart from current results

2. **Follow-up**: "Visualize that" or "Show me a chart"
   - Previous turn had results
   - Use cached results from `last_turn_metadata`

#### Detection Logic

```python
VIZ_KEYWORDS = [
    "chart", "graph", "plot", "visualize", "show me",
    "bar chart", "line chart", "pie chart",
    "trend", "over time"
]

def _detect_viz_intent(self, query: str) -> bool:
    """Check if query contains visualization keywords."""
    return any(keyword in query.lower() for keyword in VIZ_KEYWORDS)
```

#### Chart Type Selection

Uses LLM to determine appropriate chart type:

```python
prompt = f"""
Suggest the best chart type for this data.

USER QUERY: "{query}"

DATA PREVIEW:
{json.dumps(results[:5], indent=2)}

AVAILABLE CHART TYPES:
- bar: Categorical comparisons (top N, group comparisons)
- line: Trends over time, continuous data
- pie: Part-to-whole relationships (market share, distribution)
- area: Cumulative trends over time

RULES:
1. If data has date/time → line or area
2. If data shows categories → bar
3. If data shows percentages/shares → pie
4. If unclear → bar (safest default)

Respond in JSON:
{{
    "chart_type": "bar",
    "x": "column_name",
    "y": "column_name",
    "reasoning": "..."
}}
"""
```

#### Chart Generation

Delegates to `ChartGeneratorTool`:

```python
def run(self, query: str, context: Dict) -> Dict:
    # 1. Detect if visualization needed
    needs_viz = self._detect_viz_intent(query)
    
    # 2. Get data (current or cached)
    results = context.get("sql_results") or context.get("last_turn_results")
    
    if not needs_viz or not results:
        return {"should_visualize": False, "viz_config": None}
    
    # 3. Get chart config from LLM
    config = self._suggest_visualization(query, results)
    
    # 4. Generate chart using tool
    chart_data = chart_generator_tool.generate_chart(
        data=results,
        chart_type=config["chart_type"],
        x=config["x"],
        y=config["y"]
    )
    
    # 5. Return config with chart artifacts
    return {
        "should_visualize": True,
        "viz_config": {
            "chart_type": config["chart_type"],
            "x": config["x"],
            "y": config["y"],
            "data": results,
            "chart_html": chart_data["html"],        # Interactive Plotly
            "chart_base64": chart_data["base64"],    # Static PNG
            "chart_json": chart_data["json"],        # Plotly figure spec
            "theme": "plotly_dark"
        }
    }
```

---

### 8. IntentClassifier (Detailed)

Already covered above, but adding decision tree:

```
┌─────────────────────────────────────────┐
│  Contains data query?                   │
└───────────┬─────────────────────────────┘
            │
      ┌─────┴─────┐
      NO          YES
      │            │
      ▼            ▼
┌──────────┐  ┌────────────────────────────┐
│CHITCHAT  │  │ Requires aggregation/      │
└──────────┘  │ counting/filtering?        │
              └───────────┬────────────────┘
                          │
                    ┌─────┴─────┐
                   YES          NO
                    │            │
                    ▼            ▼
              ┌──────────┐  ┌────────────┐
              │SQL-only? │  │ SEMANTIC   │
              └────┬─────┘  └────────────┘
                   │
            ┌──────┴──────┐
           YES           NO
            │             │
            ▼             ▼
      ┌──────────┐  ┌─────────┐
      │ANALYTICAL│  │ HYBRID  │
      └──────────┘  └─────────┘
```

---

## 🔄 Execution Flows

Flows combine agents with business logic to implement complete execution paths.

### 1. SQLExecutionFlow

**File**: `core/flows/sql_flow.py` (1,581 bytes)

**Purpose**: Generate SQL → Execute → Return results

```python
class SQLExecutionFlow:
    def __init__(self, sql_agent: SQLAgent):
        self.sql_agent = sql_agent
        self.logger = get_logger("sql_flow")
    
    def run(self, state: ChatbotState) -> ChatbotState:
        """
        Execute SQL flow.
        
        Steps:
        1. Call SQLAgent to generate SQL
        2. Execute SQL using sql_executor tool
        3. Store results in state
        4. Store metadata for follow-up queries
        
        Args:
            state: ChatbotState with query
        
        Returns:
            Updated state with sql, sql_results, last_sql_context
        """
        query = state["query"]
        
        # 1. Generate SQL
        sql_result = self.sql_agent.run(query, {"state": state})
        
        if not sql_result["success"]:
            state["error"] = sql_result["error"]
            return state
        
        sql = sql_result["result"]["sql"]
        state["sql"] = sql
        
        # 2. Execute SQL
        try:
            from core.tools.sql_executor import execute_sql
            results = execute_sql(sql)
            
            state["sql_results"] = results
            state["last_sql_context"] = {
                "sql": sql,
                "result_count": len(results),
                "columns": list(results[0].keys()) if results else []
            }
            
            self.logger.info("sql_execution_success", 
                           result_count=len(results))
        
        except Exception as e:
            self.logger.error("sql_execution_failed", error=str(e))
            state["error"] = f"SQL execution failed: {str(e)}"
        
        return state
```

---

### 2. VectorExecutionFlow

**File**: `core/flows/vector_flow.py` (1,444 bytes)

**Purpose**: Embed query → Search vectors → Verify quality

```python
class VectorExecutionFlow:
    def __init__(self, embedding_agent: EmbeddingAgent, 
                 verifier_agent: VectorVerifier):
        self.embedding_agent = embedding_agent
        self.verifier_agent = verifier_agent
        self.logger = get_logger("vector_flow")
    
    def run(self, state: ChatbotState) -> ChatbotState:
        """
        Execute vector search flow.
        
        Steps:
        1. Get query embedding (768-dim vector)
        2. Search vector database for similar documents
        3. Verify result quality
        4. Store results in state
        
        Args:
            state: ChatbotState with query
        
        Returns:
            Updated state with vector_results, vector_confidence
        """
        query = state.get("expanded_query") or state["query"]
        
        # 1. Generate embedding
        embed_result = self.embedding_agent.run(query)
        
        if not embed_result["success"]:
            state["error"] = embed_result["error"]
            return state
        
        embedding = embed_result["result"]["embedding"]
        
        # 2. Search vectors
        try:
            from core.tools.vector_search_tool import vector_search_tool
            
            search_results = vector_search_tool(
                query_embedding=embedding,
                limit=10,
                threshold=0.5
            )
            
            state["vector_results"] = search_results
            
            # 3. Verify quality
            verify_result = self.verifier_agent.run(query, {
                "vector_results": search_results
            })
            
            if verify_result["success"]:
                state["vector_confidence"] = verify_result["result"]["confidence"]
            
            self.logger.info("vector_search_success",
                           result_count=len(search_results),
                           confidence=state.get("vector_confidence"))
        
        except Exception as e:
            self.logger.error("vector_search_failed", error=str(e))
            state["error"] = f"Vector search failed: {str(e)}"
        
        return state
```

---

### 3. HybridExecutionFlow

**File**: `core/flows/hybrid_flow.py` (6,185 bytes)

**Purpose**: Run both SQL + Vector → Intelligently merge results

#### Merging Algorithm

```python
class HybridExecutionFlow:
    def __init__(self, sql_flow, vector_flow, 
                 sql_weight=0.6, vector_weight=0.4):
        self.sql_flow = sql_flow
        self.vector_flow = vector_flow
        self.sql_weight = sql_weight
        self.vector_weight = vector_weight
    
    def run(self, state: ChatbotState) -> ChatbotState:
        """
        Execute hybrid search.
        
        Algorithm:
        1. Run SQL flow (get precise results)
        2. Run Vector flow (get semantic results)
        3. Merge with weighted scoring
        4. Deduplicate by sales_order
        5. Sort by combined score
        
        Scoring:
        - SQL: score = 1/rank (top result = 1.0, 2nd = 0.5, etc.)
        - Vector: score = similarity (0-1)
        - Combined: sql_score * 0.6 + vector_score * 0.4
        """
        # 1. Run both flows
        state = self.sql_flow.run(state)
        state = self.vector_flow.run(state)
        
        # 2. Extract results
        sql_results = state.get("sql_results", [])
        vector_results = state.get("vector_results", [])
        
        # 3. Merge
        hybrid_results = self._merge_results(sql_results, vector_results)
        
        state["hybrid_results"] = hybrid_results
        state["result_sources"] = self._annotate_sources(hybrid_results)
        
        return state
    
    def _merge_results(self, sql_results, vector_results):
        """
        Intelligent merge with deduplication.
        
        Example:
        SQL Results:
        1. Order A (rank=1, score=1.0)
        2. Order B (rank=2, score=0.5)
        
        Vector Results:
        - Order A (similarity=0.9)
        - Order C (similarity=0.8)
        
        Merged:
        1. Order A: 1.0*0.6 + 0.9*0.4 = 0.96 (BOTH)
        2. Order C: 0*0.6 + 0.8*0.4 = 0.32 (VECTOR)
        3. Order B: 0.5*0.6 + 0*0.4 = 0.30 (SQL)
        """
        merged_map = {}
        
        # Process SQL results
        for rank, result in enumerate(sql_results, start=1):
            sales_order = result.get("sales_order")
            sql_score = 1.0 / rank
            
            merged_map[sales_order] = {
                **result,
                "source": "SQL",
                "sql_rank": rank,
                "sql_score": sql_score,
                "vector_similarity": None,
                "hybrid_score": sql_score * self.sql_weight
            }
        
        # Process Vector results
        for result in vector_results:
            sales_order = result.get("sales_order")
            similarity = result.get("similarity", 0.0)
            
            if sales_order in merged_map:
                # Boost existing SQL result
                merged_map[sales_order]["source"] = "BOTH"
                merged_map[sales_order]["vector_similarity"] = similarity
                merged_map[sales_order]["hybrid_score"] = (
                    merged_map[sales_order]["sql_score"] * self.sql_weight +
                    similarity * self.vector_weight
                )
            else:
                # New vector-only result
                merged_map[sales_order] = {
                    **result,
                    "source": "VECTOR",
                    "vector_similarity": similarity,
                    "hybrid_score": similarity * self.vector_weight
                }
        
        # Sort by hybrid score
        merged_results = list(merged_map.values())
        merged_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        
        return merged_results
```

---

### 4. ChitchatFlow

**File**: `core/flows/chitchat_flow.py` (1,167 bytes)

**Purpose**: Handle casual conversation

```python
class ChitchatFlow:
    def __init__(self):
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
        self.logger = get_logger("chitchat_flow")
    
    def run(self, state: ChatbotState) -> ChatbotState:
        """
        Handle chitchat queries.
        
        Examples:
        - "Hello" → "Hi! I'm your SAP sales analytics assistant..."
        - "Thank you" → "You're welcome!"
        - "What can you do?" → Lists capabilities
        """
        query = state["query"]
        
        prompt = f"""
You are a helpful SAP sales analytics assistant.

User said: "{query}"

Respond naturally and helpfully. If they're greeting you, greet back and 
mention you can help with sales data analysis. If they're thanking you, 
acknowledge politely. Keep responses brief and friendly.

RESPONSE:
"""
        
        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7  # Allow some creativity
        )
        
        state["summary"] = response.choices[0].message.content
        
        return state
```

---

## 🔗 Agent Interaction Patterns

### Sequential Flow

```
ConversationResolver → IntentClassifier → [Flow] → Visualization → Summarizer
```

Each agent passes updated state to the next.

### Parallel Potential (Not Currently Implemented)

```
                    ┌→ SQLFlow ───┐
IntentClassifier ───┤             ├→ Merge → ...
                    └→ VectorFlow ┘
```

Could run SQL and Vector flows in parallel for performance.

### Error Propagation

```python
if agent_result["success"] == False:
    state["error"] = agent_result["error"]
    return state  # Short-circuit remaining nodes
```

### State Immutability

Agents don't modify state directly; they return new state:

```python
# ❌ Wrong
def run(self, state):
    state["sql"] = generate_sql()
    return state

# ✅ Correct
def run(self, state):
    sql = generate_sql()
    return {**state, "sql": sql}
```

---

## 📊 Agent Performance Metrics

| Agent | Avg Time | Cache? | Notes |
|-------|----------|--------|-------|
| ConversationResolver | 500ms-1s | No | LLM call |
| IntentClassifier | 500ms-1s | No | LLM call |
| SQLAgent | 1-2s | Schema cached | LLM + validation |
| EmbeddingAgent | 50-100ms | Model singleton | Fast inference |
| VectorVerifier | <10ms | No | Pure computation |
| Summarizer | 500ms-1s | No | LLM call |
| VisualizationAgent | 1-2s | No | LLM + chart gen |

**Total Pipeline**: 3-5 seconds typical

---

## 🎓 Summary

The agent architecture provides:

✅ **Modularity**: Each agent is independently testable  
✅ **Maintainability**: Single responsibility per agent  
✅ **Extensibility**: Easy to add new agents  
✅ **Observability**: Comprehensive logging at each step  
✅ **Robustness**: Graceful error handling and fallbacks  

---

[← Back to Part 1](project-doc-1-overview-architecture.md) | [Continue to Part 3: Data Layer →](project-doc-3-data-storage.md)

**Document Version**: 1.0  
**Last Updated**: 2026-02-02
