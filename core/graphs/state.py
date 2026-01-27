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


class VisualizationConfig(TypedDict, total=False):
    """
    Configuration for chart generation and rendering.

    Fields:
        chart_type: Type of chart to generate
        x: Column name for x-axis
        y: Column name for y-axis
        data: Raw data for visualization
        chart_html: Interactive Plotly HTML (for web display)
        chart_base64: Static PNG image as base64 (for API/mobile)
        chart_json: Plotly figure JSON (for programmatic access)
        theme: Visual theme (plotly_white, plotly_dark, etc.)
        error: Error message if chart generation failed
    """

    chart_type: Literal["bar", "line", "pie", "area", "none"]
    x: str
    y: str
    data: List[Dict[str, Any]]
    chart_html: Optional[str]
    chart_base64: Optional[str]
    chart_json: Optional[Dict[str, Any]]
    theme: Optional[str]
    error: Optional[str]


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

    # ===== Visualization =====
    should_visualize: Optional[bool]
    visualization_config: Optional[VisualizationConfig]

    # ===== Final output =====
    summary: Optional[str]

    # ===== Error handling =====
    error: Optional[str]
