import pika
from pika.adapters.blocking_connection import BlockingChannel
from typing import Callable
from rabbitmq_config import RabbitMQConfig


class RabbitMQConsumer:
    """Consumidor de mensagens do RabbitMQ."""

    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self.connection = None
        self.channel: BlockingChannel = None

    def connect(self) -> None:
        """Estabelece conexão com o RabbitMQ."""
        credentials = pika.PlainCredentials(
            self.config.username,
            self.config.password
        )

        parameters = pika.ConnectionParameters(
            host=self.config.host,
            port=self.config.port,
            virtual_host=self.config.virtual_host,
            credentials=credentials
        )

        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=self.config.prefetch_count)

    def declare_queue(self) -> None:
        """Declara a fila no RabbitMQ."""
        self.channel.queue_declare(
            queue=self.config.queue_name,
            durable=True
        )

    def start_consuming(self, callback: Callable) -> None:
        """Inicia o consumo de mensagens da fila."""
        self.channel.basic_consume(
            queue=self.config.queue_name,
            on_message_callback=callback,
            auto_ack=False
        )

        print(f"Aguardando mensagens na fila '{self.config.queue_name}'...")
        self.channel.start_consuming()

    def close(self) -> None:
        """Fecha a conexão com o RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
