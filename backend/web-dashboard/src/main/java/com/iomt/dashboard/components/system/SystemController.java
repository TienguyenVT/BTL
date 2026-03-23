package com.iomt.dashboard.components.system;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class SystemController {

    @GetMapping
    public String healthCheck() {
        return "Backend dang chay tai /api";
    }
}
