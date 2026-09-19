CREATE TABLE IF NOT EXISTS stock (
    sku VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0)
);

CREATE TABLE IF NOT EXISTS sales_order (
    id UUID PRIMARY KEY,
    sku VARCHAR(100) NOT NULL REFERENCES stock(sku),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    total_amount_kurus BIGINT NOT NULL CHECK (total_amount_kurus > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'TRY' CHECK (currency = 'TRY'),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PAID', 'REFUNDED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS refund_request (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL UNIQUE REFERENCES sales_order(id),
    reason VARCHAR(1000) NOT NULL CHECK (length(trim(reason)) > 0),
    amount_kurus BIGINT NOT NULL CHECK (amount_kurus > 0),
    currency VARCHAR(3) NOT NULL CHECK (currency = 'TRY'),
    requires_approval BOOLEAN NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Re-created on every start so existing databases pick up new statuses.
ALTER TABLE refund_request DROP CONSTRAINT IF EXISTS refund_request_status_check;
ALTER TABLE refund_request ADD CONSTRAINT refund_request_status_check
    CHECK (status IN ('READY', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'REFUNDED'));
