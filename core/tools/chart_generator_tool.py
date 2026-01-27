"""
Professional chart generator using Plotly Express.

This tool converts structured data into interactive, publication-quality charts.
Supports multiple chart types (bar, line, pie, area) with consistent styling.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO

from config.settings import settings
from utility.observability.logger import get_logger

logger = get_logger("chart_generator_tool")


class ChartGeneratorTool:
    """
    Generates professional interactive charts using Plotly.

    Features:
    - Multiple chart types (bar, line, pie, area)
    - Interactive HTML output for web
    - Static PNG export for API/mobile
    - Consistent professional styling
    - Automatic value formatting
    """

    # Professional color palettes
    COLOR_SCHEMES = {
        "vibrant": px.colors.qualitative.Vivid,
        "professional": px.colors.qualitative.Safe,
        "default": px.colors.qualitative.Plotly,
    }

    def __init__(self):
        """Initialize chart generator with settings from config."""
        self.default_theme = settings.CHART_DEFAULT_THEME
        self.default_width = settings.CHART_DEFAULT_WIDTH
        self.default_height = settings.CHART_DEFAULT_HEIGHT
        self.image_scale = settings.CHART_IMAGE_SCALE
        self.enable_static_export = settings.CHART_ENABLE_STATIC_EXPORT

        logger.info(
            "chart_tool_initialized",
            theme=self.default_theme,
            static_export=self.enable_static_export,
        )

    def generate_chart(
        self,
        chart_type: str,
        data: List[Dict[str, Any]],
        x: str,
        y: str,
        title: Optional[str] = None,
        color_by: Optional[str] = None,
        theme: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate interactive chart from structured data.

        Args:
            chart_type: One of 'bar', 'line', 'pie', 'area'
            data: List of dictionaries with chart data
            x: Column name for x-axis (categorical or temporal)
            y: Column name for y-axis (numeric values)
            title: Chart title (auto-generated if None)
            color_by: Optional column to group/color by
            theme: Visual theme (uses config default if None)

        Returns:
            {
                "success": bool,
                "chart_html": str,           # Interactive HTML
                "chart_base64": str | None,  # PNG image (base64)
                "chart_json": dict,          # Plotly JSON spec
                "chart_type": str,
                "error": str | None
            }

        Examples:
            >>> tool = ChartGeneratorTool()
            >>> result = tool.generate_chart(
            ...     chart_type="bar",
            ...     data=[{"region": "EAST", "sales": 50000}, ...],
            ...     x="region",
            ...     y="sales"
            ... )
            >>> result["success"]
            True
        """
        logger.info(
            "chart_generation_started",
            chart_type=chart_type,
            data_points=len(data),
            x_col=x,
            y_col=y,
        )

        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Validate columns exist
            if x not in df.columns:
                raise ValueError(
                    f"Column '{x}' not found in data. Available: {list(df.columns)}"
                )
            if y not in df.columns:
                raise ValueError(
                    f"Column '{y}' not found in data. Available: {list(df.columns)}"
                )

            # Auto-generate title if not provided
            if not title:
                title = f"{self._format_label(y)} by {self._format_label(x)}"

            # Use provided theme or default
            theme = theme or self.default_theme

            # Generate appropriate chart
            fig = self._create_figure(
                chart_type=chart_type,
                df=df,
                x=x,
                y=y,
                title=title,
                color_by=color_by,
                theme=theme,
            )

            # Apply professional styling
            self._apply_styling(fig, chart_type)

            # Generate outputs
            chart_html = self._generate_html(fig)
            chart_base64 = (
                self._generate_static_image(fig) if self.enable_static_export else None
            )
            chart_json = fig.to_dict()

            logger.info(
                "chart_generated_successfully",
                chart_type=chart_type,
                has_static=bool(chart_base64),
            )

            return {
                "success": True,
                "chart_html": chart_html,
                "chart_base64": chart_base64,
                "chart_json": chart_json,
                "chart_type": chart_type,
                "error": None,
            }

        except Exception as e:
            logger.error(
                "chart_generation_failed",
                chart_type=chart_type,
                error=str(e),
                error_type=type(e).__name__,
            )

            return {
                "success": False,
                "chart_html": None,
                "chart_base64": None,
                "chart_json": None,
                "chart_type": chart_type,
                "error": f"Chart generation failed: {str(e)}",
            }

    def _create_figure(
        self,
        chart_type: str,
        df: pd.DataFrame,
        x: str,
        y: str,
        title: str,
        color_by: Optional[str],
        theme: str,
    ) -> go.Figure:
        """Create Plotly figure based on chart type."""

        labels = {x: self._format_label(x), y: self._format_label(y)}

        if chart_type == "bar":
            fig = px.bar(
                df,
                x=x,
                y=y,
                color=color_by,
                title=title,
                labels=labels,
                template=theme,
                color_discrete_sequence=self.COLOR_SCHEMES["vibrant"],
            )
            # Add value labels on bars
            fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")

        elif chart_type == "line":
            fig = px.line(
                df,
                x=x,
                y=y,
                color=color_by,
                title=title,
                labels=labels,
                markers=True,  # Add dots on data points
                template=theme,
                color_discrete_sequence=self.COLOR_SCHEMES["vibrant"],
            )
            # Smooth line for better aesthetics
            fig.update_traces(line_shape="spline")

        elif chart_type == "pie":
            fig = px.pie(
                df,
                names=x,
                values=y,
                title=title,
                hole=0.4,  # Donut chart - more modern look
                template=theme,
                color_discrete_sequence=self.COLOR_SCHEMES["vibrant"],
            )
            # Show percentages inside slices
            fig.update_traces(textposition="inside", textinfo="percent+label")

        elif chart_type == "area":
            fig = px.area(
                df,
                x=x,
                y=y,
                color=color_by,
                title=title,
                labels=labels,
                template=theme,
                color_discrete_sequence=self.COLOR_SCHEMES["vibrant"],
            )

        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        return fig

    def _apply_styling(self, fig: go.Figure, chart_type: str) -> None:
        """Apply professional styling to figure."""
        fig.update_layout(
            # Better hover tooltips
            hovermode="x unified" if chart_type != "pie" else "closest",
            # Font styling
            font=dict(size=12, family="Arial, sans-serif"),
            title_font_size=18,
            # Background
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent
            # Size
            height=self.default_height,
            # Margins
            margin=dict(l=50, r=50, t=80, b=50),
            # Make responsive
            autosize=True,
            # Legend
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

    def _generate_html(self, fig: go.Figure) -> str:
        """Generate interactive HTML with Plotly controls."""
        return fig.to_html(
            include_plotlyjs="cdn",
            config={
                "displayModeBar": True,
                "displaylogo": False,  # Remove Plotly logo
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "chart",
                    "height": self.default_height,
                    "width": self.default_width,
                    "scale": self.image_scale,
                },
            },
        )

    def _generate_static_image(self, fig: go.Figure) -> Optional[str]:
        """Generate static PNG image as base64."""
        try:
            img_bytes = fig.to_image(
                format="png",
                width=self.default_width,
                height=self.default_height,
                scale=self.image_scale,
            )
            base64_str = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{base64_str}"
        except Exception as e:
            logger.warning("static_image_generation_failed", error=str(e))
            return None

    def _format_label(self, column_name: str) -> str:
        """Format column name for display (snake_case → Title Case)."""
        return column_name.replace("_", " ").title()


# ===== Public API (for direct tool usage) =====


def generate_chart(
    chart_type: str, data: List[Dict[str, Any]], x: str, y: str, **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for generating charts.

    This is the main entry point when using the tool directly.

    Usage:
        >>> from core.tools.chart_generator_tool import generate_chart
        >>> result = generate_chart("bar", data, x="region", y="sales")
    """
    tool = ChartGeneratorTool()
    return tool.generate_chart(chart_type, data, x, y, **kwargs)
