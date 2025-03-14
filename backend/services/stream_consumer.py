import asyncio
import logging
from redis_client import redis_client
import json
import datetime
from typing import Dict, Any
import redis.exceptions

logger = logging.getLogger(__name__)

class StreamConsumer:
    def __init__(self):
        self.running = False
        self.stats = {
            "processed_events": 0,
            "summarize_events": 0,
            "question_events": 0,
            "errors": 0,
            "start_time": None,
            "connection_errors": 0,
            "last_error": None
        }
        self.max_retries = 5
        self.retry_delay = 5  # seconds
    
    async def start(self):
        """Start consuming messages from Redis streams."""
        self.running = True
        self.stats["start_time"] = datetime.datetime.now().isoformat()
        
        # Create consumer group with retry logic
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # Create consumer group
                redis_client.create_consumer_group("llm_events", "analytics_group")
                logger.info("Started consuming from Redis streams")
                break
            except redis.exceptions.ConnectionError as e:
                retry_count += 1
                self.stats["connection_errors"] += 1
                self.stats["last_error"] = str(e)
                logger.error(f"Redis connection error (attempt {retry_count}/{self.max_retries}): {str(e)}")
                if retry_count >= self.max_retries:
                    logger.error("Max retries reached. Unable to connect to Redis.")
                    return
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Error creating consumer group: {str(e)}")
                self.stats["errors"] += 1
                self.stats["last_error"] = str(e)
                return
        
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
                        
                        # Acknowledge message
                        try:
                            redis_client.acknowledge_message("llm_events", "analytics_group", message_id)
                        except Exception as e:
                            logger.error(f"Error acknowledging message {message_id}: {str(e)}")
                        
                        # Update stats
                        self.stats["processed_events"] += 1
                
            except redis.exceptions.ConnectionError as e:
                self.stats["connection_errors"] += 1
                self.stats["last_error"] = str(e)
                logger.error(f"Redis connection error: {str(e)}")
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Error processing stream messages: {str(e)}")
                self.stats["errors"] += 1
                self.stats["last_error"] = str(e)
                await asyncio.sleep(1)
    
    async def _process_message(self, message_data):
        """Process a message from the stream."""
        try:
            event_type = message_data.get("event_type")
            
            if event_type == "summarize":
                # Process summarization event
                logger.info(f"Processing summarization event: {message_data}")
                self.stats["summarize_events"] += 1
                
                # Extract data from the message
                filename = message_data.get("filename")
                model = message_data.get("model")
                summary = message_data.get("summary")
                tokens = message_data.get("tokens", 0)
                cost = message_data.get("cost", 0)
                
                # Store analytics data in Redis
                analytics_key = f"analytics:summary:{filename}"
                analytics_data = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "filename": filename,
                    "model": model,
                    "summary_length": len(summary) if summary else 0,
                    "tokens": tokens,
                    "cost": cost
                }
                
                # Store analytics data
                try:
                    await redis_client.set(analytics_key, json.dumps(analytics_data))
                except Exception as e:
                    logger.error(f"Error storing analytics data: {str(e)}")
                
            elif event_type == "question":
                # Process question event
                logger.info(f"Processing question event: {message_data}")
                self.stats["question_events"] += 1
                
                # Extract data from the message
                filename = message_data.get("filename")
                model = message_data.get("model")
                question = message_data.get("question")
                answer = message_data.get("answer")
                tokens = message_data.get("tokens", 0)
                cost = message_data.get("cost", 0)
                
                # Store analytics data in Redis
                analytics_key = f"analytics:question:{filename}:{hash(question)}"
                analytics_data = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "filename": filename,
                    "model": model,
                    "question": question,
                    "answer_length": len(answer) if answer else 0,
                    "tokens": tokens,
                    "cost": cost
                }
                
                # Store analytics data
                try:
                    await redis_client.set(analytics_key, json.dumps(analytics_data))
                except Exception as e:
                    logger.error(f"Error storing analytics data: {str(e)}")
                
            else:
                logger.warning(f"Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
    
    def stop(self):
        """Stop consuming messages."""
        self.running = False
        logger.info("Stopped consuming from Redis streams")
        
    async def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        self.stats["uptime_seconds"] = (
            datetime.datetime.now() - 
            datetime.datetime.fromisoformat(self.stats["start_time"])
        ).total_seconds() if self.stats["start_time"] else 0
        
        return self.stats

# Create a singleton instance
stream_consumer = StreamConsumer() 