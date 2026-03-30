import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from db.connector import get_connection
from rag.embedder import get_vectorstore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("------Starting up------")
    conn = get_connection()
    vectorstore = get_vectorstore()
    yield
    logger.info("------Shutting down------")


app = FastAPI(
    title="Synthio Lab Analyst",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS Middleware for GCP/Frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For "minimal changes" - can be restricted later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    from config import settings

    uvicorn.run(
        app="main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )