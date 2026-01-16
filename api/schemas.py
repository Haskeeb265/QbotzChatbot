from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    messages: List[Message] = Field(
        ...,
        description="Full conversation history, including the latest user query at the end.",
    )


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    intent: Optional[str] = None
    sql: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
