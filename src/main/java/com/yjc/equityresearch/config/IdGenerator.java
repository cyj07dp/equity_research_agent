package com.yjc.equityresearch.config;

import java.security.SecureRandom;
import java.time.Clock;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class IdGenerator {
    private final Clock clock;
    private final SecureRandom random;

    public IdGenerator() {
        this(Clock.systemUTC(), new SecureRandom());
    }

    IdGenerator(Clock clock, SecureRandom random) {
        this.clock = clock;
        this.random = random;
    }

    public UUID newId() {
        long timestampMillis = clock.millis() & 0x0000FFFFFFFFFFFFL;
        long randomA = random.nextLong() & 0x0FFFL;
        long mostSignificantBits = (timestampMillis << 16) | 0x7000L | randomA;

        long randomB = random.nextLong() & 0x3FFFFFFFFFFFFFFFL;
        long leastSignificantBits = 0x8000000000000000L | randomB;

        return new UUID(mostSignificantBits, leastSignificantBits);
    }
}
