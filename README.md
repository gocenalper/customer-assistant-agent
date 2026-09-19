<div align="center">

# Customer Assistant Agent

### Live stock answers. Refunds with a human in the loop.

A LangGraph-powered customer assistant that queries inventory and handles refunds through a Java microservice.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Workflow-1C3C3C?style=flat-square)
![Java](https://img.shields.io/badge/Java-21-ED8B00?style=flat-square)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.0.8-6DB33F?style=flat-square&logo=springboot&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=flat-square&logo=postgresql&logoColor=white)

[Architecture](#architecture) · [Quick start](#quick-start) · [API](#api) · [Roadmap](#current-scope-and-roadmap)

</div>

---

> **User:** “Is SKU-001 in stock?”<br>
> **Assistant:** Calls the stock tool, retrieves the current quantity from PostgreSQL, and uses that data to answer.

> **User:** “Please refund order 3333…, the monitor arrived broken.”<br>
> **Assistant:** Prepares the refund. Up to TRY 200 it is executed right away; above that the conversation pauses until an operator approves or rejects it.

This small application demonstrates how an LLM uses tools to interact with a separate backend service. Python handles the conversation and tool workflow; Java owns the data and the business rules, so the model cannot bypass them.

| 💬 Conversation | 🔧 Tool calling | 💸 Refunds | 📦 Backend service | 🔎 Observability |
| :--- | :--- | :--- | :--- | :--- |
| Send messages through FastAPI | The agent calls `get_stock` and `initiate_refund` when needed | Automatic up to TRY 200, operator approval above it | Spring Boot + JDBC on PostgreSQL | Optional LangSmith tracing |

## Architecture

```mermaid
flowchart LR
    U["User / API client"] --> F["FastAPI<br/>POST /chat · :8000"]
    F --> A["LangGraph Agent<br/>GPT-5 mini"]
    O["Operator"] --> F
    A -->|Tool call| T["get_stock · initiate_refund<br/>HTTPX client"]
    T --> J["Java Stock Service<br/>Spring Boot · :8081"]
    J -->|JDBC| P[("PostgreSQL · :5433<br/>stock, orders, refunds<br/>langgraph checkpoints")]
    P --> J
    J --> T
    T -->|Tool result| A
    A -->|Final answer| F
    F --> U
    A -->|Paused threads| P
    A -. "Optional tracing" .-> L["LangSmith"]

    classDef python fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
    classDef java fill:#ecfccb,stroke:#65a30d,color:#365314
    classDef data fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
    class F,A,T python
    class J java
    class P,L data
```

The agent loop:

```mermaid
flowchart LR
    S((START)) --> M[chat_model]
    M -->|Tool call requested| T[ToolNode]
    T -->|Append result to messages| M
    T -->|Refund READY| X[execute_refund]
    T -->|Refund PENDING_APPROVAL| H[human_approval<br/>interrupt]
    H -->|Approved| X
    H -->|Rejected| M
    X --> M
    M -->|No tool call| E((END))
```

Refunds up to TRY 200 are executed automatically. Larger ones pause the graph with `interrupt()` until an operator decides through `POST /chat/{thread_id}/approval`; the Java service enforces the same rule, so execution without approval is rejected there as well. Paused threads are checkpointed to PostgreSQL (`langgraph` schema), so they survive restarts and can be resumed by any API instance. A thread's checkpoints are deleted once its request finishes; only threads waiting for approval remain.

`bind_tools` makes tools available to the model. `ToolNode` executes the selected tool, and the model uses its result to produce a final answer. Each `/chat` request starts with a fresh message history; conversation memory across requests is not implemented yet.

## Quick start

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Java 21, Maven, a running Docker/OrbStack instance, and an OpenAI API key.

### 1 · Set up the project

```bash
git clone git@github.com:gocenalper/customer-assistant-agent.git
cd customer-assistant-agent
uv sync --locked
cp .env.example .env
```

Replace `OPENAI_API_KEY` in `.env` with your own key. This file is excluded from Git.

### 2 · Start PostgreSQL and the Java service

From the project root, in your first terminal:

```bash
cd stock-service
docker compose up -d
mvn spring-boot:run
```

The Java application creates the stock, order, and refund tables on startup. PostgreSQL data persists in a Docker volume; the tables are empty on a fresh installation.

### 3 · Add sample data

Once the Java service has started, open a second terminal at the project root:

```bash
docker compose -f stock-service/compose.yaml exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U stock -d stockdb <<'SQL'
INSERT INTO stock (sku, name, quantity) VALUES
    ('SKU-001', 'Mechanical Keyboard', 25),
    ('SKU-002', 'Wireless Mouse', 40),
    ('SKU-003', '27-inch Monitor', 12),
    ('SKU-004', 'USB-C Hub', 18),
    ('SKU-005', 'Bluetooth Headphones', 0)
ON CONFLICT (sku) DO NOTHING;
SQL
```

Running this command again leaves existing products unchanged, including their names and quantities. `SKU-005` starts with zero stock to demonstrate an out-of-stock response.

To try refunds, also load three demo orders of TRY 150, 200, and 250:

```bash
docker compose -f stock-service/compose.yaml exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U stock -d stockdb < stock-service/demo-refunds.sql
```

### 4 · Start the Python API

From the project root:

```bash
uv run uvicorn api.service:app --reload
```

PostgreSQL must be running: on startup the API creates the `langgraph` schema and its checkpoint tables.

| Service | Address |
| :--- | :--- |
| FastAPI Swagger UI | [localhost:8000/docs](http://localhost:8000/docs) |
| Stock list | [localhost:8081/stocks](http://localhost:8081/stocks) |
| Single product | [localhost:8081/stocks/SKU-001](http://localhost:8081/stocks/SKU-001) |
| PostgreSQL | `localhost:5433` · database: `stockdb` |

## API

### Ask the assistant

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Is SKU-001 in stock?"}'
```

Example response; the exact wording may vary:

```json
{
  "response": "The Mechanical Keyboard is in stock. There are 25 units available.",
  "thread_id": "5f0c1a52-6f0e-4d5c-9d0e-2f1f4f0c9a11",
  "pending_approval": null
}
```

### Request a refund

The TRY 150 and TRY 200 demo orders are refunded within the same request. The TRY 250 order needs an operator:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Refund order 33333333-3333-4333-8333-333333333333, the monitor arrived broken."}'
```

```json
{
  "response": "İade talebiniz alındı ve operatör onayı bekliyor.",
  "thread_id": "9b2d7c1e-3a44-4f7b-8a55-0c6d1e2f3a4b",
  "pending_approval": {
    "refundRequestId": "a7aa5d8b-42ea-4a14-aeac-5d725e0ce918",
    "orderId": "33333333-3333-4333-8333-333333333333",
    "amountKurus": 25000,
    "currency": "TRY",
    "requiresApproval": true,
    "status": "PENDING_APPROVAL"
  }
}
```

The graph is now paused in PostgreSQL. The operator resumes it with the returned `thread_id`; the response carries the agent's final answer:

```bash
curl -X POST http://localhost:8000/chat/9b2d7c1e-3a44-4f7b-8a55-0c6d1e2f3a4b/approval \
  -H 'Content-Type: application/json' \
  -d '{"approved": true}'
```

On approval the refund is executed and the order becomes `REFUNDED`; on rejection the refund becomes `REJECTED` and the order stays `PAID`. Deciding the same thread twice returns `404`.

### Query the stock service directly

```bash
curl http://localhost:8081/stocks/SKU-001
```

```json
{
  "sku": "SKU-001",
  "name": "Mechanical Keyboard",
  "quantity": 25
}
```

| Method | Endpoint | Behavior |
| :--- | :--- | :--- |
| `POST` | `/chat` | Accepts a `message` and returns the agent's answer in `response`, with a `thread_id` and, when a refund waits for an operator, `pending_approval` |
| `POST` | `/chat/{thread_id}/approval` | Operator decision `{"approved": true}` or `false`; resumes the paused refund and returns the agent's answer. `404` when nothing is waiting |
| `GET` | `/stocks` | Returns all stock records, or `[]` when empty |
| `GET` | `/stocks/{sku}` | Returns one product, or `404` if not found |
| `POST` | `/refunds/prepare` | Prepares a full-order refund using the stored order amount; flags amounts above TRY 200 for approval |
| `POST` | `/refunds/{id}/approve` · `/reject` | Decides a refund that is `PENDING_APPROVAL`; `409` otherwise |
| `POST` | `/refunds/{id}/execute` | Executes a `READY` or `APPROVED` refund and marks the order `REFUNDED`; `409` otherwise |

The `get_stock` tool queries by SKU. Product-name search is not implemented yet.

## Container images

Both services have a Dockerfile; the processes run as a non-root user and `.env` is never copied into an image.

```bash
docker build -t customer-assistant-api .
docker build -t stock-service stock-service
```

Configure the containers with the environment variables listed under [Configuration](#configuration). Images built on Apple silicon are `arm64`; add `--platform linux/amd64` when the target host is x86.

## Project structure

```text
customer-assistant-agent/
├── api/
│   ├── service.py          # FastAPI /chat and operator approval endpoints
│   └── model.py            # Request, response, stock, and refund models
├── clients/
│   └── stock_service.py    # HTTP calls to the Java service
├── graph/
│   ├── agent.py            # Model, state, tool loop, and refund approval flow
│   └── checkpointer.py     # PostgreSQL connection pool and checkpoint tables
├── tools/
│   └── toolset.py          # get_stock, initiate_refund, and TOOLSET
├── stock-service/
│   ├── src/main/java/      # Spring Boot application, stock and refund endpoints
│   ├── src/main/resources/
│   │   ├── application.properties
│   │   └── schema.sql      # Stock, orders, and refund preparation records
│   ├── demo-refunds.sql    # Demo orders for the refund flow
│   ├── compose.yaml        # PostgreSQL
│   ├── Dockerfile
│   └── pom.xml
├── Dockerfile              # Python API image
├── .env.example            # Environment template without credentials
├── pyproject.toml
└── uv.lock
```

## Configuration

Python loads the project-root `.env` file through `load_dotenv()`:

| Variable | Purpose | Default / requirement |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | GPT-5 mini calls | Required |
| `STOCK_SERVICE_URL` | Java service address | `http://localhost:8081` |
| `CHECKPOINT_DB_URL` | PostgreSQL for paused graph threads | `postgresql://stock:stock@localhost:5433/stockdb` |
| `LANGSMITH_TRACING` | Send agent and tool traces | `false` in the example file |
| `LANGSMITH_API_KEY` | LangSmith access | Required when tracing is enabled |
| `LANGSMITH_PROJECT` | Project for collected traces | `customer-assistant-agent` |

To use LangSmith, set tracing to `true` and add your key. For the EU region, set `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`. Keys associated with multiple workspaces also require `LANGSMITH_WORKSPACE_ID`. When tracing is enabled, messages and tool results are sent to LangSmith. [LangGraph tracing setup](https://docs.langchain.com/langsmith/trace-with-langgraph)

The Java service accepts `DB_URL`, `DB_USER`, `DB_PASSWORD`, and `PORT` environment variables. Java does not automatically read the project-root `.env` file; provide these values in the Java process environment. See the [Stock Service README](stock-service/README.md) for details.

## Current scope and roadmap

- [x] Assistant endpoint through FastAPI
- [x] Asynchronous model → tool → model loop with LangGraph
- [x] SKU-based stock queries backed by PostgreSQL
- [x] Pydantic stock-response validation, with validation failures returned as tool results
- [x] Optional LangSmith tracing configuration
- [x] Backend refund rules with stored order amounts and a TRY 200 approval threshold; [details](stock-service/README.md#prepare-a-refund)
- [x] Refund tool: automatic execution up to TRY 200, operator approval (human-in-the-loop) above it, duplicate-refund protection
- [x] PostgreSQL checkpointer: refunds waiting for approval survive restarts
- [x] Container images for both services
- [ ] Stock tool error handling for HTTP errors and connection failures (the refund tool already has it)
- [ ] Product-name search
- [ ] User authentication, operator authorization, and refund ownership checks
- [ ] Separate least-privilege database accounts for the Java service and the checkpointer
- [ ] Operator view of refunds waiting for approval
- [ ] LLM timeouts and a concurrency limit with fast rejection under overload
- [ ] Versioned schema migrations instead of `schema.sql` on every start
- [ ] Kubernetes deployment (k3s)
- [ ] Decouple request and run lifetimes: RabbitMQ work queue, LangGraph workers, streamed responses

> **Development scope:** The APIs do not currently require authentication. In the local setup, the Java service connects with an administrative account that can create tables; GET endpoints do not make that database account read-only. Refunds work for demo orders and only update order and refund status; no payment provider is called, and the approval endpoint is as unauthenticated as the rest. Ownership checks are not implemented yet. Default database credentials are intended for local development.
