from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class Message:
    """Entidade que representa uma mensagem recebida do RabbitMQ."""

    id: str
    body: Dict[str, Any]
    timestamp: datetime
    routing_key: str
