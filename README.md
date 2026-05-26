# teste-python

API em FastAPI + GraphQL (Strawberry) para cadastro de clientes e processamento de webhooks do Pipefy.

---

## Pré-requisitos

- Python 3.11+
- Docker e Docker Compose

---

## Execução local

### 1. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` com os valores reais. O único campo obrigatório para rodar localmente é `DATABASE_URL`. As credenciais do Pipefy (`PIPEFY_TOKEN`, `PIPEFY_PIPE_ID`) são opcionais — sem elas o serviço loga um aviso e pula as chamadas ao Pipefy.

### 2. Suba o banco de dados

```bash
docker compose up db -d
```

Ou suba tudo (banco + API) de uma vez:

```bash
docker compose up
```

### 3. Execute as migrações

```bash
alembic upgrade head
```

### 4. Inicie a API

```bash
# com hot-reload
python -m uvicorn main:app --reload

# ou diretamente
python main.py
```

A API ficará disponível em `http://localhost:8000`.

---

## Execução dos testes

Os testes de integração exigem um Postgres acessível (use `docker compose up db -d`).

```bash
# todos os testes
pytest

# arquivo específico
pytest tests/test_create_client.py
pytest tests/test_webhook.py
pytest tests/test_pipefy_service.py

# com relatório de cobertura
pytest --cov

# um teste específico pelo nome
pytest tests/test_create_client.py::TestCreateClient::test_valid_payload_returns_client
```

O `conftest.py` cria e destrói automaticamente o banco `test_appdb` a cada sessão de testes; cada teste recebe as tabelas truncadas via fixture `clean_db`.

---

## Exemplos de requisição

### Endpoint 1 — Criar cliente (GraphQL)

`POST /graphql`

```bash
curl -s -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { createClient(input: { clientName: \"Maria Silva\" clientEmail: \"maria@exemplo.com\" requestType: \"Abertura de Conta\" patrimonyValue: 250000 }) { id name email requestType patrimonyValue status priority } }"
  }' | python3 -m json.tool
```

Resposta esperada:

```json
{
  "data": {
    "createClient": {
      "id": 1,
      "name": "Maria Silva",
      "email": "maria@exemplo.com",
      "requestType": "Abertura de Conta",
      "patrimonyValue": 250000.0,
      "status": "Aguardando Análise",
      "priority": null
    }
  }
}
```

Health check:

```bash
curl -s -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ health }"}' | python3 -m json.tool
```

---

### Endpoint 2 — Webhook Pipefy (card atualizado)

`POST /webhooks/pipefy/card-updated`

Esse endpoint é chamado pelo Pipefy quando um card é atualizado. Ele atualiza o status e a prioridade do cliente no banco e espelha a mudança de volta no Pipefy.

```bash
curl -s -X POST http://localhost:8000/webhooks/pipefy/card-updated \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_abc123",
    "card_id": "card_456",
    "client_email": "maria@exemplo.com",
    "timestamp": "2026-05-26T12:00:00Z"
  }' | python3 -m json.tool
```

Resposta esperada (primeiro processamento):

```json
{
  "status": "processed",
  "event_id": "evt_abc123",
  "priority": "prioridade_alta"
}
```

Resposta para evento duplicado (mesmo `event_id`):

```json
{
  "status": "duplicate",
  "event_id": "evt_abc123"
}
```

> **Regra de prioridade:** `patrimony_value >= 200.000` → `prioridade_alta`; abaixo disso → `prioridade_normal`.

---

## Visão de Produção na AWS

A estrutura atual (FastAPI + PostgreSQL síncrono) funciona bem em baixa escala, mas apresenta gargalos quando o volume de webhooks e criações de clientes cresce. Veja como cada parte evoluiria na AWS.

### API e processamento de requisições

O aplicativo FastAPI seria containerizado e executado no **Amazon ECS (Fargate)**, eliminando a necessidade de gerenciar servidores. O **API Gateway** ficaria na frente, centralizando autenticação (chaves de API ou Cognito), throttling e logging. Para picos de tráfego, o Auto Scaling do ECS ajusta o número de containers automaticamente com base em CPU/memória.

Caso a equipe prefira eliminar completamente a gestão de infraestrutura, o endpoint GraphQL e o webhook poderiam ser migrados para funções **AWS Lambda** individualmente — cada rota se torna uma função independente, com escalonamento automático até milhares de invocações simultâneas sem configuração adicional.

### Banco de dados

O PostgreSQL local seria substituído pelo **Amazon RDS for PostgreSQL** (Multi-AZ para alta disponibilidade). Para leituras intensas — por exemplo, consultas de clientes em relatórios — um **Read Replica** absorve o tráfego de leitura sem impactar o banco principal.

Se o volume de clientes crescer muito e as consultas se tornarem mais analíticas do que transacionais, parte dos dados poderia migrar para o **DynamoDB**: a tabela `webhook_events` (usada apenas para deduplicação por `event_id`) é uma candidata natural, pois o acesso é sempre por chave primária, se beneficia do TTL automático do DynamoDB para expirar eventos antigos, e a escala é ilimitada sem impacto no PostgreSQL.

### Processamento assíncrono de webhooks

O maior ganho de escala vem de **desacoplar o recebimento do processamento**. Em vez de o endpoint `/webhooks/pipefy/card-updated` chamar o Pipefy de forma síncrona (o que torna a resposta lenta e frágil), o fluxo passaria a ser:

1. API Gateway recebe o webhook do Pipefy e publica uma mensagem no **Amazon SQS**.
2. O endpoint responde imediatamente `202 Accepted` para o Pipefy.
3. Uma função **Lambda** consome a fila SQS, aplica a lógica de prioridade e atualiza o banco e o Pipefy em background.

Esse modelo resolve três problemas ao mesmo tempo: elimina o timeout do Pipefy caso o processamento demore, oferece retentativas automáticas via SQS em caso de falha, e permite processar muitos webhooks em paralelo sem sobrecarregar o banco.

### Diagrama simplificado

```
Pipefy ──► API Gateway ──► SQS ──► Lambda (processamento)
                │                        │
                │                        ▼
                └──► ECS/Lambda     RDS PostgreSQL
                     (GraphQL)           │
                                    DynamoDB
                                  (deduplicação)
```

### Resumo das escolhas

| Componente atual       | Equivalente AWS              | Motivo principal                              |
|------------------------|------------------------------|-----------------------------------------------|
| FastAPI (processo único)| ECS Fargate ou Lambda        | Escalabilidade horizontal sem gerenciar VMs   |
| PostgreSQL local       | RDS Multi-AZ + Read Replica  | Alta disponibilidade e separação leitura/escrita |
| `webhook_events` (PG)  | DynamoDB com TTL             | Acesso por chave, escala ilimitada, expiração automática |
| Chamada síncrona Pipefy| SQS + Lambda consumidor      | Desacoplamento, retentativas, respostas rápidas |
| Sem autenticação       | API Gateway + Cognito/API Key| Rate limiting e autenticação gerenciados      |
