import os
import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from config import settings

logger = logging.getLogger(__name__)

_vectorstore = None

def get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
        )
        docs = _build_docs()
        _vectorstore = FAISS.from_documents(docs, embeddings)
        logger.info(f"Built vectorstore with {len(docs)} documents")
    return _vectorstore

def _build_docs() -> List[Document]:
    docs = []
    context_docs_dir = settings.DOCS_DIR
    analysis_file_path = os.path.join(context_docs_dir, "analysis.md")
    if os.path.exists(analysis_file_path):
        with open(analysis_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            sections = content.split("---")
            for i, section in enumerate(sections):
                section_tnp = section.strip()
                if section_tnp:
                    docs.append(Document(
                        page_content=section_tnp,
                        metadata={
                            "source": analysis_file_path,
                            "chunk_id": i,
                        }
                    ))

    return docs
    