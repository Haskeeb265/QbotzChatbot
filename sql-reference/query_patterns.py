"""
SQL Query Patterns Reference
=============================

This file contains standardized query patterns translated from SAP VBRK schema
to the current sales_orders schema. These serve as REFERENCE PATTERNS for the
SQL agent to learn from, NOT as exact queries to copy.

Field Mapping:
SAP Field (VBRK)        →  sales_orders Field
-----------------          ---------------------
VBRK-FKDAT             →  sales_order_date
VBRK-VBELN             →  sales_order
VBRK-FKART             →  sales_document_type
VBRK-VKORG             →  sales_organization
VBRK-VTWEG             →  distribution_channel
VBRK-REGIO             →  sales_district
VBRK-KUNAG             →  sold_to_party
VBRK-NETWR             →  total_net_amount
VBRK-FKSTO             →  billing_block_status
"""

# ============================================================================
# QUERY PATTERN TEMPLATES
# ============================================================================

QUERY_PATTERNS = {
    "01_time_series_trend": {
        "description": "Time-based aggregation with trending (monthly/quarterly)",
        "pattern": """
SELECT 
    DATE_TRUNC('month', {date_column}) as period,
    SUM({amount_column}) as total_revenue,
    COUNT({id_column}) as document_count,
    AVG({amount_column}) as avg_per_document
FROM {table}
WHERE {date_column} >= {start_date}
  AND {date_column} < {end_date}
  {optional_filters}
GROUP BY DATE_TRUNC('month', {date_column})
ORDER BY period DESC
LIMIT 1000;
""",
        "use_cases": [
            "monthly sales trend",
            "quarterly revenue",
            "time series analysis",
            "trending over time",
        ],
    },
    "02_highest_lowest_by_dimension": {
        "description": "Find top/bottom performers by a dimension (region, customer, etc.)",
        "pattern": """
WITH aggregated AS (
    SELECT 
        {dimension_column},
        SUM({amount_column}) as total_revenue,
        COUNT({id_column}) as document_count,
        AVG({amount_column}) as avg_revenue
    FROM {table}
    WHERE {date_filter}
      {optional_filters}
    GROUP BY {dimension_column}
)
SELECT 
    {dimension_column},
    total_revenue,
    document_count,
    avg_revenue
FROM aggregated
ORDER BY total_revenue {DESC/ASC}
LIMIT {top_n};
""",
        "use_cases": [
            "top N customers",
            "highest revenue region",
            "lowest performing channel",
            "best/worst performers",
        ],
    },
    "03_contribution_analysis": {
        "description": "Calculate percentage contribution to total",
        "pattern": """
WITH total AS (
    SELECT SUM({amount_column}) as total_revenue
    FROM {table}
    WHERE {date_filter}
),
by_dimension AS (
    SELECT 
        {dimension_column},
        SUM({amount_column}) as dimension_revenue
    FROM {table}
    WHERE {date_filter}
    GROUP BY {dimension_column}
)
SELECT 
    b.{dimension_column},
    b.dimension_revenue,
    t.total_revenue,
    (b.dimension_revenue / NULLIF(t.total_revenue, 0) * 100) as contribution_pct
FROM by_dimension b
CROSS JOIN total t
ORDER BY contribution_pct DESC
LIMIT 1000;
""",
        "use_cases": [
            "revenue contribution by sales org",
            "percentage share by region",
            "contribution analysis",
        ],
    },
    "04_category_performance": {
        "description": "Performance metrics grouped by category (billing type, product type, etc.)",
        "pattern": """
SELECT 
    {category_column},
    SUM({amount_column}) as total_revenue,
    COUNT({id_column}) as document_count,
    AVG({amount_column}) as avg_value,
    MIN({amount_column}) as min_value,
    MAX({amount_column}) as max_value
FROM {table}
WHERE {date_filter}
  {optional_filters}
GROUP BY {category_column}
ORDER BY total_revenue DESC
LIMIT 1000;
""",
        "use_cases": [
            "billing type performance",
            "product mix analysis",
            "category breakdown",
        ],
    },
    "05_multi_dimensional_breakdown": {
        "description": "Cross-tabulation by multiple dimensions",
        "pattern": """
SELECT 
    {dimension1_column},
    {dimension2_column},
    {dimension3_column},
    SUM({amount_column}) as total_revenue,
    COUNT({id_column}) as document_count,
    AVG({amount_column}) as avg_revenue
FROM {table}
WHERE {date_filter}
  {optional_filters}
GROUP BY {dimension1_column}, {dimension2_column}, {dimension3_column}
ORDER BY total_revenue DESC
LIMIT 1000;
""",
        "use_cases": [
            "billing type by region and channel",
            "multi-dimensional segmentation",
            "cross-tabulation",
        ],
    },
    "06_customer_ranking": {
        "description": "Rank customers by total value with aggregations",
        "pattern": """
SELECT 
    {customer_column},
    SUM({amount_column}) as total_revenue,
    COUNT({id_column}) as order_count,
    AVG({amount_column}) as avg_order_value,
    MIN({date_column}) as first_order_date,
    MAX({date_column}) as last_order_date
FROM {table}
WHERE {date_filter}
  {optional_filters}
GROUP BY {customer_column}
ORDER BY total_revenue DESC
LIMIT {top_n};
""",
        "use_cases": ["top customers", "customer lifetime value", "customer ranking"],
    },
    "07_average_deal_size": {
        "description": "Average metrics per entity across dimensions",
        "pattern": """
SELECT 
    {dimension_column},
    AVG({amount_column}) as avg_deal_size,
    COUNT({id_column}) as total_deals,
    SUM({amount_column}) as total_revenue,
    STDDEV({amount_column}) as revenue_stddev
FROM {table}
WHERE {date_filter}
  {optional_filters}
GROUP BY {dimension_column}
ORDER BY avg_deal_size DESC
LIMIT 1000;
""",
        "use_cases": [
            "average deal size by customer",
            "average value per region",
            "deal size analysis",
        ],
    },
    "08_high_volume_low_value": {
        "description": "Identify areas with high transaction count but low average value",
        "pattern": """
WITH metrics AS (
    SELECT 
        {dimension_column},
        COUNT({id_column}) as transaction_count,
        AVG({amount_column}) as avg_value,
        SUM({amount_column}) as total_revenue
    FROM {table}
    WHERE {date_filter}
      {optional_filters}
    GROUP BY {dimension_column}
)
SELECT 
    {dimension_column},
    transaction_count,
    avg_value,
    total_revenue
FROM metrics
WHERE transaction_count > {volume_threshold}
  AND avg_value < {value_threshold}
ORDER BY transaction_count DESC
LIMIT 1000;
""",
        "use_cases": [
            "high volume low value areas",
            "efficiency analysis",
            "opportunity detection",
        ],
    },
    "09_period_comparison": {
        "description": "Compare metrics between two time periods",
        "pattern": """
WITH current_period AS (
    SELECT 
        {dimension_column},
        SUM({amount_column}) as current_revenue,
        COUNT({id_column}) as current_count
    FROM {table}
    WHERE {date_column} >= {current_start}
      AND {date_column} < {current_end}
    GROUP BY {dimension_column}
),
previous_period AS (
    SELECT 
        {dimension_column},
        SUM({amount_column}) as previous_revenue,
        COUNT({id_column}) as previous_count
    FROM {table}
    WHERE {date_column} >= {previous_start}
      AND {date_column} < {previous_end}
    GROUP BY {dimension_column}
)
SELECT 
    COALESCE(c.{dimension_column}, p.{dimension_column}) as dimension,
    c.current_revenue,
    p.previous_revenue,
    (c.current_revenue - p.previous_revenue) as revenue_change,
    ((c.current_revenue - p.previous_revenue) / NULLIF(p.previous_revenue, 0) * 100) as pct_change
FROM current_period c
FULL OUTER JOIN previous_period p ON c.{dimension_column} = p.{dimension_column}
ORDER BY pct_change {ASC/DESC}
LIMIT 1000;
""",
        "use_cases": [
            "declining regions",
            "growth analysis",
            "period over period comparison",
            "historical vs current",
        ],
    },
    "10_growth_opportunities": {
        "description": "Find opportunities: high value but low volume",
        "pattern": """
WITH metrics AS (
    SELECT 
        {dimension_column},
        COUNT({id_column}) as transaction_count,
        AVG({amount_column}) as avg_value,
        SUM({amount_column}) as total_revenue
    FROM {table}
    WHERE {date_filter}
      {optional_filters}
    GROUP BY {dimension_column}
)
SELECT 
    {dimension_column},
    transaction_count,
    avg_value,
    total_revenue,
    (avg_value * {expected_volume}) as potential_revenue
FROM metrics
WHERE avg_value > {high_value_threshold}
  AND transaction_count < {low_volume_threshold}
ORDER BY avg_value DESC
LIMIT 1000;
""",
        "use_cases": [
            "revenue growth opportunities",
            "untapped potential",
            "high value low volume",
        ],
    },
}

# ============================================================================
# FEW-SHOT EXAMPLES (Concrete Questions → SQL)
# ============================================================================

FEW_SHOT_EXAMPLES = [
    {
        "question": "How is total net sales trending monthly over the last year?",
        "sql": """
SELECT 
    DATE_TRUNC('month', sales_order_date) as period,
    SUM(total_net_amount) as total_revenue,
    COUNT(sales_order) as order_count,
    AVG(total_net_amount) as avg_per_order
FROM sales_orders
WHERE sales_order_date >= CURRENT_DATE - INTERVAL '12 months'
  AND sales_order_date < CURRENT_DATE
GROUP BY DATE_TRUNC('month', sales_order_date)
ORDER BY period DESC
LIMIT 1000;
""",
        "pattern_used": "01_time_series_trend",
    },
    {
        "question": "Which sales regions are generating the highest net revenue?",
        "sql": """
SELECT 
    sales_district,
    SUM(total_net_amount) as total_revenue,
    COUNT(sales_order) as order_count,
    AVG(total_net_amount) as avg_revenue
FROM sales_orders
WHERE sales_order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY sales_district
ORDER BY total_revenue DESC
LIMIT 10;
""",
        "pattern_used": "02_highest_lowest_by_dimension",
    },
    {
        "question": "Which sales organizations contribute most to overall revenue?",
        "sql": """
WITH total AS (
    SELECT SUM(total_net_amount) as total_revenue
    FROM sales_orders
    WHERE sales_order_date >= CURRENT_DATE - INTERVAL '12 months'
),
by_org AS (
    SELECT 
        sales_organization,
        SUM(total_net_amount) as org_revenue
    FROM sales_orders
    WHERE sales_order_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY sales_organization
)
SELECT 
    b.sales_organization,
    b.org_revenue,
    t.total_revenue,
    (b.org_revenue / NULLIF(t.total_revenue, 0) * 100) as contribution_pct
FROM by_org b
CROSS JOIN total t
ORDER BY contribution_pct DESC
LIMIT 1000;
""",
        "pattern_used": "03_contribution_analysis",
    },
    {
        "question": "Who are the top 20 customers by total net value?",
        "sql": """
SELECT 
    sold_to_party,
    SUM(total_net_amount) as total_revenue,
    COUNT(sales_order) as order_count,
    AVG(total_net_amount) as avg_order_value,
    MIN(sales_order_date) as first_order,
    MAX(sales_order_date) as last_order
FROM sales_orders
WHERE sales_order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY sold_to_party
ORDER BY total_revenue DESC
LIMIT 20;
""",
        "pattern_used": "06_customer_ranking",
    },
    {
        "question": "Which regions show declining sales in the last 6 months compared to the previous 6 months?",
        "sql": """
WITH current_period AS (
    SELECT 
        sales_district,
        SUM(total_net_amount) as current_revenue,
        COUNT(sales_order) as current_count
    FROM sales_orders
    WHERE sales_order_date >= CURRENT_DATE - INTERVAL '6 months'
      AND sales_order_date < CURRENT_DATE
    GROUP BY sales_district
),
previous_period AS (
    SELECT 
        sales_district,
        SUM(total_net_amount) as previous_revenue,
        COUNT(sales_order) as previous_count
    FROM sales_orders
    WHERE sales_order_date >= CURRENT_DATE - INTERVAL '12 months'
      AND sales_order_date < CURRENT_DATE - INTERVAL '6 months'
    GROUP BY sales_district
)
SELECT 
    COALESCE(c.sales_district, p.sales_district) as district,
    c.current_revenue,
    p.previous_revenue,
    (c.current_revenue - p.previous_revenue) as revenue_change,
    ((c.current_revenue - p.previous_revenue) / NULLIF(p.previous_revenue, 0) * 100) as pct_change
FROM current_period c
FULL OUTER JOIN previous_period p ON c.sales_district = p.sales_district
WHERE c.current_revenue < p.previous_revenue
ORDER BY pct_change ASC
LIMIT 1000;
""",
        "pattern_used": "09_period_comparison",
    },
]

# ============================================================================
# HELPER FUNCTION TO FORMAT FOR LLM PROMPT
# ============================================================================


def get_few_shot_examples_text(max_examples: int = 5) -> str:
    """
    Format few-shot examples as text for inclusion in LLM prompt.

    Args:
        max_examples: Maximum number of examples to include

    Returns:
        Formatted string with example questions and SQL
    """
    examples_text = ["REFERENCE EXAMPLES (Learn the patterns, don't copy directly):"]
    examples_text.append("")

    for i, example in enumerate(FEW_SHOT_EXAMPLES[:max_examples], 1):
        examples_text.append(f"EXAMPLE {i}:")
        examples_text.append(f'Question: "{example["question"]}"')
        examples_text.append(f'Pattern: {example["pattern_used"]}')
        examples_text.append("SQL:")
        examples_text.append(example["sql"].strip())
        examples_text.append("")

    return "\n".join(examples_text)


def get_pattern_descriptions() -> str:
    """
    Get a summary of all available query patterns.

    Returns:
        Formatted string describing each pattern
    """
    descriptions = ["AVAILABLE QUERY PATTERNS:"]
    descriptions.append("")

    for pattern_id, pattern_info in QUERY_PATTERNS.items():
        descriptions.append(f"• {pattern_id}: {pattern_info['description']}")
        descriptions.append(f"  Use for: {', '.join(pattern_info['use_cases'][:3])}")
        descriptions.append("")

    return "\n".join(descriptions)
