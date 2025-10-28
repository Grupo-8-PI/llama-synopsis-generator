from src.domain.entities import Message
from src.infrastructure.llm.llm_service import LLMService
from datetime import datetime
import uuid
import json
import logging

logger = logging.getLogger(__name__)


class ProcessMessageUseCase:
    """Caso de uso para processar mensagens recebidas e gerar sinopses."""

    def __init__(self):
        try:
            self.llm_service = LLMService()
        except Exception as e:
            logger.warning(f"Falha ao inicializar LLM service: {e}")
            self.llm_service = None

    def execute(self, body: bytes, routing_key: str) -> None:
        """Executa o processamento da mensagem."""
        message = self._parse_message(body, routing_key)

        if not self._validate_message(message):
            raise ValueError("Mensagem inválida")

        livro_id = message.body.get("livroId")
        titulo = message.body.get("titulo")
        autor = message.body.get("autor")
        isbn = message.body.get("isbn")

        logger.info(f"=== Processando Livro ===")
        logger.info(f"ID: {livro_id}")
        logger.info(f"Título: {titulo}")
        logger.info(f"Autor: {autor}")
        logger.info(f"ISBN: {isbn}")
        logger.info(f"Routing Key: {message.routing_key}")
        logger.info("=" * 25)

        if self.llm_service:
            try:
                logger.info("Iniciando geração de sinopse...")
                sinopse = self.llm_service.generate_book_synopsis(titulo, autor, isbn)
                
                logger.info("=== Sinopse Gerada ===")
                logger.info(f"Título: {titulo}")
                logger.info(f"Sinopse: {sinopse}")
                logger.info("=" * 25)
                
                
                
            except Exception as e:
                logger.error(f"Erro ao gerar sinopse: {e}")
        else:
            logger.warning("LLM service não disponível, pulando geração de sinopse")

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
        """Valida se a mensagem contém os dados obrigatórios do livro."""
        if not message.body:
            return False
            
        required_fields = ["livroId", "titulo", "autor", "isbn"]
        
        for field in required_fields:
            if field not in message.body or not message.body[field]:
                logger.error(f"Campo obrigatório ausente ou vazio: {field}")
                return False
                
        return True
