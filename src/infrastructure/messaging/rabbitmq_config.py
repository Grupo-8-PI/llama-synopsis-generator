from dataclasses import dataclass
import os


@dataclass
class RabbitMQConfig:
    """Configurações de conexão com o RabbitMQ usando variáveis de ambiente."""

    host: str = None
    port: int = None
    username: str = None
    password: str = None
    virtual_host: str = None
    queue_name: str = None
    exchange_name: str = None
    routing_key: str = None
    prefetch_count: int = None

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
