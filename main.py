import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("------Starting up------")

    yield
    logger.info("------Shutting down------")


app = FastAPI(
    title="Synthio Lab Analyst",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from config import settings

    uvicorn.run(
        app="main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )