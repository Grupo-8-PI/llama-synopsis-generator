#!/usr/bin/env python3
"""
Script de teste simples - assume RabbitMQ já rodando
Envia mensagens JSON simulando o Java para testar o consumer
"""

import json
import time
import pika
from dotenv import load_dotenv

load_dotenv()

def send_test_messages():
    """Envia mensagens de teste para RabbitMQ."""
    # Mensagens simulando o Java
    test_books = [
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
    
    try:
        # Conecta ao RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', port=5672)
        )
        channel = connection.channel()
        
        # Cria fila se não existir
        queue_name = "fila-sinopse"
        channel.queue_declare(queue=queue_name, durable=True)
        
        print("📤 Enviando mensagens de teste...")
        print("=" * 50)
        
        for i, book in enumerate(test_books, 1):
            # Serializa como JSON
            message_body = json.dumps(book)
            
            # Envia mensagem
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistente
                    content_type='application/json'
                )
            )
            
            print(f"✅ Mensagem {i}: {book['titulo']} - {book['autor']}")
            time.sleep(1)
        
        connection.close()
        
        print("=" * 50)
        print(f"🎉 {len(test_books)} mensagens enviadas com sucesso!")
        print("\n💡 Agora execute o consumer em outro terminal:")
        print("   python main.py")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("\n🔧 Verifique se:")
        print("   - RabbitMQ está rodando (localhost:5672)")
        print("   - Credenciais estão corretas no .env")

if __name__ == "__main__":
    send_test_messages()