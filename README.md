# 🦙 Llama Synopsis Generator - RabbitMQ Consumer

Um consumer RabbitMQ robusto e resiliente para processamento de mensagens com retry automático, circuit breaker e múltiplos modos de operação.

## 📋 Índice

- [🚀 Início Rápido](#-início-rápido)
- [⚙️ Configuração](#️-configuração)
- [🔧 Modos de Operação](#-modos-de-operação)
- [🔄 Sistema de Retry](#-sistema-de-retry)
- [📊 Monitoramento e Logs](#-monitoramento-e-logs)
- [🏃‍♂️ Executando](#️-executando)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [🦙 Configuração LLM](#-configuração-llm)

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.8+
- RabbitMQ server
- Biblioteca `pika` para RabbitMQ

### Instalação Rápida

```bash
# Clone o repositório
git clone <repository-url>
cd llama-synopsis-generator

# Instale dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas configurações (RabbitMQ + LLM)

# Execute o consumer
python main.py
```

## ⚙️ Configuração

### Configuração Básica (.env)

```bash
# Conexão RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VIRTUAL_HOST=/
RABBITMQ_QUEUE_NAME=synopsis_queue

# Configurações de Performance
RABBITMQ_PREFETCH_COUNT=1

# Sistema de Retry
RABBITMQ_MAX_RETRIES=10
RABBITMQ_INITIAL_RETRY_DELAY=1.0
RABBITMQ_MAX_RETRY_DELAY=60.0
RABBITMQ_FAILURE_THRESHOLD=5
RABBITMQ_RECOVERY_TIMEOUT=30.0

# Modo de Operação da Fila
RABBITMQ_QUEUE_MODE=passive
RABBITMQ_WAIT_FOR_QUEUE=true
RABBITMQ_QUEUE_CHECK_INTERVAL=5.0
```

### Variáveis de Configuração Explicadas

| Variável | Default | Descrição |
|----------|---------|-----------|
| `RABBITMQ_HOST` | `localhost` | Endereço do servidor RabbitMQ |
| `RABBITMQ_PORT` | `5672` | Porta do RabbitMQ |
| `RABBITMQ_USERNAME` | `guest` | Usuário para autenticação |
| `RABBITMQ_PASSWORD` | `guest` | Senha para autenticação |
| `RABBITMQ_QUEUE_NAME` | `default_queue` | Nome da fila a consumir |
| `RABBITMQ_PREFETCH_COUNT` | `1` | Msgs simultâneas por consumer |
| `RABBITMQ_MAX_RETRIES` | `10` | Máximo de tentativas de reconexão |
| `RABBITMQ_INITIAL_RETRY_DELAY` | `1.0` | Delay inicial entre tentativas (seg) |
| `RABBITMQ_MAX_RETRY_DELAY` | `60.0` | Delay máximo entre tentativas (seg) |
| `RABBITMQ_FAILURE_THRESHOLD` | `5` | Falhas para ativar circuit breaker |
| `RABBITMQ_RECOVERY_TIMEOUT` | `30.0` | Tempo para testar recuperação (seg) |
| `RABBITMQ_QUEUE_MODE` | `passive` | Modo: `passive` ou `active` |
| `RABBITMQ_WAIT_FOR_QUEUE` | `true` | Aguardar fila aparecer |
| `RABBITMQ_QUEUE_CHECK_INTERVAL` | `5.0` | Intervalo de verificação da fila (seg) |

## 🔧 Modos de Operação

### 🔍 Passive Mode (Recomendado para APIs existentes)

**Quando usar:**
- Sua API já cria e gerencia as filas
- Múltiplos consumers compartilham a mesma fila
- Ambiente de produção com infraestrutura gerenciada

**Configuração:**
```bash
RABBITMQ_QUEUE_MODE=passive
RABBITMQ_WAIT_FOR_QUEUE=true
RABBITMQ_QUEUE_CHECK_INTERVAL=5.0
```

**Comportamento:**
- ✅ **Apenas verifica** se a fila existe (nunca cria)
- ✅ **Aguarda** a fila ficar disponível
- ✅ **Monitora** continuamente a saúde da fila
- ✅ **Health check** com contadores de mensagens

**Exemplo de logs:**
```
INFO - Queue mode: passive
INFO - Waiting for queue 'synopsis_queue' to be available...
INFO - Found existing queue 'synopsis_queue' with 3 messages
INFO - Started consuming from queue 'synopsis_queue'
```

### 🏗️ Active Mode (Modo tradicional)

**Quando usar:**
- Consumer independente
- Desenvolvimento local
- Consumer responsável pela própria infraestrutura

**Configuração:**
```bash
RABBITMQ_QUEUE_MODE=active
```

**Comportamento:**
- ✅ **Cria** a fila se não existir
- ✅ **Declara** a fila como durável
- ✅ **Gerencia** a infraestrutura

## 🔄 Sistema de Retry

### Características

#### 🔄 **Exponential Backoff**
- Delay inicial: 1 segundo (configurável)
- Cresce exponencialmente: `delay = initial * (2 ^ tentativa)`
- Máximo: 60 segundos (configurável)

#### ⚡ **Circuit Breaker**
- **CLOSED**: Operação normal
- **OPEN**: Muitas falhas, pausa tentativas temporariamente
- **HALF_OPEN**: Testa se o serviço se recuperou

#### 🛡️ **Graceful Shutdown**
- Captura sinais SIGINT (Ctrl+C) e SIGTERM
- Para consumer de forma controlada
- Limpa conexões adequadamente

### Fluxo de Recuperação

```
1. Falha detectada → Registra no circuit breaker
2. Retry com delay exponencial
3. Muitas falhas → Circuit breaker OPEN
4. Aguarda timeout → Testa recuperação (HALF_OPEN)
5. Sucesso → Circuit breaker CLOSED
6. Operação normal retomada
```

## 📊 Monitoramento e Logs

### Níveis de Log

- **INFO**: Eventos importantes (conexões, estados)
- **WARNING**: Problemas temporários (reconexões)
- **ERROR**: Falhas que requerem atenção
- **DEBUG**: Detalhes técnicos para troubleshooting

### Logs Importantes

#### Inicialização
```
INFO - Starting RabbitMQ consumer with auto-retry capability
INFO - Queue mode: passive
INFO - Target queue: synopsis_queue
INFO - Wait for queue: true
```

#### Operação Normal
```
INFO - Connected successfully to RabbitMQ at localhost:5672
INFO - Found existing queue 'synopsis_queue' with 3 messages
INFO - Started consuming from queue 'synopsis_queue'
```

#### Recuperação de Falhas
```
WARNING - Connection lost during consuming: Connection closed by client
INFO - Reconnecting in 2.0s...
INFO - Connection successful, circuit breaker CLOSED
```

#### Circuit Breaker
```
WARNING - Circuit breaker OPEN after 5 failures
INFO - Circuit breaker transitioning to HALF_OPEN
INFO - Connection successful, circuit breaker CLOSED
```

## 🏃‍♂️ Executando

### Desenvolvimento Local

```bash
# Subir RabbitMQ local (Docker)
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# Configurar ambiente
cp .env.example .env
# Editar .env se necessário

# Executar consumer
python main.py
```

### Produção

```bash
# Configurar variáveis de ambiente de produção
export RABBITMQ_HOST=your-rabbitmq-server
export RABBITMQ_USERNAME=your-user
export RABBITMQ_PASSWORD=your-password
export RABBITMQ_QUEUE_NAME=your-queue
export RABBITMQ_QUEUE_MODE=passive

# Executar com logging estruturado
python main.py 2>&1 | tee consumer.log
```

### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Testando o Sistema

#### 🚀 Teste Completo (com Docker)
Script que sobe infraestrutura completa e testa tudo:

```bash
# Instala dependências
pip install -r requirements.txt

# Executa teste completo (sobe RabbitMQ + testa tudo)
python test_full_integration.py
```

#### 📤 Teste Simples (RabbitMQ já rodando)
Para enviar mensagens rapidamente:

```bash
# Terminal 1: Enviar mensagens de teste
python test_messages.py

# Terminal 2: Executar consumer
python main.py
```

#### 🔧 Teste Manual com Docker
```bash
# Subir RabbitMQ
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# Executar consumer
python main.py

# Enviar mensagens (outro terminal)
python test_messages.py
```

## 🛠️ Troubleshooting

### Problemas Comuns

#### ❌ Consumer não conecta

**Sintomas:**
```
ERROR - Connection failed: [Errno 111] Connection refused
WARNING - Retrying connection in 2.0s (attempt 2/10)
```

**Soluções:**
1. Verificar se RabbitMQ está rodando
2. Validar host/porta no `.env`
3. Verificar credenciais
4. Checar firewall/rede

#### ❌ Fila não encontrada (Passive Mode)

**Sintomas:**
```
DEBUG - Queue synopsis_queue does not exist or is not accessible
INFO - Waiting for queue 'synopsis_queue' to be available...
```

**Soluções:**
1. Aguardar API criar a fila (comportamento normal)
2. Verificar nome da fila no `.env`
3. Confirmar que producer está rodando
4. Mudar para `active` mode temporariamente para debug

#### ❌ Circuit Breaker sempre OPEN

**Sintomas:**
```
WARNING - Circuit breaker OPEN after 5 failures
```

**Soluções:**
1. Aumentar `RABBITMQ_FAILURE_THRESHOLD`
2. Verificar conectividade de rede
3. Validar recursos do RabbitMQ server
4. Ajustar `RABBITMQ_RECOVERY_TIMEOUT`

#### ❌ Mensagens não processadas

**Sintomas:**
```
ERROR - Error processing message: [Errno] ...
WARNING - Could not send NACK - connection may be closed
```

**Soluções:**
1. Verificar dependências do message service
2. Validar estrutura das mensagens
3. Checar logs do callback de processamento
4. Testar com mensagens simples

### Debugging

#### Habilitar logs debug
```python
# No início do main.py
logging.getLogger().setLevel(logging.DEBUG)
```

#### Testar conectividade
```bash
# Teste básico de conexão
telnet localhost 5672

# Management UI (se disponível)
curl http://localhost:15672/api/overview
```

#### Verificar fila manualmente
```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Verificar se fila existe
try:
    method = channel.queue_declare(queue='synopsis_queue', passive=True)
    print(f"Queue exists with {method.method.message_count} messages")
except:
    print("Queue does not exist")
```

### Configurações de Performance

#### Para alto volume de mensagens:
```bash
RABBITMQ_PREFETCH_COUNT=10          # Mais mensagens simultâneas
RABBITMQ_MAX_RETRY_DELAY=10.0       # Recovery mais rápido
RABBITMQ_QUEUE_CHECK_INTERVAL=1.0   # Verificação mais frequente
```

#### Para máxima estabilidade:
```bash
RABBITMQ_PREFETCH_COUNT=1           # Uma msg por vez
RABBITMQ_MAX_RETRIES=50             # Mais tentativas
RABBITMQ_FAILURE_THRESHOLD=10       # Tolera mais falhas
RABBITMQ_RECOVERY_TIMEOUT=60.0      # Recovery mais conservador
```

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Sua API       │    │   RabbitMQ       │    │   Consumer      │
│   (Producer)    │───▶│   Server         │───▶│   (Este App)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        │ Cria fila            │ Gerencia msgs         │ Processa msgs
        │ Publica msgs         │ Roteamento            │ Auto-retry
        │                      │ Persistência          │ Circuit breaker
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 🦙 Configuração LLM

O consumer integra com serviços LLM para gerar sinopses automaticamente. Veja [LLM_SETUP.md](LLM_SETUP.md) para configuração detalhada.

### Configuração LLM:

#### 🤗 Hugging Face (Gratuito)
```bash
HF_API_KEY=sua-chave-huggingface
HF_MODEL=meta-llama/Llama-2-7b-chat-hf
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.7
```

1. Crie conta em [huggingface.co](https://huggingface.co)
2. Gere token em Settings → Access Tokens
3. Configure `HF_API_KEY` no `.env`

### Fluxo Completo:
```
Java API → RabbitMQ → Consumer → LLM → Sinopse Gerada
```

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para detalhes.