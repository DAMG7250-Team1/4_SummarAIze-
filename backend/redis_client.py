import redis
import redis.asyncio
import json
from config import get_settings
import logging
from typing import Optional, Any
import ssl

settings = get_settings()
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, host=None, port=None, db=0):
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.db = db
        self.password = settings.REDIS_PASSWORD
        self.ssl = getattr(settings, 'REDIS_SSL', False)
        self.timeout = getattr(settings, 'REDIS_TIMEOUT', None)
        
        # For Redis Cloud, we'll try both with and without SSL
        self.redis = None
        self._connect_sync()
            
        # Async client for async operations
        self.async_redis = None

    def _connect_sync(self):
        """Connect to Redis with sync client, trying different configurations."""
        # First try: Use settings as provided
        try:
            logger.info(f"Attempting to connect to Redis at {self.host}:{self.port} with SSL={self.ssl}")
            self.redis = redis.Redis(
                host=self.host, 
                port=self.port, 
                db=self.db,
                password=self.password,
                ssl=self.ssl,
                ssl_cert_reqs=ssl.CERT_NONE if self.ssl else None,
                socket_timeout=self.timeout,
                decode_responses=True
            )
            self.redis.ping()
            logger.info("Successfully connected to Redis")
            return
        except Exception as e:
            logger.error(f"Error connecting to Redis with SSL={self.ssl}: {str(e)}")
        
        # Second try: Try with opposite SSL setting
        try:
            opposite_ssl = not self.ssl
            logger.info(f"Attempting to connect to Redis with SSL={opposite_ssl}")
            self.redis = redis.Redis(
                host=self.host, 
                port=self.port, 
                db=self.db,
                password=self.password,
                ssl=opposite_ssl,
                ssl_cert_reqs=ssl.CERT_NONE if opposite_ssl else None,
                socket_timeout=self.timeout,
                decode_responses=True
            )
            self.redis.ping()
            logger.info(f"Successfully connected to Redis with SSL={opposite_ssl}")
            self.ssl = opposite_ssl
            return
        except Exception as e:
            logger.error(f"Error connecting to Redis with SSL={opposite_ssl}: {str(e)}")
        
        # Third try: For Redis Cloud, try with specific SSL configuration
        try:
            logger.info("Attempting to connect to Redis Cloud with specific SSL configuration")
            self.redis = redis.Redis(
                host=self.host, 
                port=self.port, 
                db=self.db,
                password=self.password,
                ssl=True,
                ssl_cert_reqs=ssl.CERT_NONE,
                socket_connect_timeout=self.timeout,
                socket_keepalive=True,
                decode_responses=True
            )
            self.redis.ping()
            logger.info("Successfully connected to Redis Cloud")
            self.ssl = True
            return
        except Exception as e:
            logger.error(f"Error connecting to Redis Cloud: {str(e)}")
            
        # Last resort: Try without SSL and with minimal configuration
        try:
            logger.info("Last attempt: connecting with minimal configuration")
            self.redis = redis.Redis(
                host=self.host, 
                port=self.port, 
                password=self.password,
                decode_responses=True
            )
            self.redis.ping()
            logger.info("Successfully connected to Redis with minimal configuration")
            self.ssl = False
            return
        except Exception as e:
            logger.error(f"All Redis connection attempts failed. Last error: {str(e)}")
            # Create a dummy client that will raise exceptions when used
            self.redis = redis.Redis(host='localhost')

    async def initialize(self):
        """Initialize the async Redis connection."""
        if self.async_redis is not None:
            return
            
        try:
            # Use the same configuration that worked for sync client
            self.async_redis = redis.asyncio.Redis(
                host=self.host, 
                port=self.port, 
                db=self.db,
                password=self.password,
                ssl=self.ssl,
                ssl_cert_reqs=ssl.CERT_NONE if self.ssl else None,
                socket_timeout=self.timeout,
                decode_responses=True
            )
            await self.async_redis.ping()
            logger.info("Successfully connected to Redis (async)")
        except Exception as e:
            logger.error(f"Error connecting to Redis (async): {str(e)}")
            # Try with minimal configuration
            try:
                self.async_redis = redis.asyncio.Redis(
                    host=self.host, 
                    port=self.port, 
                    password=self.password,
                    decode_responses=True
                )
                await self.async_redis.ping()
                logger.info("Successfully connected to Redis (async) with minimal configuration")
            except Exception as e2:
                logger.error(f"All async Redis connection attempts failed: {str(e2)}")
                # Create a dummy client that will raise exceptions when used
                self.async_redis = redis.asyncio.Redis(host='localhost')

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
            logger.info(f"Created consumer group {group_name} for stream {stream_name}")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' not in str(e):
                logger.error(f"Error creating consumer group: {str(e)}")
                raise
            else:
                logger.info(f"Consumer group {group_name} already exists for stream {stream_name}")

    def read_as_consumer(self, stream_name: str, group_name: str, consumer_name: str):
        """Read from stream as a consumer in a group."""
        return self.redis.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: '>'},
            count=1
        )
        
    def acknowledge_message(self, stream_name: str, group_name: str, message_id: str):
        """Acknowledge a message has been processed."""
        return self.redis.xack(stream_name, group_name, message_id)

# Create a singleton instance
redis_client = RedisClient() 