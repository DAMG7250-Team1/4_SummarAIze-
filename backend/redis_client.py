import redis
from config import get_settings

settings = get_settings()

class RedisClient:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def add_to_stream(self, stream_name: str, data: dict) -> str:
        """Add data to a Redis stream."""
        return self.redis_client.xadd(stream_name, data)

    def read_from_stream(self, stream_name: str, count: int = 1, block: int = 0) -> list:
        """Read data from a Redis stream."""
        return self.redis_client.xread({stream_name: '0'}, count=count, block=block)

    def create_consumer_group(self, stream_name: str, group_name: str):
        """Create a consumer group for a stream."""
        try:
            self.redis_client.xgroup_create(stream_name, group_name, mkstream=True)
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' not in str(e):
                raise

    def read_as_consumer(self, stream_name: str, group_name: str, consumer_name: str):
        """Read from stream as a consumer in a group."""
        return self.redis_client.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: '>'},
            count=1
        )

redis_client = RedisClient() 