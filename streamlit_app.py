import streamlit as st
import pandas as pd
from datetime import datetime
from core.graphs.supervisor import SupervisorGraph

# Page config
st.set_page_config(
    page_title="SAP Sales Analytics Chatbot",
    page_icon="🤖",
    layout="wide",
)

# Initialize session state
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "last_turn_metadata" not in st.session_state:
    st.session_state.last_turn_metadata = None

if "supervisor" not in st.session_state:
    with st.spinner("🚀 Initializing AI agents..."):
        st.session_state.supervisor = SupervisorGraph()

# Pre-load embedding model
if "embedding_model_loaded" not in st.session_state:
    with st.spinner("🔧 Loading embedding model..."):
        from core.storage.embedding import EmbeddingModelManager

        EmbeddingModelManager.get_instance()
        st.session_state.embedding_model_loaded = True

# Header
st.title("🤖 SAP Sales Analytics Chatbot")
st.caption("Multi-Agent AI • Conversation Memory • SQL + Vector Search")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown(
        """
    **Ask questions about SAP sales data!**
    
    **Features:**
    - 🔄 Conversation Continuity
    - 🎯 Intent Classification
    - 🔧 SQL Generation
    - 🔍 Vector Search
    """
    )

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.last_turn_metadata = None
        st.rerun()

# Display conversation history
for msg in st.session_state.conversation_history:
    role = msg.get("role", "user")
    content = msg.get("content", "")

    with st.chat_message(role):
        st.markdown(content)

        # Show metadata for assistant messages
        if role == "assistant" and "metadata" in msg:
            meta = msg["metadata"]
            with st.expander("📊 Details"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Intent", meta.get("intent", "N/A"))
                    if meta.get("is_follow_up") is not None:
                        st.metric("Follow-up", "Yes" if meta["is_follow_up"] else "No")
                with col2:
                    if meta.get("sql"):
                        st.code(meta["sql"], language="sql")

# Chat input
if prompt := st.chat_input("Ask about your sales data..."):
    # Add user message
    st.session_state.conversation_history.append(
        {"role": "user", "content": prompt, "timestamp": datetime.now().isoformat()}
    )

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Processing..."):
            # Call supervisor
            result = st.session_state.supervisor.run(
                query=prompt,
                conversation_history=st.session_state.conversation_history,
                last_turn_metadata=st.session_state.last_turn_metadata,
            )

            # Get response
            summary = result.get("summary", "I couldn't generate a response.")

            # Display response
            st.markdown(summary)

            # Render visualization if available
            if result.get("should_visualize") and result.get("visualization_config"):
                viz = result["visualization_config"]

                st.subheader("📊 Visualization")

                # Check for errors first
                if viz.get("error"):
                    st.error(f"⚠️ Chart generation failed: {viz['error']}")
                    st.info(
                        "💡 Tip: Try rephrasing your question or asking for a different chart type."
                    )

                # Display interactive chart (preferred)
                elif viz.get("chart_html"):
                    try:
                        import streamlit.components.v1 as components

                        components.html(
                            viz["chart_html"],
                            height=650,  # Slightly taller for better viewing
                            scrolling=False,
                        )

                        # Add download hint
                        st.caption(
                            "💡 Hover over the chart for interactive controls. Click 📷 to download."
                        )

                    except Exception as e:
                        st.warning(f"Could not render interactive chart: {str(e)}")

                        # Fallback to static image if HTML fails
                        if viz.get("chart_base64"):
                            st.image(viz["chart_base64"], use_container_width=True)

                # Fallback: Display static image if no HTML
                elif viz.get("chart_base64"):
                    st.image(viz["chart_base64"], use_container_width=True)
                    st.caption("📷 Static chart image")

                else:
                    st.warning(
                        "Chart configuration exists but no renderable output was generated."
                    )

            # Show metadata
            with st.expander("📊 Details"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Intent", result.get("intent", "N/A"))
                    if result.get("is_follow_up") is not None:
                        st.metric(
                            "Follow-up", "Yes" if result["is_follow_up"] else "No"
                        )
                with col2:
                    if result.get("sql"):
                        st.code(result["sql"], language="sql")

    # Add assistant message to history
    st.session_state.conversation_history.append(
        {
            "role": "assistant",
            "content": summary,
            "intent": result.get("intent"),
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "intent": result.get("intent"),
                "is_follow_up": result.get("is_follow_up"),
                "sql": result.get("sql"),
            },
        }
    )

    # Update last turn metadata (store results for follow-up visualization)
    sql_results = result.get("sql_results")
    st.session_state.last_turn_metadata = {
        "user_query": prompt,
        "intent": result.get("intent"),
        "sql": result.get("sql"),
        "sql_results": sql_results[:10] if sql_results else None,  # Store last 10 rows
        "entities": {},
        "filters": {},
        "had_results": bool(sql_results or result.get("vector_results")),
    }

    # Keep only last 10 messages
    if len(st.session_state.conversation_history) > 10:
        st.session_state.conversation_history = st.session_state.conversation_history[
            -10:
        ]
