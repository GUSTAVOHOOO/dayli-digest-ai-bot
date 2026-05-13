# 🤖 AI Daily Digest Bot

Bot de newsletter automatizado 100% self-hosted que coleta, processa e distribui um boletim diário sobre IA e computação via Telegram.

## 🏗️ Arquitetura

O bot utiliza uma arquitetura baseada em filas (Celery) para processamento assíncrono e resiliente.

```
[07:00] Celery Beat → Redis Queues
         │
         ├── Queue: collect   (Coleta de feeds Atom/RSS)
         ├── Queue: extract   (Extração de texto via Jina AI/Trafilatura)
         ├── Queue: summarize (Sumarização via Ollama LLM – Uso de GPU)
         ├── Queue: score     (Pontuação de relevância baseada em keywords)
         └── Queue: dispatch  (Envio formatado para o Telegram)
```

## 📋 Requisitos

- **Python 3.11+**
- **Docker + Docker Compose**
- **GPU NVIDIA** (Recomendado para rodar o Ollama/Qwen com performance aceitável)
- **Redis 7.2** (Broker e Backend)
- **8GB RAM** (Mínimo recomendado)

## 🚀 Quick Start

1.  **Clone o repositório e entre no diretório:**
    ```bash
    cd digestbot
    ```

2.  **Configure as variáveis de ambiente:**
    ```bash
    cp .env.example .env
    # Edite o .env com seu TELEGRAM_BOT_TOKEN e ADMIN_CHAT_ID
    ```

3.  **Execute o script de setup:**
    ```bash
    # Linux/macOS
    bash scripts/setup.sh
    
    # Windows (PowerShell)
    .\scripts\setup.ps1
    ```

4.  **Verifique se os serviços estão rodando:**
    ```bash
    docker-compose ps
    ```

5.  **Teste o Health Check:**
    ```bash
    curl http://localhost:18080/health
    ```

## ⚙️ Configuração (.env)

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Token oficial do seu bot via @BotFather | `123456:ABC-...` |
| `ADMIN_CHAT_ID` | Seu ID no Telegram para comandos restritos | `123456789` |
| `OLLAMA_API_URL` | URL da API do Ollama (serviço interno) | `http://ollama:11434` |
| `REDIS_URL` | URL do banco Redis | `redis://redis:6379/0` |
| `MIN_SCORE_THRESHOLD` | Pontuação mínima para o artigo ser enviado | `3` |
| `SQLITE_DB_PATH` | Caminho do banco SQLite | `data/articles.db` |

## 🤖 Comandos do Bot

| Comando | Descrição | Restrição |
|---------|-----------|-----------|
| `/start` | Mensagem de boas-vindas e ajuda | Público |
| `/status` | Status do último digest e estatísticas de hoje | Público |
| `/test` | Dispara o envio de um digest imediato para o chat | **Admin** |
| `/retry_failed` | Move artigos da DLQ de volta para o processamento | **Admin** |

## 📊 Observabilidade e Logs

Os logs são gerados em formato JSON em `logs/digest.log` e possuem rotação automática.

- **Métricas:** Filtre por `"metric"` para ver contadores de artigos.
- **DLQ:** Artigos com falha crítica são registrados em `logs/failed_articles.jsonl`.
- **Health:** Endpoint disponível em `http://localhost:18080/health`.

## 🧪 Testes

Para rodar a suíte de testes completa:
```bash
cd digestbot
python -m pytest tests/ -v --cov=src
```

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
