import redis
import redis.asyncio
import json
from config import get_settings
import logging
from typing import Optional, Any

settings = get_settings()
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        # Synchronous client for non-async operations
        self.redis = redis.Redis(host=host, port=port, db=db)
        # Async client for async operations
        self.async_redis = None

    async def initialize(self):
        """Initialize the async Redis connection."""
        # For Redis 4.2.0+
        self.async_redis = redis.asyncio.Redis(
            host=self.host, 
            port=self.port, 
            db=self.db
        )

    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis asynchronously."""
        if self.async_redis is None:
            await self.initialize()
        return await self.async_redis.get(key)

    async def set(self, key: str, value: str, expire: int = None) -> bool:
        """Set a value in Redis asynchronously."""
        if self.async_redis is None:
            await self.initialize()
        result = await self.async_redis.set(key, value)
        if expire:
            await self.async_redis.expire(key, expire)
        return result

    def add_to_stream(self, stream_name: str, data: dict) -> str:
        """Add data to a Redis stream."""
        return self.redis.xadd(stream_name, data)

    def read_from_stream(self, stream_name: str, count: int = 1, block: int = 0) -> list:
        """Read data from a Redis stream."""
        return self.redis.xread({stream_name: '0'}, count=count, block=block)

    def create_consumer_group(self, stream_name: str, group_name: str):
        """Create a consumer group for a stream."""
        try:
            self.redis.xgroup_create(stream_name, group_name, mkstream=True)
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' not in str(e):
                raise

    def read_as_consumer(self, stream_name: str, group_name: str, consumer_name: str):
        """Read from stream as a consumer in a group."""
        return self.redis.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: '>'},
            count=1
        )

# Create a singleton instance
redis_client = RedisClient() 