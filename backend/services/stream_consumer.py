import asyncio
import logging
from redis_client import redis_client
import json

logger = logging.getLogger(__name__)

class StreamConsumer:
    def __init__(self):
        self.running = False
    
    async def start(self):
        """Start consuming messages from Redis streams."""
        self.running = True
        
        # Create consumer group
        redis_client.create_consumer_group("llm_events", "analytics_group")
        
        logger.info("Started consuming from Redis streams")
        
        # Consume messages in a loop
        while self.running:
            try:
                # Read messages as a consumer
                messages = redis_client.read_as_consumer(
                    "llm_events", "analytics_group", "analytics_consumer"
                )
                
                if not messages:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process messages
                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        # Process the message
                        await self._process_message(message_data)
                        
                        # Acknowledge message (you'd need to add this method to your RedisClient)
                        # redis_client.acknowledge_message("llm_events", "analytics_group", message_id)
                
            except Exception as e:
                logger.error(f"Error processing stream messages: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_message(self, message_data):
        """Process a message from the stream."""
        try:
            event_type = message_data.get("event_type")
            
            if event_type == "summarize":
                # Process summarization event
                logger.info(f"Processing summarization event: {message_data}")
                # Add your processing logic here
                
            elif event_type == "question":
                # Process question event
                logger.info(f"Processing question event: {message_data}")
                # Add your processing logic here
                
            else:
                logger.warning(f"Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def stop(self):
        """Stop consuming messages."""
        self.running = False
        logger.info("Stopped consuming from Redis streams")

# Create a singleton instance
stream_consumer = StreamConsumer() 