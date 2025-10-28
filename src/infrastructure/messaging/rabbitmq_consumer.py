import pika
import time
import logging
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker, ConnectionClosedByBroker
from typing import Callable
from src.infrastructure.messaging.rabbitmq_config import RabbitMQConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RabbitMQConsumer:

    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self.connection = None
        self.channel: BlockingChannel = None
        self.is_consuming = False
        self.should_stop = False
        
        self.max_retries = config.max_retries
        self.initial_retry_delay = config.initial_retry_delay
        self.max_retry_delay = config.max_retry_delay
        self.retry_count = 0
        
        self.circuit_state = ConnectionState.CLOSED
        self.failure_count = 0
        self.failure_threshold = config.failure_threshold
        self.recovery_timeout = config.recovery_timeout
        self.last_failure_time = 0
        self.queue_available = False

    def _calculate_retry_delay(self) -> float:
        delay = self.initial_retry_delay * (2 ** self.retry_count)
        return min(delay, self.max_retry_delay)

    def _can_attempt_connection(self) -> bool:
        if self.circuit_state == ConnectionState.CLOSED:
            return True
        elif self.circuit_state == ConnectionState.HALF_OPEN:
            return True
        elif self.circuit_state == ConnectionState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.circuit_state = ConnectionState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False

    def _record_success(self) -> None:
        self.retry_count = 0
        self.failure_count = 0
        self.circuit_state = ConnectionState.CLOSED
        logger.info("Connection successful, circuit breaker CLOSED")

    def _record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_state = ConnectionState.OPEN
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

    def connect(self) -> bool:
        if not self._can_attempt_connection():
            return False

        try:
            credentials = pika.PlainCredentials(
                self.config.username,
                self.config.password
            )

            parameters = pika.ConnectionParameters(
                host=self.config.host,
                port=self.config.port,
                virtual_host=self.config.virtual_host,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.basic_qos(prefetch_count=self.config.prefetch_count)
            
            self._record_success()
            logger.info(f"Connected successfully to RabbitMQ at {self.config.host}:{self.config.port}")
            return True
            
        except (AMQPConnectionError, ConnectionClosedByBroker, OSError) as e:
            self._record_failure()
            logger.error(f"Connection failed: {e}")
            return False

    def _check_queue_exists(self) -> bool:
        try:
            self.channel.queue_declare(
                queue=self.config.queue_name,
                passive=True
            )
            return True
        except Exception as e:
            logger.debug(f"Queue {self.config.queue_name} does not exist or is not accessible: {e}")
            return False

    def _wait_for_queue(self) -> bool:
        """Wait for queue to be available, checking periodically."""
        logger.info(f"Waiting for queue '{self.config.queue_name}' to be available...")
        
        while not self.should_stop:
            if not self._ensure_connection():
                time.sleep(self.config.queue_check_interval)
                continue
                
            if self._check_queue_exists():
                logger.info(f"Queue '{self.config.queue_name}' is now available")
                return True
                
            logger.debug(f"Queue not available yet, checking again in {self.config.queue_check_interval}s...")
            time.sleep(self.config.queue_check_interval)
            
        return False

    def _get_queue_info(self) -> dict:
        """Get queue information for health check."""
        try:
            method = self.channel.queue_declare(
                queue=self.config.queue_name,
                passive=True
            )
            return {
                "exists": True,
                "message_count": method.method.message_count,
                "consumer_count": method.method.consumer_count
            }
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def ensure_queue(self) -> bool:
        """Ensure queue is available based on configured mode."""
        if self.config.queue_mode == "passive":
            if self._check_queue_exists():
                queue_info = self._get_queue_info()
                logger.info(f"Found existing queue '{self.config.queue_name}' with {queue_info.get('message_count', 0)} messages")
                self.queue_available = True
                return True
            elif self.config.wait_for_queue:
                return self._wait_for_queue()
            else:
                logger.error(f"Queue '{self.config.queue_name}' does not exist and wait_for_queue is disabled")
                return False
        
        elif self.config.queue_mode == "active":
            try:
                self.channel.queue_declare(
                    queue=self.config.queue_name,
                    durable=True
                )
                logger.info(f"Queue '{self.config.queue_name}' declared successfully")
                self.queue_available = True
                return True
            except Exception as e:
                logger.error(f"Failed to declare queue '{self.config.queue_name}': {e}")
                return False
        
        else:
            logger.error(f"Invalid queue_mode: {self.config.queue_mode}. Use 'passive' or 'active'")
            return False

    def _ensure_connection(self) -> bool:
        """Ensure active connection, reconnecting if necessary."""
        if self.connection and not self.connection.is_closed:
            return True
            
        return self.connect()

    def start_consuming(self, callback: Callable) -> None:
        """Start message consumption with automatic retry and error handling."""
        self.is_consuming = True
        
        while not self.should_stop:
            try:
                if not self._ensure_connection():
                    if self.retry_count < self.max_retries:
                        delay = self._calculate_retry_delay()
                        logger.warning(f"Retrying connection in {delay:.1f}s (attempt {self.retry_count + 1}/{self.max_retries})")
                        time.sleep(delay)
                        self.retry_count += 1
                        continue
                    else:
                        logger.error(f"Max retries ({self.max_retries}) exceeded. Stopping consumer.")
                        break

                if not self.ensure_queue():
                    logger.error("Failed to ensure queue availability. Retrying connection...")
                    time.sleep(self.config.queue_check_interval)
                    continue
                
                def robust_callback(ch, method, properties, body):
                    try:
                        callback(ch, method, properties, body)
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")
                        try:
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                        except:
                            pass

                self.channel.basic_consume(
                    queue=self.config.queue_name,
                    on_message_callback=robust_callback,
                    auto_ack=False
                )

                logger.info(f"Started consuming from queue '{self.config.queue_name}'")
                self.channel.start_consuming()
                
            except (AMQPConnectionError, ConnectionClosedByBroker, ChannelClosedByBroker) as e:
                logger.warning(f"Connection lost during consuming: {e}")
                self._record_failure()
                self._cleanup_connection()
                
                if not self.should_stop and self.retry_count < self.max_retries:
                    delay = self._calculate_retry_delay()
                    logger.info(f"Reconnecting in {delay:.1f}s...")
                    time.sleep(delay)
                    self.retry_count += 1
                    continue
                else:
                    break
                    
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.should_stop = True
                break
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                self._cleanup_connection()
                break

        self.is_consuming = False
        logger.info("Consumer stopped")

    def _cleanup_connection(self) -> None:
        """Safely cleanup connection and channel resources."""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.stop_consuming()
        except:
            pass
            
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except:
            pass
            
        self.channel = None
        self.connection = None
        self.queue_available = False

    def stop(self) -> None:
        """Stop consumer gracefully."""
        logger.info("Stopping consumer...")
        self.should_stop = True
        
        if self.channel and not self.channel.is_closed:
            try:
                self.channel.stop_consuming()
            except:
                pass

    def close(self) -> None:
        """Close RabbitMQ connection safely."""
        self.stop()
        self._cleanup_connection()
        logger.info("Consumer closed")
