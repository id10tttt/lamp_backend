# -*- coding: utf-8 -*-
import asyncpg
import os

# 配置 PostgreSQL 数据库连接池
DATABASE_URL = os.getenv('DATABASE_URL')


# 创建连接池
class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None

    async def init_pool(self):
        self.pool = await asyncpg.create_pool(dsn=self.database_url)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)

    async def close_pool(self):
        if self.pool:
            await self.pool.close()
