from src.domain.entities import Message
from datetime import datetime
import uuid
import json


class ProcessMessageUseCase:
    """Caso de uso para processar mensagens recebidas."""

    def execute(self, body: bytes, routing_key: str) -> None:
        """Executa o processamento da mensagem."""
        message = self._parse_message(body, routing_key)

        if not self._validate_message(message):
            raise ValueError("Mensagem inválida")

        print(f"Processando mensagem ID: {message.id}")
        print(f"Corpo: {message.body}")
        print(f"Timestamp: {message.timestamp}")

    def _parse_message(self, body: bytes, routing_key: str) -> Message:
        """Converte mensagem bruta em entidade de domínio."""
        message_body = json.loads(body.decode('utf-8'))

        return Message(
            id=str(uuid.uuid4()),
            body=message_body,
            timestamp=datetime.now(),
            routing_key=routing_key
        )

    def _validate_message(self, message: Message) -> bool:
        """Valida se a mensagem está no formato esperado."""
        return message.body is not None and len(message.body) > 0
