"""Date / Calendar Utility Tool.

Provides information about available dates, quarters, and time ranges in the dataset.
Queries: date_dim only.
"""

from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query


@tool
def get_date_info(
    info_type: str = "summary",
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get information about the available dates and time periods in the dataset.

    Use this tool to answer calendar-related questions like:
    - "What date range does the data cover?"
    - "What quarters are available?"
    - "How many weeks of data do we have in 2025?"

    Args:
        info_type: Type of information to return. One of:
            - 'summary': Overall date range, total days, and quarter list (default)
            - 'quarters': Breakdown of available quarters with date ranges
            - 'monthly': Monthly row counts (useful for data availability)
        year: Filter by year (e.g., 2024 or 2025). Optional.
        quarter: Filter by quarter ('Q1', 'Q2', 'Q3', 'Q4'). Optional.
    """
    try:
        if info_type == "summary":
            sql = """
            SELECT
                MIN(calendar_date) AS earliest_date,
                MAX(calendar_date) AS latest_date,
                COUNT(DISTINCT calendar_date) AS total_days,
                COUNT(DISTINCT year) AS total_years,
                COUNT(DISTINCT quarter) AS total_quarters,
                LIST(DISTINCT year ORDER BY year) AS years,
                LIST(DISTINCT quarter ORDER BY quarter) AS quarters
            FROM date_dim
            """
            if year:
                sql += f" WHERE year = {year}"

        elif info_type == "quarters":
            sql = """
            SELECT
                year,
                quarter,
                MIN(calendar_date) AS quarter_start,
                MAX(calendar_date) AS quarter_end,
                COUNT(DISTINCT calendar_date) AS days_in_quarter,
                COUNT(DISTINCT week_num) AS weeks_in_quarter
            FROM date_dim
            WHERE 1=1
            """
            if year:
                sql += f" AND year = {year}"
            if quarter:
                sql += f" AND quarter = '{quarter}'"
            sql += " GROUP BY year, quarter ORDER BY year, quarter"

        elif info_type == "monthly":
            sql = """
            SELECT
                year,
                quarter,
                MONTH(calendar_date) AS month_num,
                MIN(calendar_date) AS month_start,
                MAX(calendar_date) AS month_end,
                COUNT(*) AS day_count
            FROM date_dim
            WHERE 1=1
            """
            if year:
                sql += f" AND year = {year}"
            if quarter:
                sql += f" AND quarter = '{quarter}'"
            sql += " GROUP BY year, quarter, month_num ORDER BY year, month_num"

        else:
            return f"Invalid info_type: '{info_type}'. Must be 'summary', 'quarters', or 'monthly'."

        results = execute_query(sql)
        if not results:
            return "No date information available for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error retrieving date info: {str(e)}"
