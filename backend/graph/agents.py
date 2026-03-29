import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from config import settings
from tools.library.hcp_lookup import get_hcp_profile
from tools.library.hcp_rx import get_hcp_rx_performance
from tools.library.account_summary import get_account_profile
from tools.library.payor_mix import get_account_payor_mix
from tools.library.rep_activity import get_rep_activity_summary
from tools.library.date_range import get_date_info
from tools.library.hcp_ranking import get_hcp_ranking
from tools.library.rx_trend import get_rx_trend
from tools.library.rx_comparison import compare_rx_performance
from tools.library.rep_performance import get_rep_performance
from tools.library.specialty_analysis import get_specialty_analysis
from tools.library.market_share import get_market_share_metrics
from tools.library.territory import get_territory_summary
from tools.library.rep_hcp_coverage import get_rep_hcp_coverage
from tools.library.account_performance import get_account_performance
from tools.library.kpi_dashboard import get_kpi_dashboard
from tools.library.growth_analysis import get_growth_analysis
from tools.fallback_sql import execute_safe_sql
from rag.retriever import search_doc

logger = logging.getLogger(__name__)

def get_llm(temperature=0):
    return ChatGoogleGenerativeAI(
        model=settings.PLANNER_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
    )

# --- Tool Groupings ---
DATA_ANALYST_TOOLS = [
    get_hcp_profile, get_hcp_rx_performance, get_account_profile,
    get_account_payor_mix, get_rep_activity_summary, get_date_info,
    get_hcp_ranking, get_rx_trend, compare_rx_performance,
    get_rep_performance, get_specialty_analysis, get_market_share_metrics,
    get_territory_summary, get_rep_hcp_coverage, get_account_performance,
    get_kpi_dashboard, get_growth_analysis, execute_safe_sql
]

PHARMA_RESEARCHER_TOOLS = [search_doc]

# --- Agent Prompts ---

SUPERVISOR_PROMPT = """You are the Lead Pharmaceutical Strategy Orchestrator.
Your job is to decompose complex user queries into a plan and delegate to specialized agents.

Agents available:
1. Data_Analyst: Expert in structured Rx data, sales metrics, and SQL.
2. Pharma_Researcher: Expert in clinical documentation and drug information (RAG).

**STRICT SCOPE RULES:**
- You ONLY have access to internal GAZYVA pharmaceutical data.
- REFUSE requests for: competitor drug performance (not in our data), real-time stock prices, news, web scraping scripts, or destructive SQL.
- If a request is off-topic, select FINISH immediately and inform the user of the limitations.

**PLANNING RULES:**
- If the question is about sales, HCP rankings, or specific metrics, use Data_Analyst.
- If the question is about clinical trials, indications, or drug science, use Pharma_Researcher.
- If it's a mix, sequence them.
"""

DATA_ANALYST_PROMPT = """You are a Pharmaceutical Data Analyst.
You excel at querying structured databases to uncover sales trends, HCP performance, and territory metrics.

**SPECIFICITY RULES:**
1. Always check for multiple entries if a name (like 'Mountain Hospital') exists in multiple locations or categories (Hospital vs. Clinic). 
2. Use the `account_id` whenever provided to avoid ambiguity.
3. For payor mix, the latest data is usually preferred unless a year/quarter is specified.
4. For rep activity, use the 'ALL TOTAL' row for overall counts.
"""

PHARMA_RESEARCHER_PROMPT = """You are a Clinical Pharma Researcher.
You specialize in extracting insights from pharmaceutical documentation, clinical guidelines, and drug labels.
Use the search tool to find scientific or regulatory information.
"""
