from typing import List, Dict, Any, Optional


def format_conversation_context(
    history: Optional[List[Dict[str, Any]]], max_turns: int = 5
) -> str:
    """
    Format conversation history into a concise string for LLM context.

    Args:
        history: List of conversation turns with role/content
        max_turns: Maximum number of recent exchanges to include (default: 5)

    Returns:
        Formatted string with recent conversation context

    Example:
        >>> history = [
        ...     {"role": "user", "content": "Top customers?"},
        ...     {"role": "assistant", "content": "Customer 123 with 1M SAR..."}
        ... ]
        >>> format_conversation_context(history)
        'Previous Exchange:\nUser: Top customers?\nAssistant: Customer 123 with 1M SAR...'
    """
    if not history or len(history) == 0:
        return ""

    # Take last N exchanges (each exchange = user + assistant)
    # max_turns=5 means last 10 messages (5 user + 5 assistant)
    recent_history = history[-(max_turns * 2) :]

    if not recent_history:
        return ""

    lines = ["CONVERSATION HISTORY (recent):"]
    for msg in recent_history:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")

        # Truncate long messages to avoid token bloat
        if len(content) > 200:
            content = content[:200] + "..."

        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def is_follow_up_query(query: str, history: Optional[List[Dict[str, Any]]]) -> bool:
    """
    Detect if a query is likely a follow-up based on pronouns and context references.

    Args:
        query: Current user query
        history: Conversation history

    Returns:
        True if query appears to be a follow-up

    Examples:
        "What about EAST district?" → True (starts with "what about")
        "Show me their orders" → True (contains pronoun "their")
        "And the revenue?" → True (starts with "and")
        "Top 10 customers" → False (standalone query)
    """
    if not history or len(history) == 0:
        return False

    query_lower = query.lower().strip()

    # Follow-up patterns
    follow_up_starters = [
        "what about",
        "how about",
        "and ",
        "also ",
        "what if",
        "but ",
        "or ",
    ]

    # Pronouns indicating reference to previous context
    reference_pronouns = [
        "their",
        "them",
        "they",
        "it",
        "its",
        "that",
        "those",
        "these",
        "he",
        "she",
        "his",
        "her",
    ]

    # Check for follow-up starters
    for starter in follow_up_starters:
        if query_lower.startswith(starter):
            return True

    # Check for reference pronouns
    words = query_lower.split()
    for pronoun in reference_pronouns:
        if pronoun in words:
            return True

    # Short queries are often follow-ups
    if len(words) <= 3:
        return True

    return False


def get_last_query_context(history: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """
    Extract the last user query from history.

    Useful for providing context like:
    "Previous query: 'Top customers by revenue'"

    Args:
        history: Conversation history

    Returns:
        Last user query or None
    """
    if not history:
        return None

    # Find last user message
    for msg in reversed(history):
        if msg.get("role") == "user":
            return msg.get("content")

    return None


def add_to_history(
    history: List[Dict[str, Any]],
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Add a new message to conversation history.

    Args:
        history: Existing history
        role: 'user' or 'assistant'
        content: Message content
        metadata: Optional metadata (intent, SQL, etc.)

    Returns:
        Updated history list
    """
    new_entry = {"role": role, "content": content}

    if metadata:
        new_entry["metadata"] = metadata

    return history + [new_entry]
