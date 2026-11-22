"""
File: backend/redis_client.py
Mô tả: Khởi tạo và cấu hình kết nối Redis async dùng chung toàn bộ Backend.

Task #90 - [BE] Khởi tạo và cấu hình kết nối Redis async trong FastAPI

Cách dùng (trong bất kỳ file nào):
    from redis_client import get_redis
    redis = await get_redis()
    await redis.set("key", "value")
"""

import os
import pathlib
import asyncio
import redis.asyncio as aioredis
from dotenv import load_dotenv

_env_path = pathlib.Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

# URL kết nối Redis - lấy từ biến môi trường, fallback về localhost cho môi trường dev
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Pool kết nối Redis dùng chung - được tạo 1 lần duy nhất khi server khởi động
# decode_responses=True: tự động decode bytes -> str khi đọc giá trị từ Redis
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    Lấy instance Redis async (Singleton pattern có hỗ trợ reset khi event loop thay đổi).
    Tạo connection pool và tự động khởi tạo lại nếu loop hiện tại đã đóng (phục vụ đa luồng/test).
    
    Raises:
        RuntimeError: Nếu không thể kết nối tới Redis server.
    """
    global _redis_pool
    try:
        loop = asyncio.get_running_loop()
        if _redis_pool is not None:
            conn_pool = getattr(_redis_pool, "connection_pool", None)
            pool_loop = getattr(conn_pool, "_loop", None)
            if pool_loop is not None and (pool_loop is not loop or pool_loop.is_closed()):
                _redis_pool = None
    except Exception:
        pass

    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,      # Trả về str thay vì bytes
            socket_connect_timeout=5,   # Timeout kết nối: 5 giây
            socket_timeout=5,           # Timeout đọc/ghi: 5 giây
        )
    return _redis_pool


async def close_redis():
    """
    Đóng kết nối Redis khi server shutdown.
    Được gọi trong sự kiện shutdown của FastAPI.
    """
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
