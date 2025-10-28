import os
import requests
import json
import time
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    @abstractmethod
    def generate_synopsis(self, titulo: str, autor: str, isbn: str) -> str:
        pass


class HuggingFaceLLMAdapter(LLMAdapter):
    
    def __init__(self):
        self.api_key = os.getenv("HF_API_KEY")
        self.model = os.getenv("HF_MODEL", "meta-llama/Llama-2-7b-chat-hf")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "500"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        self.base_url = f"https://api-inference.huggingface.co/models/{self.model}"
        
        self.api_available = bool(self.api_key and self.api_key.strip())
        if not self.api_available:
            logger.warning("HF_API_KEY não configurada - usando apenas fallback")
    
    def generate_synopsis(self, titulo: str, autor: str, isbn: str) -> str:
        if not self.api_available:
            logger.info(f"Usando fallback para '{titulo}' (API não configurada)")
            return self._fallback_synopsis(titulo, autor)
        
        prompt = self._build_prompt(titulo, autor, isbn)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": self.max_tokens,
                "temperature": self.temperature,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Gerando sinopse para '{titulo}' via API (tentativa {attempt + 1})")
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 503:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Modelo carregando, aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code == 401:
                    logger.error("API key inválida - usando fallback")
                    self.api_available = False
                    return self._fallback_synopsis(titulo, autor)
                
                response.raise_for_status()
                result = response.json()
                
                if isinstance(result, list) and len(result) > 0:
                    synopsis = result[0].get("generated_text", "").strip()
                    if synopsis:
                        logger.info("Sinopse gerada com sucesso via API")
                        return self._clean_synopsis(synopsis)
                
                logger.warning("Resposta vazia do modelo - usando fallback")
                return self._fallback_synopsis(titulo, autor)
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout na tentativa {attempt + 1}")
                if attempt == max_retries - 1:
                    logger.warning("Timeout final - usando fallback")
                    return self._fallback_synopsis(titulo, autor)
                time.sleep(retry_delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro na requisição: {e}")
                if attempt == max_retries - 1:
                    logger.warning("Erro final de requisição - usando fallback")
                    return self._fallback_synopsis(titulo, autor)
                time.sleep(retry_delay)
                
            except Exception as e:
                logger.error(f"Erro inesperado: {e}")
                return self._fallback_synopsis(titulo, autor)
        
        return self._fallback_synopsis(titulo, autor)
    
    def _build_prompt(self, titulo: str, autor: str, isbn: str) -> str:
        return f"""[INST] Você é um especialista em literatura. Crie uma sinopse envolvente e concisa para um livro com as seguintes informações:

Título: {titulo}
Autor: {autor}
ISBN: {isbn}

A sinopse deve:
- Ser atrativa e despertar curiosidade
- Ter entre 100-200 palavras
- Capturar a essência da obra
- Ser adequada para divulgação

Sinopse: [/INST]"""
    
    def _clean_synopsis(self, synopsis: str) -> str:
        synopsis = synopsis.replace("[INST]", "").replace("[/INST]", "")
        synopsis = synopsis.replace("Sinopse:", "").strip()
        
        if len(synopsis) > 1000:
            synopsis = synopsis[:997] + "..."
        
        return synopsis
    
    def _fallback_synopsis(self, titulo: str, autor: str) -> str:
        """Sinopse de fallback quando LLM falha."""
        fallback_templates = {
            "machado de assis": f"'{titulo}' é uma obra clássica de {autor} que explora com maestria os aspectos mais profundos da natureza humana, apresentando personagens complexos e uma narrativa rica em reflexões sobre a sociedade brasileira do século XIX.",
            "george orwell": f"'{titulo}' é uma obra distópica de {autor} que apresenta uma visão crítica e provocativa sobre sistemas totalitários, controle social e a manipulação da verdade, permanecendo extremamente relevante nos dias atuais.",
            "aluísio azevedo": f"'{titulo}' é um romance naturalista de {autor} que retrata com realismo a vida urbana brasileira, explorando as condições sociais e os contrastes da sociedade com uma narrativa envolvente e crítica."
        }
        
        autor_lower = autor.lower()
        for key, template in fallback_templates.items():
            if key in autor_lower:
                return template
        
        return f"'{titulo}' é uma obra de {autor} que promete envolver o leitor em uma narrativa única e cativante. Uma leitura imperdível para apreciar o talento literário do autor."



class LLMService:
    """Serviço principal para geração de sinopses usando Hugging Face."""
    
    def __init__(self):
        try:
            self.adapter = HuggingFaceLLMAdapter()
            if self.adapter.api_available:
                logger.info("LLM Service inicializado com Hugging Face API")
            else:
                logger.info("LLM Service inicializado em modo fallback (API não configurada)")
        except Exception as e:
            logger.error(f"Erro ao inicializar LLM Service: {e}")
            raise
    
    def generate_book_synopsis(self, titulo: str, autor: str, isbn: str) -> str:
        """Gera sinopse para um livro."""
        return self.adapter.generate_synopsis(titulo, autor, isbn)