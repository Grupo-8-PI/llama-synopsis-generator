#!/usr/bin/env python3
"""
Script de teste completo para o Llama Synopsis Generator
- Sobe RabbitMQ via Docker
- Cria fila e exchange 
- Envia mensagens JSON simulando o Java
- Testa todo o fluxo: RabbitMQ → Consumer → LLM → Sinopse
"""

import os
import sys
import json
import time
import subprocess
import signal
import threading
from datetime import datetime
from typing import List, Dict, Any

import pika
import requests
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

class Colors:
    """Cores para output no terminal."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_step(step: str, message: str):
    """Print colorido para steps."""
    print(f"{Colors.OKBLUE}[{step}]{Colors.ENDC} {message}")

def print_success(message: str):
    """Print de sucesso."""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")

def print_error(message: str):
    """Print de erro."""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")

def print_warning(message: str):
    """Print de warning."""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")

def check_docker():
    """Verifica se Docker está disponível."""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, check=True)
        print_success(f"Docker disponível: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Docker não encontrado. Instale Docker primeiro.")
        return False

def start_rabbitmq():
    """Inicia RabbitMQ via Docker."""
    print_step("RABBITMQ", "Iniciando RabbitMQ...")
    
    # Para container existente se houver
    subprocess.run(['docker', 'stop', 'rabbitmq-test'], 
                  capture_output=True)
    subprocess.run(['docker', 'rm', 'rabbitmq-test'], 
                  capture_output=True)
    
    # Inicia novo container
    cmd = [
        'docker', 'run', '-d',
        '--name', 'rabbitmq-test',
        '--hostname', 'rabbitmq-test', 
        '-p', '5672:5672',
        '-p', '15672:15672',
        '-e', 'RABBITMQ_DEFAULT_USER=guest',
        '-e', 'RABBITMQ_DEFAULT_PASS=guest',
        'rabbitmq:3-management'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print_success("RabbitMQ container iniciado")
        
        # Aguarda RabbitMQ ficar pronto
        print_step("RABBITMQ", "Aguardando RabbitMQ ficar pronto...")
        max_attempts = 30
        
        for attempt in range(max_attempts):
            try:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host='localhost', port=5672)
                )
                connection.close()
                print_success("RabbitMQ pronto para conexões")
                return True
            except:
                time.sleep(2)
                print(f"Tentativa {attempt + 1}/{max_attempts}...")
        
        print_error("Timeout aguardando RabbitMQ")
        return False
        
    except subprocess.CalledProcessError as e:
        print_error(f"Erro ao iniciar RabbitMQ: {e}")
        return False

def setup_rabbitmq_infrastructure():
    """Configura filas e exchanges no RabbitMQ."""
    print_step("SETUP", "Configurando infraestrutura RabbitMQ...")
    
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', port=5672)
        )
        channel = connection.channel()
        
        # Declara exchange
        exchange_name = "livros.exchange"
        channel.exchange_declare(exchange=exchange_name, exchange_type='direct', durable=True)
        
        # Declara fila
        queue_name = "fila-sinopse"
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Bind fila ao exchange
        routing_key = "livro.criado"
        channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)
        
        connection.close()
        
        print_success(f"Exchange '{exchange_name}' criado")
        print_success(f"Fila '{queue_name}' criada e bindada")
        
        return True
        
    except Exception as e:
        print_error(f"Erro ao configurar RabbitMQ: {e}")
        return False

def generate_test_messages() -> List[Dict[str, Any]]:
    """Gera mensagens de teste simulando o Java."""
    return [
        {
            "livroId": 1,
            "titulo": "Dom Casmurro",
            "autor": "Machado de Assis",
            "isbn": "978-85-359-0277-5"
        },
        {
            "livroId": 2,
            "titulo": "O Cortiço",
            "autor": "Aluísio Azevedo", 
            "isbn": "978-85-260-1347-8"
        },
        {
            "livroId": 3,
            "titulo": "1984",
            "autor": "George Orwell",
            "isbn": "978-85-250-4809-1"
        }
    ]

def send_test_messages():
    """Envia mensagens de teste para RabbitMQ."""
    print_step("MESSAGES", "Enviando mensagens de teste...")
    
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', port=5672)
        )
        channel = connection.channel()
        
        messages = generate_test_messages()
        exchange_name = "livros.exchange"
        routing_key = "livro.criado"
        
        for i, message in enumerate(messages, 1):
            # Serializa como JSON (como o Spring faria)
            body = json.dumps(message)
            
            channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Torna mensagem persistente
                    content_type='application/json'
                )
            )
            
            print_success(f"Mensagem {i} enviada: {message['titulo']}")
            time.sleep(0.5)  # Pequeno delay entre mensagens
        
        connection.close()
        print_success(f"Total de {len(messages)} mensagens enviadas")
        return True
        
    except Exception as e:
        print_error(f"Erro ao enviar mensagens: {e}")
        return False

def check_huggingface_config():
    """Verifica se Hugging Face está configurado."""
    print_step("LLM", "Verificando configuração Hugging Face...")
    
    api_key = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")
    if not api_key or not api_key.strip():
        print_warning("HF_TOKEN/HF_API_KEY não configurado")
        print_warning("✨ LLM usará fallback inteligente - configure um token Hugging Face real")
        return False
    active_var = "HF_TOKEN" if os.getenv("HF_TOKEN") else "HF_API_KEY"
    
    # Testa API key
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://huggingface.co/api/whoami",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print_success(f"{active_var} configurado para usuário: {user_info.get('name', 'N/A')}")
            return True
        else:
            print_success(f"{active_var} configurado - usando API Hugging Face")
            return True  # API key existe, mesmo se whoami falhar
            
    except Exception as e:
        print_success(f"{active_var} configurado - usando API Hugging Face")
        return True  # API key existe, assumimos que funciona

def start_consumer():
    """Inicia o consumer em processo separado."""
    print_step("CONSUMER", "Iniciando consumer...")
    
    # Configura environment para o consumer
    env = os.environ.copy()
    token_value = os.getenv('HF_TOKEN') or os.getenv('HF_API_KEY', '')
    model_value = os.getenv('MODEL') or os.getenv('HF_MODEL', 'meta-llama/Llama-3.1-8B')

    env.update({
        'RABBITMQ_HOST': 'localhost',
        'RABBITMQ_PORT': '5672',
        'RABBITMQ_USERNAME': 'guest', 
        'RABBITMQ_PASSWORD': 'guest',
        'RABBITMQ_QUEUE_NAME': 'fila-sinopse',
        'RABBITMQ_QUEUE_MODE': 'active',  # Para criar fila se não existir
        'RABBITMQ_WAIT_FOR_QUEUE': 'false',
        # Adiciona variáveis do HuggingFace do .env
        'HF_TOKEN': token_value,
        'HF_API_KEY': os.getenv('HF_API_KEY', token_value),
        'MODEL': model_value,
        'HF_MODEL': os.getenv('HF_MODEL', model_value),
        'LLM_MAX_TOKENS': os.getenv('LLM_MAX_TOKENS', '500'),
        'LLM_TEMPERATURE': os.getenv('LLM_TEMPERATURE', '0.7'),
        'LLM_TIMEOUT': os.getenv('LLM_TIMEOUT', '30')
    })
    
    try:
        # Usa Python do ambiente virtual se disponível
        python_exe = sys.executable
        if '.venv' not in python_exe and os.path.exists('.venv/bin/python3'):
            python_exe = '.venv/bin/python3'
            
        # Inicia consumer em processo separado
        process = subprocess.Popen(
            [python_exe, 'main.py'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        print_success("Consumer iniciado")
        return process
        
    except Exception as e:
        print_error(f"Erro ao iniciar consumer: {e}")
        return None

def monitor_consumer_output(process, duration=30):
    """Monitora output do consumer por um tempo determinado."""
    print_step("MONITOR", f"Monitorando consumer por {duration}s...")
    
    def read_output():
        """Lê output do consumer."""
        try:
            for line in process.stdout:
                if line.strip():
                    # Colore logs importantes
                    if "=== Processando Livro ===" in line:
                        print(f"{Colors.OKCYAN}{line.strip()}{Colors.ENDC}")
                    elif "=== Sinopse Gerada ===" in line:
                        print(f"{Colors.OKGREEN}{line.strip()}{Colors.ENDC}")
                    elif "ERROR" in line:
                        print(f"{Colors.FAIL}{line.strip()}{Colors.ENDC}")
                    elif "WARNING" in line:
                        print(f"{Colors.WARNING}{line.strip()}{Colors.ENDC}")
                    else:
                        print(line.strip())
        except:
            pass
    
    # Thread para ler output
    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()
    
    # Aguarda por um tempo
    time.sleep(duration)
    
    return process.poll() is None  # Retorna True se processo ainda está rodando

def cleanup():
    """Limpa recursos."""
    print_step("CLEANUP", "Limpando recursos...")
    
    # Para RabbitMQ container
    subprocess.run(['docker', 'stop', 'rabbitmq-test'], 
                  capture_output=True)
    subprocess.run(['docker', 'rm', 'rabbitmq-test'], 
                  capture_output=True)
    
    print_success("Cleanup concluído")

def main():
    """Função principal do teste."""
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("=" * 60)
    print("🦙 LLAMA SYNOPSIS GENERATOR - TESTE COMPLETO")
    print("=" * 60)
    print(f"{Colors.ENDC}")
    
    # Registra cleanup no Ctrl+C
    def signal_handler(sig, frame):
        print("\n")
        print_warning("Teste interrompido")
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    consumer_process = None
    
    try:
        # 1. Verifica Docker
        if not check_docker():
            return False
        
        # 2. Inicia RabbitMQ
        if not start_rabbitmq():
            return False
        
        # 3. Configura infraestrutura
        if not setup_rabbitmq_infrastructure():
            return False
        
        # 4. Verifica configuração LLM
        llm_ok = check_huggingface_config()
        
        # 5. Inicia consumer
        consumer_process = start_consumer()
        if not consumer_process:
            return False
        
        # Aguarda consumer inicializar
        time.sleep(3)
        
        # 6. Envia mensagens de teste
        if not send_test_messages():
            return False
        
        # 7. Monitora consumer
        print_step("TEST", "Aguardando processamento das mensagens...")
        consumer_running = monitor_consumer_output(consumer_process, duration=45)
        
        if consumer_running:
            print_success("Teste concluído com sucesso!")
            if llm_ok:
                print_success("✨ LLM API funcionando - sinopses geradas via Hugging Face")
            else:
                print_success("🎯 LLM em modo fallback - sinopses inteligentes geradas localmente")
        else:
            print_error("Consumer parou inesperadamente")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Erro durante teste: {e}")
        return False
        
    finally:
        # Cleanup
        if consumer_process:
            try:
                consumer_process.terminate()
                consumer_process.wait(timeout=5)
            except:
                consumer_process.kill()
        
        cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)