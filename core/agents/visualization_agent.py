"""
Visualization Agent - Determines if and how to visualize data.

This agent:
1. Detects visualization intent from user queries
2. Suggests appropriate chart types using LLM
3. Generates actual chart artifacts via ChartGeneratorTool
4. Handles both simultaneous and follow-up visualization requests
5. RESPECTS user's explicit chart type preferences
"""

import json
import re
from typing import Any, Dict, List, Optional

from groq import Groq

from config.settings import settings
from core.agents.base_agent import BaseAgent
from core.tools.chart_generator_tool import ChartGeneratorTool

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

            # Step 0: Check if user explicitly requested a chart type
            user_requested_type = self._extract_user_chart_preference(query)

            # Step 1: Prepare data for chart (aggregate if needed for pie charts)
            prepared_data, override_message = self._prepare_data_for_chart(
                data_to_visualize, user_requested_type, query
            )

            # Step 2: Ask LLM what chart type to use (but respect user preference)
            viz_suggestion = self._suggest_visualization(
                query, prepared_data, user_requested_type
            )

            if not viz_suggestion or viz_suggestion.get("chart_type") == "none":
                return self._create_response(
                    success=True, result={"should_visualize": False, "viz_config": None}
                )

            # Step 3: Generate the actual chart using the tool
            chart_result = self.chart_tool.generate_chart(
                chart_type=viz_suggestion["chart_type"],
                data=prepared_data,
                x=viz_suggestion["x"],
                y=viz_suggestion["y"],
                title=None,  # Auto-generated
                theme=settings.CHART_DEFAULT_THEME,
            )

            # Step 4: Build final viz_config with chart artifacts
            viz_config = {
                "chart_type": viz_suggestion["chart_type"],
                "x": viz_suggestion["x"],
                "y": viz_suggestion["y"],
                "data": prepared_data,
                "chart_html": chart_result.get("chart_html"),
                "chart_base64": chart_result.get("chart_base64"),
                "chart_json": chart_result.get("chart_json"),
                "theme": settings.CHART_DEFAULT_THEME,
                "error": chart_result.get("error"),  # Pass through any errors
                "override_message": override_message,  # Tell user if we changed something
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
                    user_requested=user_requested_type,
                    data_prepared=len(prepared_data) != len(data_to_visualize),
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

    def _extract_user_chart_preference(self, query: str) -> Optional[str]:
        """
        Extract explicit chart type from user query.

        Examples:
            "show me a pie chart" -> "pie"
            "visualize on a bar graph" -> "bar"
            "plot this as a line chart" -> "line"

        Returns:
            Chart type string or None if no explicit preference
        """
        query_lower = query.lower()

        # Check for explicit chart type mentions
        chart_type_patterns = {
            "pie": ["pie chart", "pie graph", "donut chart"],
            "bar": ["bar chart", "bar graph", "column chart"],
            "line": ["line chart", "line graph", "time series"],
            "area": ["area chart", "area graph", "stacked area"],
        }

        for chart_type, patterns in chart_type_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                self.logger.info(
                    "user_chart_preference_detected",
                    chart_type=chart_type,
                    query=query[:100],
                )
                return chart_type

        return None

    def _prepare_data_for_chart(
        self, data: List[Dict[str, Any]], chart_type: Optional[str], query: str
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Prepare data for visualization, aggregating if necessary.

        For pie charts with too many data points, aggregate to make readable.

        Returns:
            (prepared_data, override_message)
        """
        override_message = None

        # Only aggregate for pie charts
        if chart_type != "pie":
            return data, None

        # If too many data points for a pie chart, aggregate
        if len(data) > 30:
            self.logger.warning(
                "too_many_data_points_for_pie",
                original_count=len(data),
                action="attempting_aggregation",
            )

            # Try to intelligently aggregate
            aggregated_data = self._aggregate_for_pie_chart(data, query)

            if aggregated_data and len(aggregated_data) < len(data):
                override_message = (
                    f"📊 Note: Data aggregated for pie chart readability "
                    f"({len(data)} → {len(aggregated_data)} categories). "
                    f"Original data had {len(data)} rows which would make "
                    f"a pie chart unreadable."
                )
                self.logger.info(
                    "data_aggregated_for_pie",
                    original_count=len(data),
                    aggregated_count=len(aggregated_data),
                )
                return aggregated_data, override_message

        return data, None

    def _aggregate_for_pie_chart(
        self, data: List[Dict[str, Any]], query: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Intelligently aggregate data for pie chart display.

        Strategy:
        1. Identify the grouping column (categorical)
        2. Identify the value column (numeric)
        3. Group by the categorical column and sum values
        4. Keep top N categories, combine rest as "Others"
        """
        try:
            import pandas as pd

            df = pd.DataFrame(data)

            # Find categorical and numeric columns
            categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            if not categorical_cols or not numeric_cols:
                return None

            # Use first categorical and first numeric column
            # (LLM will suggest better ones in _suggest_visualization)
            group_col = categorical_cols[0]
            value_col = numeric_cols[0]

            # Aggregate by the categorical column
            aggregated = df.groupby(group_col)[value_col].sum().reset_index()

            # Sort by value descending
            aggregated = aggregated.sort_values(value_col, ascending=False)

            # Keep top 15, combine rest as "Others"
            TOP_N = 15

            if len(aggregated) > TOP_N:
                top_n = aggregated.head(TOP_N)
                others_sum = aggregated.iloc[TOP_N:][value_col].sum()

                if others_sum > 0:
                    others_row = pd.DataFrame(
                        [{group_col: "Others", value_col: others_sum}]
                    )
                    aggregated = pd.concat([top_n, others_row], ignore_index=True)
                else:
                    aggregated = top_n

            return aggregated.to_dict("records")

        except Exception as e:
            self.logger.warning("aggregation_failed", error=str(e))
            return None

    def _suggest_visualization(
        self,
        query: str,
        sql_results: List[Dict[str, Any]],
        user_preference: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to suggest appropriate chart type based on query and data.

        Args:
            query: User's query
            sql_results: Data to visualize
            user_preference: User's explicit chart type preference (overrides LLM)

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

        # Build preference instruction
        preference_instruction = ""
        if user_preference:
            preference_instruction = f"""
⚠️ CRITICAL: User explicitly requested a "{user_preference.upper()}" chart.
You MUST use chart_type: "{user_preference}" in your response.
This overrides all other considerations.
"""

        prompt = f"""Analyze the data and suggest the best chart type.

Question: {query}
{preference_instruction}

Available Columns: {", ".join(columns)}

Sample Data (first 5 rows):
{json.dumps(sample, indent=2, default=str)}

RULES:
1. Choose "bar" for categorical comparisons (e.g., sales by region, count by status)
2. Choose "line" for time series or trends over time (look for date columns)
3. Choose "pie" for proportions/percentages or parts-of-whole relationships
4. Choose "area" for cumulative trends or stacked time series
5. Choose "none" if the data is not suitable for visualization (e.g., single value, text-heavy)

6. Select ONE column for x-axis (categorical or temporal)
7. Select ONE column for y-axis (numeric)
8. Ensure selected columns exist in the data

{preference_instruction}

Return ONLY valid JSON:
{{
    "chart_type": "{user_preference if user_preference else "bar | line | pie | area | none"}",
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
                        "content": "You are a data visualization expert. Respond only with valid JSON. Always respect user's explicit chart type preferences.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,  # Deterministic
            )

            result = json.loads(response.choices[0].message.content)

            # Force user preference if provided
            if user_preference and result.get("chart_type") != user_preference:
                self.logger.warning(
                    "llm_ignored_user_preference",
                    user_requested=user_preference,
                    llm_suggested=result.get("chart_type"),
                    action="forcing_user_preference",
                )
                result["chart_type"] = user_preference

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

            self.logger.info(
                "viz_suggestion_generated",
                chart_type=result.get("chart_type"),
                x=result.get("x"),
                y=result.get("y"),
                user_preference=user_preference,
            )

            return result

        except Exception as e:
            self.logger.error("viz_suggestion_failed", error=str(e))
            return None
