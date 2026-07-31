package com.yjc.equityresearch;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@EnableAsync
@SpringBootApplication
public class EquityResearchApplication {
    public static void main(String[] args) {
        SpringApplication.run(EquityResearchApplication.class, args);
    }
}
