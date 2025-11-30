from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class MessageRecebida:

    id: str
    body: Dict[str, Any]
    timestamp: datetime
    routing_key: str
