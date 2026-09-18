# Stock Service

Java 21 + Spring Boot + JDBC. Reads inventory from a single PostgreSQL `stock` table.

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
