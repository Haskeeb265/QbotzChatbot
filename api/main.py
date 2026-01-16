from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

from api.schemas import ChatRequest, ChatResponse, Message
from core.graphs.supervisor import SupervisorGraph
from core.graphs.state import ChatbotState, ConversationTurn
from utility.observability.logger import get_logger

# Initialize Logger
logger = get_logger("api")

# Initialize App
app = FastAPI(
    title="Qbotz Sales Analytics API",
    description="Stateless API for SAP Sales Analytics Chatbot",
    version="1.0.0",
)

# CORS (Allow all for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Graph Singleton (Thread-safe agents)
chatbot_graph = SupervisorGraph()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "qbotz-api"}


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_cocompletions(request: ChatRequest):
    """
    Stateless chat endpoint.
    Accepts full conversation history, processes the last message, and returns the response.
    """
    try:
        messages = request.messages
        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        # 1. Extract latest query
        last_message = messages[-1]
        if last_message.role != "user":
            raise HTTPException(
                status_code=400, detail="Last message must be from user"
            )

        query = last_message.content

        # 2. Extract History (all messages except last)
        history: List[ConversationTurn] = []
        for msg in messages[:-1]:
            if msg.role in ["user", "assistant"]:
                history.append({"role": msg.role, "content": msg.content})

        # 3. Construct Initial State
        # We initialize with the query and the history provided by the client
        initial_state: ChatbotState = {
            "query": query,
            "conversation_history": history,
            "intent": None,
            "intent_confidence": None,
            "is_follow_up": None,
            "sql": None,
            "sql_results": None,
            "last_sql_context": None,
            "expanded_query": None,
            "vector_results": None,
            "vector_confidence": None,
            "hybrid_results": None,
            "result_sources": None,
            "entities": None,  # Future: could accept entities in request if client tracks them
            "summary": None,
            "error": None,
        }

        logger.info("api_request_received", query=query, history_length=len(history))

        # 4. Run the Graph
        # We run the graph synchronously here.
        # In a high-load prod env, you might want to run this in a threadpool
        # or convert agents to fully async.
        final_state = chatbot_graph.graph.invoke(initial_state)

        # 5. Extract Response
        response_content = (
            final_state.get("summary")
            or "I encountered an error processing your request."
        )

        # Log result
        logger.info(
            "api_request_complete",
            intent=final_state.get("intent"),
            response_length=len(response_content),
        )

        return ChatResponse(
            role="assistant",
            content=response_content,
            intent=final_state.get("intent"),
            sql=final_state.get("sql"),
            metadata={
                "intent_confidence": final_state.get("intent_confidence"),
                "sql_results_count": len(final_state.get("sql_results") or []),
                "vector_results_count": len(final_state.get("vector_results") or []),
                "hybrid_results_count": len(final_state.get("hybrid_results") or []),
            },
        )

    except Exception as e:
        logger.error("api_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
