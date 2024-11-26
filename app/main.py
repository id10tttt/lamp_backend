# -*- coding: utf-8 -*-

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
import uvicorn
import logging
import aioredis
from contextlib import asynccontextmanager
from routes.main import router as api_router
from db.pg_client import Database, DATABASE_URL
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在 FastAPI 启动时初始化连接池
    await db.init_pool()
    yield
    redis_pool = await aioredis.create_redis_pool(REDIS_URL)
    yield redis_pool
    redis_pool.close()
    # 在 FastAPI 关闭时关闭连接池
    await db.close_pool()
    await redis_pool.wait_closed()


async def get_redis(redis_pool=Depends(lifespan)):
    return redis_pool

app = FastAPI(title="async-fastapi-sqlalchemy", default_response_class=JSONResponse, lifespan=lifespan)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app.include_router(api_router, prefix="/api")

db = Database(DATABASE_URL)


@app.get("/", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"message": "It worked!!"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
