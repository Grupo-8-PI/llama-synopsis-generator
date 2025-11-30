from dataclasses import dataclass
import os


@dataclass
class RabbitMQConfig:

    host: str = None
    port: int = None
    username: str = None
    password: str = None
    virtual_host: str = None
    queue_name: str = None
    exchange_name: str = None
    routing_key: str = None
    prefetch_count: int = None
    
    max_retries: int = None
    initial_retry_delay: float = None
    max_retry_delay: float = None
    failure_threshold: int = None
    recovery_timeout: float = None
    
    queue_mode: str = None
    wait_for_queue: bool = None
    queue_check_interval: float = None

    def __post_init__(self):
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.username = os.getenv("RABBITMQ_USERNAME", "guest")
        self.password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.virtual_host = os.getenv("RABBITMQ_VIRTUAL_HOST", "/")
        self.queue_name = os.getenv("RABBITMQ_QUEUE_NAME", "default_queue")
        self.exchange_name = os.getenv("RABBITMQ_EXCHANGE_NAME", "")
        self.routing_key = os.getenv("RABBITMQ_ROUTING_KEY", "")
        self.prefetch_count = int(os.getenv("RABBITMQ_PREFETCH_COUNT", "1"))
        
        self.max_retries = int(os.getenv("RABBITMQ_MAX_RETRIES", "10"))
        self.initial_retry_delay = float(os.getenv("RABBITMQ_INITIAL_RETRY_DELAY", "1.0"))
        self.max_retry_delay = float(os.getenv("RABBITMQ_MAX_RETRY_DELAY", "60.0"))
        self.failure_threshold = int(os.getenv("RABBITMQ_FAILURE_THRESHOLD", "5"))
        self.recovery_timeout = float(os.getenv("RABBITMQ_RECOVERY_TIMEOUT", "30.0"))
        
        self.queue_mode = os.getenv("RABBITMQ_QUEUE_MODE", "passive")
        self.wait_for_queue = os.getenv("RABBITMQ_WAIT_FOR_QUEUE", "true").lower() == "true"
        self.queue_check_interval = float(os.getenv("RABBITMQ_QUEUE_CHECK_INTERVAL", "5.0"))
