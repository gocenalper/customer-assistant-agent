-- Local demonstration data only. Run explicitly; existing records are preserved.
INSERT INTO stock (sku, name, quantity) VALUES
    ('SKU-001', 'Mechanical Keyboard', 25),
    ('SKU-002', 'Wireless Mouse', 40),
    ('SKU-003', '27-inch Monitor', 12)
ON CONFLICT (sku) DO NOTHING;

INSERT INTO sales_order (id, sku, quantity, total_amount_kurus, status) VALUES
    ('11111111-1111-4111-8111-111111111111', 'SKU-001', 1, 15000, 'PAID'),
    ('22222222-2222-4222-8222-222222222222', 'SKU-002', 1, 20000, 'PAID'),
    ('33333333-3333-4333-8333-333333333333', 'SKU-003', 1, 25000, 'PAID')
ON CONFLICT (id) DO NOTHING;
