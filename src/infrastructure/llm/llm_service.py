import os
import logging
from abc import ABC, abstractmethod
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    @abstractmethod
    def generate_synopsis(self, titulo: str, autor: str, isbn: str) -> str:
        pass


class HuggingFaceLLMAdapter(LLMAdapter):
    
    def __init__(self):
        token = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")
        if not token:
            raise ValueError("HF_TOKEN ou HF_API_KEY não configurado")
        
        self.client = InferenceClient(api_key=token)
        self.model = os.getenv(
            "MODEL",
            os.getenv("HF_MODEL", "nvidia/Llama-3_1-Nemotron-Ultra-253B-v1:nebius")
        )
        
    def generate_synopsis(self, titulo: str, autor: str, isbn: str) -> str:
        try:
            content = f"Escreva uma sinopse em português para o livro '{titulo}' de {autor} em UMA ÚNICA FRASE. Sinopse:"
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar sinopse: {e}")
            return f"'{titulo}' é uma obra de {autor} que promete envolver o leitor em uma narrativa única e cativante."


class LLMService:
    
    def __init__(self):
        try:
            self.adapter = HuggingFaceLLMAdapter()
            logger.info("LLM Service inicializado com HuggingFace InferenceClient")
        except Exception as e:
            logger.error(f"Erro ao inicializar LLM Service: {e}")
            raise
    
    def generate_book_synopsis(self, titulo: str, autor: str, isbn: str) -> str:
        return self.adapter.generate_synopsis(titulo, autor, isbn)