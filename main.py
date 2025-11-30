import logging
import signal
import sys
from dotenv import load_dotenv
from src.infrastructure.messaging.rabbitmq_config import RabbitMQConfig
from src.infrastructure.messaging.rabbitmq_consumer import RabbitMQConsumer
from src.application.use_cases.process_message_use_case import ProcessMessageUseCase

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

consumer = None


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    if consumer:
        consumer.stop()
    sys.exit(0)


def main():
    global consumer
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    config = RabbitMQConfig()
    
    logger.info("Starting RabbitMQ consumer with auto-retry capability")
    logger.info(f"Queue mode: {config.queue_mode}")
    logger.info(f"Target queue: {config.queue_name}")
    logger.info(f"Wait for queue: {config.wait_for_queue}")
    
    consumer = RabbitMQConsumer(config)
    
    try:
        use_case = ProcessMessageUseCase()
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.info("Consumer will start but message processing will be limited")
        use_case = None

    def callback(ch, method, properties, body):
        """Process received messages with robust error handling."""
        try:
            if use_case:
                use_case.execute(body, method.routing_key)
            else:
                logger.info(f"Received message (basic processing): {body.decode('utf-8', errors='ignore')[:100]}...")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.debug("Message processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            try:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except:
                logger.warning("Could not send NACK - connection may be closed")

    try:
        consumer.start_consuming(callback)
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
    finally:
        logger.info("Shutting down consumer...")
        if consumer:
            consumer.close()
        logger.info("Consumer shutdown complete")


if __name__ == "__main__":
    main()
