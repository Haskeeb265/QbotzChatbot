"""Unit tests for ChartGeneratorTool."""

import pytest
from core.tools.chart_generator_tool import ChartGeneratorTool


@pytest.fixture
def sample_data():
    return [
        {"region": "EAST", "sales": 50000},
        {"region": "WEST", "sales": 38000},
        {"region": "NORTH", "sales": 42000},
    ]


def test_generate_bar_chart(sample_data):
    tool = ChartGeneratorTool()
    result = tool.generate_chart(
        chart_type="bar", data=sample_data, x="region", y="sales"
    )

    assert result["success"] is True
    assert result["chart_type"] == "bar"
    assert result["chart_html"] is not None
    assert "plotly" in result["chart_html"].lower()


def test_invalid_column_name(sample_data):
    tool = ChartGeneratorTool()
    result = tool.generate_chart(
        chart_type="bar", data=sample_data, x="invalid_column", y="sales"
    )

    assert result["success"] is False
    assert "not found" in result["error"]


def test_empty_data():
    tool = ChartGeneratorTool()
    result = tool.generate_chart(chart_type="bar", data=[], x="region", y="sales")

    assert result["success"] is False
