# Stock Service

Java 21 + Spring Boot + JDBC. Reads inventory from PostgreSQL and prepares refund requests for demo orders.

## Run locally

With Docker running, execute these commands from this directory:

```bash
docker compose up -d
mvn spring-boot:run
```

The service runs on port `8081`, and PostgreSQL is exposed on port `5433`.
The application creates the table on startup; it is initially empty.
The API does not require authentication.

Once the application has started, add a sample product from another terminal
in this directory:

```bash
docker compose exec postgres psql -U stock -d stockdb -c "INSERT INTO stock (sku, name, quantity) VALUES ('SKU-001', 'Mechanical Keyboard', 25) ON CONFLICT (sku) DO NOTHING;"
```

- `GET http://localhost:8081/stocks` — all stock records, or `[]` when empty.
- `GET http://localhost:8081/stocks/SKU-001` — one product, or `404` if not found.

Example single-product response:

```json
{"sku":"SKU-001","name":"Mechanical Keyboard","quantity":25}
```

For an existing PostgreSQL instance, set the `DB_URL`, `DB_USER`, and `DB_PASSWORD`
environment variables. Set `PORT` to change the service port. The default database
password is intended for local development; use your own credentials elsewhere.

## Prepare a refund

`POST /refunds/prepare` prepares a full-order refund without moving money or changing stock.
The amount comes from `sales_order`, never from the request body. Amounts are integer
kurus: `20000` means TRY 200.00. Amounts up to and including 20000 return `READY`;
larger amounts return `PENDING_APPROVAL`. Neither status means the order was refunded.

After starting the updated application, load the local demonstration orders:

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U stock -d stockdb < demo-refunds.sql
```

| Order ID | Amount | Requires approval |
| --- | --- | --- |
| `11111111-1111-4111-8111-111111111111` | TRY 150.00 | No |
| `22222222-2222-4222-8222-222222222222` | TRY 200.00 | No |
| `33333333-3333-4333-8333-333333333333` | TRY 250.00 | Yes |

```bash
curl -X POST http://localhost:8081/refunds/prepare \
  -H 'Content-Type: application/json' \
  -d '{"orderId":"33333333-3333-4333-8333-333333333333","reason":"Customer requested a return"}'
```

Example response (the refund ID is generated when first prepared):

```json
{
  "refundRequestId": "a7aa5d8b-42ea-4a14-aeac-5d725e0ce918",
  "orderId": "33333333-3333-4333-8333-333333333333",
  "amountKurus": 25000,
  "currency": "TRY",
  "requiresApproval": true,
  "status": "PENDING_APPROVAL"
}
```

Repeated preparation for the same paid order returns the existing request, preserving
its original reason and amount. Missing orders return `404`; unpaid, cancelled, or
already refunded orders return `409`; invalid input returns `400`.

## Approve, reject, and execute a refund

| Endpoint | Allowed from | Result |
| --- | --- | --- |
| `POST /refunds/{id}/approve` | `PENDING_APPROVAL` | `APPROVED` |
| `POST /refunds/{id}/reject` | `PENDING_APPROVAL` | `REJECTED` |
| `POST /refunds/{id}/execute` | `READY`, `APPROVED` | `REFUNDED`; the order becomes `REFUNDED` |

Any other starting status returns `409`, so a refund above TRY 200 cannot be executed
without approval. Repeating a call that already took effect returns the current
request without changing anything; an order is refunded at most once. Unknown IDs
return `404`. Execution checks again that the order is still `PAID`.

```bash
curl -X POST http://localhost:8081/refunds/<refundRequestId>/execute
```

The Python agent calls these endpoints: it executes `READY` refunds right away and
asks an operator before approving larger ones.

This is a local demo: execution only updates statuses; no payment provider is called
and stock is unchanged. User authentication, order ownership, and refund-window
policy are not implemented.
