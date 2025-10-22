from dotenv import load_dotenv
from src.infrastructure.messaging.rabbitmq_config import RabbitMQConfig
from src.infrastructure.messaging.rabbitmq_consumer import RabbitMQConsumer
from src.application.services.message_service import MessageService
from src.application.use_cases.process_message_use_case import ProcessMessageUseCase

load_dotenv()


def main():
    """Função principal para inicializar o consumidor RabbitMQ."""

    config = RabbitMQConfig()

    consumer = RabbitMQConsumer(config)
    message_service = MessageService()
    use_case = ProcessMessageUseCase(message_service)

    def callback(ch, method, properties, body):
        """Callback executado ao receber uma mensagem."""
        try:
            message = message_service.parse_message(body, method.routing_key)
            use_case.execute(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    try:
        consumer.connect()
        consumer.declare_queue()
        consumer.start_consuming(callback)

    except KeyboardInterrupt:
        print("Encerrando consumidor...")
        consumer.close()

    except Exception as e:
        print(f"Erro: {e}")
        consumer.close()


if __name__ == "__main__":
    main()
