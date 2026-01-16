from typing import TypedDict, List, Dict, Any, Optional, Literal


IntentType = Literal["ANALYTICAL", "SEMANTIC", "HYBRID", "CHITCHAT"]
VectorConfidence = Literal["HIGH", "MEDIUM", "LOW"]


class ConversationTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class EntityContext(TypedDict, total=False):
    sales_order_id: Optional[str]
    customer_id: Optional[str]
    region: Optional[str]
    date_range: Optional[Dict[str, str]]  # {"from": "...", "to": "..."}


class SQLContext(TypedDict, total=False):
    sql: str
    result_count: int
    columns: List[str]


class ChatbotState(TypedDict):
    """
    Conversation state flowing through LangGraph.
    This state is minimal, explicit, and continuity-aware.
    """

    # ===== User input =====
    query: str

    # ===== Intent =====
    intent: Optional[IntentType]
    intent_confidence: Optional[float]
    is_follow_up: Optional[bool]

    # ===== SQL path =====
    sql: Optional[str]
    sql_results: Optional[List[Dict[str, Any]]]
    last_sql_context: Optional[SQLContext]

    # ===== Vector path =====
    expanded_query: Optional[str]
    vector_results: Optional[List[Dict[str, Any]]]
    vector_confidence: Optional[VectorConfidence]

    # ===== Hybrid path =====
    hybrid_results: Optional[List[Dict[str, Any]]]
    result_sources: Optional[Dict[str, Literal["SQL", "VECTOR", "BOTH"]]]

    # ===== Conversation memory =====
    conversation_history: List[ConversationTurn]
    entities: Optional[EntityContext]

    # ===== Final output =====
    summary: Optional[str]

    # ===== Error handling =====
    error: Optional[str]
