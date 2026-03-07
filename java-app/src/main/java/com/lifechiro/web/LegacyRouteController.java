package com.lifechiro.web;

import java.util.HashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/legacy")
public class LegacyRouteController {

    private ResponseEntity<Map<String, Object>> notImplemented(String route, String method) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("status", "not_implemented");
        payload.put("route", route);
        payload.put("method", method);
        payload.put("message", "Route scaffolded during Flask-to-Java conversion. Business logic not migrated yet.");
        return ResponseEntity.ok(payload);
    }

    @GetMapping("/")
    public ResponseEntity<Map<String, Object>> root() {
        return notImplemented("/legacy/", "GET");
    }

    @RequestMapping(value = "/signup")
    public ResponseEntity<Map<String, Object>> signup() {
        return notImplemented("/legacy/signup", "GET/POST");
    }

    @RequestMapping(value = "/forgot-password")
    public ResponseEntity<Map<String, Object>> forgotPassword() {
        return notImplemented("/legacy/forgot-password", "GET/POST");
    }

    @RequestMapping(value = "/reset-password/{token}")
    public ResponseEntity<Map<String, Object>> resetPassword(@PathVariable String token) {
        return notImplemented("/legacy/reset-password/{token}", "GET/POST");
    }

    @GetMapping("/staff/dashboard")
    public ResponseEntity<Map<String, Object>> staffDashboard() {
        return notImplemented("/legacy/staff/dashboard", "GET");
    }

    @GetMapping("/appointments")
    public ResponseEntity<Map<String, Object>> appointments() {
        return notImplemented("/legacy/appointments", "GET");
    }

    @PostMapping("/appointments/self-book")
    public ResponseEntity<Map<String, Object>> appointmentsSelfBook() {
        return notImplemented("/legacy/appointments/self-book", "POST");
    }
}
