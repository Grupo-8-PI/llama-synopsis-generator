from numbers import Number
from src.domain.entities import Message
from src.infrastructure.llm.llm_service import LLMService
from datetime import datetime
import uuid
import json
import logging
import requests
import os
from urllib.parse import quote

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
                self._send_callback_to_api(livro_id, sinopse)
                
            except Exception as e:
                logger.error(f"Erro ao gerar sinopse: {e}")
        else:
            logger.warning("LLM service não disponível, pulando geração de sinopse")

        

    def _send_callback_to_api(self, livro_id: str, sinopse: str) -> None:
        """Envia callback para a API com a sinopse gerada."""
        try:
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8080")
            api_endpoint = os.getenv("API_CALLBACK_ENDPOINT", "/livros/atualizar/sinopse")
            api_timeout = int(os.getenv("API_TIMEOUT", "30"))
            
            url = f"{api_base_url}{api_endpoint}?id={int(livro_id)}&sinopse={quote(sinopse)}"
            
            logger.info(f"Enviando callback para: {url}")
            
            response = requests.put(
                url=url,
                timeout=api_timeout
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"Callback enviado com sucesso! Status: {response.status_code}")
            else:
                logger.warning(f"Callback retornou status inesperado: {response.status_code}")
                logger.warning(f"Resposta: {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout ao enviar callback para a API (timeout: {api_timeout}s)")
        except requests.exceptions.ConnectionError:
            logger.error("Erro de conexão ao enviar callback para a API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao enviar callback para a API: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar callback: {e}")

    def _parse_message(self, body: bytes, routing_key: str) -> Message:
        """Converte mensagem bruta em entidade de domínio assumindo JSON."""
        try:
            decoded_body = body.decode('utf-8')
            message_body = json.loads(decoded_body)
            
            return Message(
                id=str(uuid.uuid4()),
                body=message_body,
                timestamp=datetime.now(),
                routing_key=routing_key
            )
            
        except UnicodeDecodeError as e:
            logger.error(f"Erro de codificação UTF-8: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse JSON: {e}")
            logger.error(f"Conteúdo recebido: {body.decode('utf-8', errors='replace')[:200]}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao processar mensagem: {e}")
            raise

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
