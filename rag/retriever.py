from langchain_core.tools import tool
from rag.embedder import get_vectorstore

@tool
def search_doc(query: str) -> str:
    """Search the knowledge base for relevant documents.
    This tool has knowledge about:
    - What tables and columns mean
    - What abbreviations like HCP, TRx, NRx mean
    - What the allowed values for fields are
    - How tables are related to each other
    - What date range the data covers
    Do NOT use this tool for retrieving actual data values — use the SQL tools instead.

    Args:
        query: A natural language question about the data schema or terminology.
    """
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(query, k=3)
    if not results:
        return "No relevant documents found."
    output_parts = []
    for doc in results:
        source = doc.metadata.get("source", "unknown")
        output_parts.append(f"[Source: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(output_parts)