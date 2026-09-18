# Stock Service

Java 21 + Spring Boot + JDBC. PostgreSQL'deki tek `stock` tablosunu okur.

## Çalıştırma

Docker açıkken bu klasörde:

```bash
docker compose up -d
mvn spring-boot:run
```

Servis `8081`, PostgreSQL `5433` portunu kullanır. Tablo uygulama açılırken
oluşturulur; başlangıçta boştur. API kimlik doğrulaması gerektirmez.

Örnek stok eklemek için uygulama açıldıktan sonra başka bir terminalde:

```bash
docker compose exec postgres psql -U stock -d stockdb -c "INSERT INTO stock (sku, name, quantity) VALUES ('SKU-001', 'Klavye', 25) ON CONFLICT (sku) DO NOTHING;"
```

- `GET http://localhost:8081/stocks` — tüm stoklar (boşsa `[]`).
- `GET http://localhost:8081/stocks/SKU-001` — tek ürün (bulunamazsa `404`).

Tek ürün yanıtı:

```json
{"sku":"SKU-001","name":"Klavye","quantity":25}
```

Mevcut bir PostgreSQL için `DB_URL`, `DB_USER`, `DB_PASSWORD` ortam değişkenlerini
ayarla. Port `PORT` ile değiştirilebilir. Varsayılan veritabanı parolası yerel
geliştirme içindir; dış ortamda kendi parolanı kullan.
