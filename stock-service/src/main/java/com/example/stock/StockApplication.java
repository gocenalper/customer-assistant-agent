package com.example.stock;

import java.util.List;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
@RestController
public class StockApplication {
    private final JdbcClient jdbc;

    public StockApplication(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public static void main(String[] args) {
        SpringApplication.run(StockApplication.class, args);
    }

    @GetMapping("/stocks")
    public List<Stock> stocks() {
        return jdbc.sql("SELECT sku, name, quantity FROM stock ORDER BY sku")
                .query(Stock.class).list();
    }

    @GetMapping("/stocks/{sku}")
    public Stock stock(@PathVariable String sku) {
        return jdbc.sql("SELECT sku, name, quantity FROM stock WHERE sku = :sku")
                .param("sku", sku)
                .query(Stock.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Stock not found"));
    }

    public record Stock(String sku, String name, int quantity) {}
}
