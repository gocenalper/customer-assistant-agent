package com.example.stock;

import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class RefundController {
    private static final long AUTOMATIC_REFUND_LIMIT_KURUS = 20_000;
    private static final String REFUND_COLUMNS =
            "id AS refund_request_id, order_id, amount_kurus, currency, requires_approval, status";
    private final JdbcClient jdbc;

    public RefundController(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @PostMapping("/refunds/prepare")
    @Transactional
    public RefundPreparation prepare(@RequestBody PrepareRefundRequest request) {
        if (request.orderId() == null || request.reason() == null
                || request.reason().isBlank() || request.reason().length() > 1000) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "orderId and a non-blank reason of up to 1000 characters are required.");
        }

        // Serialize preparation requests for the same order.
        var order = jdbc.sql("""
                SELECT id, total_amount_kurus, currency, status
                FROM sales_order WHERE id = :id FOR UPDATE
                """)
                .param("id", request.orderId())
                .query(Order.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Order not found."));

        if (!"PAID".equals(order.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Only paid orders that have not been refunded can be prepared for refund.");
        }

        boolean requiresApproval = order.totalAmountKurus() > AUTOMATIC_REFUND_LIMIT_KURUS;
        jdbc.sql("""
                INSERT INTO refund_request
                    (id, order_id, reason, amount_kurus, currency, requires_approval, status)
                VALUES (:id, :orderId, :reason, :amount, :currency, :approval, :status)
                ON CONFLICT (order_id) DO NOTHING
                """)
                .param("id", UUID.randomUUID())
                .param("orderId", order.id())
                .param("reason", request.reason().strip())
                .param("amount", order.totalAmountKurus())
                .param("currency", order.currency())
                .param("approval", requiresApproval)
                .param("status", requiresApproval ? "PENDING_APPROVAL" : "READY")
                .update();

        return jdbc.sql("""
                SELECT id AS refund_request_id, order_id, amount_kurus, currency,
                       requires_approval, status
                FROM refund_request WHERE order_id = :orderId
                """)
                .param("orderId", order.id())
                .query(RefundPreparation.class).single();
    }

    @PostMapping("/refunds/{id}/approve")
    @Transactional
    public RefundPreparation approve(@PathVariable UUID id) {
        return decide(id, "APPROVED");
    }

    @PostMapping("/refunds/{id}/reject")
    @Transactional
    public RefundPreparation reject(@PathVariable UUID id) {
        return decide(id, "REJECTED");
    }

    @PostMapping("/refunds/{id}/execute")
    @Transactional
    public RefundPreparation execute(@PathVariable UUID id) {
        var refund = lock(id);
        // Repeated execution must not refund twice.
        if ("REFUNDED".equals(refund.status())) {
            return refund;
        }
        if (!"READY".equals(refund.status()) && !"APPROVED".equals(refund.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Only ready or approved refunds can be executed.");
        }

        int updated = jdbc.sql("UPDATE sales_order SET status = 'REFUNDED' WHERE id = :id AND status = 'PAID'")
                .param("id", refund.orderId())
                .update();
        if (updated == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Order is no longer eligible for refund.");
        }
        return setStatus(id, "REFUNDED");
    }

    private RefundPreparation decide(UUID id, String decision) {
        var refund = lock(id);
        if (decision.equals(refund.status())) {
            return refund;
        }
        if (!"PENDING_APPROVAL".equals(refund.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Only refunds pending approval can be approved or rejected.");
        }
        return setStatus(id, decision);
    }

    private RefundPreparation lock(UUID id) {
        return jdbc.sql("SELECT " + REFUND_COLUMNS + " FROM refund_request WHERE id = :id FOR UPDATE")
                .param("id", id)
                .query(RefundPreparation.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Refund request not found."));
    }

    private RefundPreparation setStatus(UUID id, String status) {
        return jdbc.sql("UPDATE refund_request SET status = :status WHERE id = :id RETURNING " + REFUND_COLUMNS)
                .param("status", status)
                .param("id", id)
                .query(RefundPreparation.class).single();
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ProblemDetail handleRefundError(ResponseStatusException exception) {
        return ProblemDetail.forStatusAndDetail(exception.getStatusCode(), exception.getReason());
    }

    public record PrepareRefundRequest(UUID orderId, String reason) {}

    public record RefundPreparation(UUID refundRequestId, UUID orderId, long amountKurus,
                                    String currency, boolean requiresApproval, String status) {}

    public record Order(UUID id, long totalAmountKurus, String currency, String status) {}
}
