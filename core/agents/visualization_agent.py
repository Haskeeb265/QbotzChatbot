"""
Visualization Agent - Determines if and how to visualize data.

This agent:
1. Detects visualization intent from user queries
2. Suggests appropriate chart types using LLM
3. Generates actual chart artifacts via ChartGeneratorTool
4. Handles both simultaneous and follow-up visualization requests
"""

from typing import Dict, Any, Optional, List
import json

from groq import Groq
from core.agents.base_agent import BaseAgent
from core.tools.chart_generator_tool import ChartGeneratorTool
from config.settings import settings


# Visualization keywords for detection
VIZ_KEYWORDS = [
    "graph",
    "chart",
    "plot",
    "illustrate",
    "visualize",
    "show me a",
    "draw",
    "display",
    "bar chart",
    "line chart",
    "pie chart",
    "histogram",
    "scatter",
    "visualization",
    "bar graph",
    "line graph",
    "pie graph",
    "trend",  # Added - time series indicator
    "over time",  # Added - time series indicator
]


class VisualizationAgent(BaseAgent):
    """
    Determines if a visualization should be generated and creates it.

    Handles two scenarios:
    1. Simultaneous: User asks for chart in the same query as the question
    2. Follow-up: User asks for chart after receiving textual answer

    Now also generates the actual chart using ChartGeneratorTool.
    """

    def __init__(self):
        super().__init__("visualization_agent")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
        self.chart_tool = ChartGeneratorTool()  # ← NEW: Own the chart generator

    def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze query and data to determine visualization config, then generate chart.

        Args:
            query: User's question
            context: {
                "sql_results": List[Dict] - Data to visualize
                "is_follow_up": bool - Whether this is a follow-up request
                "last_turn_metadata": Dict - Previous turn metadata
            }

        Returns:
            {
                "success": bool,
                "result": {
                    "should_visualize": bool,
                    "viz_config": VisualizationConfig | None
                }
            }
        """
        try:
            context = context or {}
            sql_results = context.get("sql_results")
            is_follow_up = context.get("is_follow_up", False)
            last_turn_metadata = context.get("last_turn_metadata")

            # Check if user wants visualization
            wants_viz = self._detect_viz_intent(query)

            # If no viz requested, return early
            if not wants_viz:
                return self._create_response(
                    success=True, result={"should_visualize": False, "viz_config": None}
                )

            # Try to get data from multiple sources:
            # 1. Current SQL results (simultaneous request)
            # 2. Cached results from last turn (follow-up request)
            data_to_visualize = None

            if sql_results and len(sql_results) > 0:
                # Use current results (simultaneous request)
                data_to_visualize = sql_results
                self.logger.info("using_current_results", result_count=len(sql_results))
            elif last_turn_metadata and last_turn_metadata.get("sql_results"):
                # Use cached results (follow-up request)
                data_to_visualize = last_turn_metadata["sql_results"]
                self.logger.info(
                    "using_cached_results",
                    result_count=len(data_to_visualize),
                    reason="no_current_results",
                )

            # No visualization if no data available
            if not data_to_visualize or len(data_to_visualize) == 0:
                self.logger.warning(
                    "no_data_for_visualization",
                    has_current_results=bool(sql_results),
                    has_cached_results=bool(
                        last_turn_metadata and last_turn_metadata.get("sql_results")
                    ),
                )
                return self._create_response(
                    success=True, result={"should_visualize": False, "viz_config": None}
                )

            # Step 1: Ask LLM what chart type to use
            viz_suggestion = self._suggest_visualization(query, data_to_visualize)

            if not viz_suggestion or viz_suggestion.get("chart_type") == "none":
                return self._create_response(
                    success=True, result={"should_visualize": False, "viz_config": None}
                )

            # Step 2: Generate the actual chart using the tool
            chart_result = self.chart_tool.generate_chart(
                chart_type=viz_suggestion["chart_type"],
                data=data_to_visualize,
                x=viz_suggestion["x"],
                y=viz_suggestion["y"],
                title=None,  # Auto-generated
                theme=settings.CHART_DEFAULT_THEME,
            )

            # Step 3: Build final viz_config with chart artifacts
            viz_config = {
                "chart_type": viz_suggestion["chart_type"],
                "x": viz_suggestion["x"],
                "y": viz_suggestion["y"],
                "data": data_to_visualize,
                "chart_html": chart_result.get("chart_html"),
                "chart_base64": chart_result.get("chart_base64"),
                "chart_json": chart_result.get("chart_json"),
                "theme": settings.CHART_DEFAULT_THEME,
                "error": chart_result.get("error"),  # Pass through any errors
            }

            # Log result
            if chart_result["success"]:
                self.logger.info(
                    "visualization_generated",
                    chart_type=viz_config["chart_type"],
                    x=viz_config["x"],
                    y=viz_config["y"],
                    has_html=bool(viz_config["chart_html"]),
                    has_static=bool(viz_config["chart_base64"]),
                )
            else:
                self.logger.warning(
                    "chart_generation_failed_but_continuing", error=viz_config["error"]
                )

            return self._create_response(
                success=True,
                result={
                    "should_visualize": chart_result[
                        "success"
                    ],  # Only true if chart actually generated
                    "viz_config": viz_config,
                },
            )

        except Exception as e:
            return self._handle_error(e, query)

    def _detect_viz_intent(self, query: str) -> bool:
        """Check if query contains visualization keywords."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in VIZ_KEYWORDS)

    def _suggest_visualization(
        self, query: str, sql_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to suggest appropriate chart type based on query and data.

        Returns:
            {
                "chart_type": "bar" | "line" | "pie" | "area" | "none",
                "x": "column_name",
                "y": "column_name"
            }
        """
        if not sql_results or len(sql_results) == 0:
            return None

        # Get sample data and column info
        sample = sql_results[:5]
        columns = list(sql_results[0].keys())

        prompt = f"""Analyze the data and suggest the best chart type.

Question: {query}

Available Columns: {", ".join(columns)}

Sample Data (first 5 rows):
{json.dumps(sample, indent=2, default=str)}

RULES:
1. Choose "bar" for categorical comparisons (e.g., sales by region, count by status)
2. Choose "line" for time series or trends over time (look for date columns)
3. Choose "pie" for proportions/percentages (only if data shows parts of a whole)
4. Choose "area" for cumulative trends or stacked time series
5. Choose "none" if the data is not suitable for visualization (e.g., single value, text-heavy)

6. Select ONE column for x-axis (categorical or temporal)
7. Select ONE column for y-axis (numeric)
8. Ensure selected columns exist in the data

Return ONLY valid JSON:
{{
    "chart_type": "bar" | "line" | "pie" | "area" | "none",
    "x": "column_name",
    "y": "column_name"
}}
"""

        try:
            response = self.llm.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data visualization expert. Respond only with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,  # Deterministic
            )

            result = json.loads(response.choices[0].message.content)

            # Validate suggested columns exist
            if result.get("chart_type") != "none":
                if result.get("x") not in columns or result.get("y") not in columns:
                    self.logger.warning(
                        "invalid_column_suggestion",
                        suggested_x=result.get("x"),
                        suggested_y=result.get("y"),
                        available=columns,
                    )
                    return {"chart_type": "none"}

            return result

        except Exception as e:
            self.logger.error("viz_suggestion_failed", error=str(e))
            return None
