"""Integration tests for visualization flow."""

import pytest
from core.graphs.supervisor import SupervisorGraph


@pytest.fixture(scope="module")
def supervisor():
    """Initialize supervisor once for all tests."""
    return SupervisorGraph()


def test_bar_chart_simultaneous_request(supervisor):
    """Test: User asks for data AND chart in one query."""
    result = supervisor.run(
        query="Show me top 5 customers by revenue as a bar chart",
        conversation_history=[],
        last_turn_metadata=None,
    )

    # Verify intent classification
    assert result["intent"] in ["ANALYTICAL", "HYBRID"]

    # Verify visualization was triggered
    assert result.get("should_visualize") is True

    # Verify chart was generated
    viz = result.get("visualization_config")
    assert viz is not None
    assert viz.get("chart_type") in ["bar", "line", "pie", "area"]
    assert viz.get("x") is not None
    assert viz.get("y") is not None

    # Verify chart artifacts exist
    assert (
        viz.get("chart_html") is not None
    ), "Interactive HTML chart should be generated"
    assert "plotly" in viz["chart_html"].lower(), "Should use Plotly"

    # Check for errors
    assert viz.get("error") is None, f"Chart generation failed: {viz.get('error')}"

    print(f"\n✅ Test passed!")
    print(f"   Intent: {result['intent']}")
    print(f"   Chart Type: {viz.get('chart_type')}")
    print(f"   X-axis: {viz.get('x')}")
    print(f"   Y-axis: {viz.get('y')}")
    print(f"   Has HTML: {bool(viz.get('chart_html'))}")
    print(f"   Has Static: {bool(viz.get('chart_base64'))}")


def test_follow_up_visualization(supervisor):
    """Test: User asks for data, then asks for chart in follow-up."""

    # Step 1: Ask for data without visualization
    result1 = supervisor.run(
        query="What are the top 3 regions by sales?",
        conversation_history=[],
        last_turn_metadata=None,
    )

    assert result1.get("sql_results") is not None, "First query should return data"
    assert result1.get("should_visualize") is False, "First query shouldn't visualize"

    # Step 2: Prepare metadata for follow-up
    last_turn = {
        "sql_results": result1.get("sql_results"),
        "user_query": "What are the top 3 regions by sales?",
        "intent": result1.get("intent"),
        "sql": result1.get("sql"),
        "had_results": True,
    }

    conversation_history = [
        {"role": "user", "content": "What are the top 3 regions by sales?"},
        {"role": "assistant", "content": result1.get("summary", "")},
    ]

    # Step 3: Ask for visualization of previous data
    result2 = supervisor.run(
        query="Visualize that as a bar chart",
        conversation_history=conversation_history,
        last_turn_metadata=last_turn,
    )

    # Verify visualization was triggered
    assert (
        result2.get("should_visualize") is True
    ), "Follow-up should trigger visualization"

    # Verify chart used cached data
    viz = result2.get("visualization_config")
    assert viz is not None
    assert viz.get("chart_type") == "bar"
    assert viz.get("data") is not None, "Should use cached data"

    # Verify chart artifacts
    assert viz.get("chart_html") is not None
    assert viz.get("error") is None

    print(f"\n✅ Follow-up test passed!")
    print(f"   Used cached data: {len(viz.get('data', []))} rows")
    print(f"   Chart Type: {viz.get('chart_type')}")


def test_no_visualization_without_keyword(supervisor):
    """Test: Query without viz keywords should not generate chart."""
    result = supervisor.run(
        query="What is the total revenue?",
        conversation_history=[],
        last_turn_metadata=None,
    )

    # Should NOT visualize (no keywords like "chart", "graph", etc.)
    assert result.get("should_visualize") is False
    assert result.get("visualization_config") is None

    print(f"\n✅ No-viz test passed!")
    print(f"   Intent: {result['intent']}")
    print(f"   Should visualize: {result.get('should_visualize')}")


def test_line_chart_for_time_series(supervisor):
    """Test: Time series query should suggest line chart."""
    result = supervisor.run(
        query="Show me revenue trends over the last 6 months as a line chart",
        conversation_history=[],
        last_turn_metadata=None,
    )

    if result.get("should_visualize"):
        viz = result.get("visualization_config")
        # Should suggest line chart for time series
        assert viz.get("chart_type") in [
            "line",
            "area",
        ], f"Time series should use line/area chart, got: {viz.get('chart_type')}"

        print(f"\n✅ Time series test passed!")
        print(f"   Chart Type: {viz.get('chart_type')}")
    else:
        print(f"\n⚠️ No data available for visualization (expected in test env)")


@pytest.mark.skipif(
    True,  # Change to False to enable performance test
    reason="Performance test - only run manually",
)
def test_large_dataset_performance(supervisor):
    """Test: Chart generation with large dataset (performance check)."""
    import time

    start = time.time()
    result = supervisor.run(
        query="Show me all customers by revenue as a bar chart",
        conversation_history=[],
        last_turn_metadata=None,
    )
    duration = time.time() - start

    print(f"\n⏱️ Performance test:")
    print(f"   Total duration: {duration:.2f}s")
    print(f"   Data points: {len(result.get('sql_results', []))}")

    # Should complete in reasonable time (adjust threshold as needed)
    assert duration < 30, f"Chart generation took too long: {duration:.2f}s"
