import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import router as api_router
from db.connector import get_db_connection
from rag.embedder import get_vectorstore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("------Starting up------")
    conn = get_db_connection()
    vectorstore = get_vectorstore()
    yield
    logger.info("------Shutting down------")


app = FastAPI(
    title="Synthio Lab Analyst",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    from config import settings

    uvicorn.run(
        app="main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )