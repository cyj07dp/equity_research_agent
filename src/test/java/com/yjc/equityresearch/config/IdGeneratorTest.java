package com.yjc.equityresearch.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class IdGeneratorTest {
    @Test
    void newIdGeneratesUuidV7WithRfc4122Variant() {
        IdGenerator idGenerator = new IdGenerator(
                Clock.fixed(Instant.parse("2026-06-10T00:00:00Z"), ZoneOffset.UTC),
                new SecureRandom(new byte[]{1, 2, 3, 4})
        );

        UUID id = idGenerator.newId();

        assertThat(id.version()).isEqualTo(7);
        assertThat(id.variant()).isEqualTo(2);
    }

    @Test
    void newIdStoresUnixMillisInMostSignificantPrefix() {
        Instant instant = Instant.parse("2026-06-10T00:00:00Z");
        IdGenerator idGenerator = new IdGenerator(
                Clock.fixed(instant, ZoneOffset.UTC),
                new SecureRandom(new byte[]{5, 6, 7, 8})
        );

        UUID id = idGenerator.newId();

        long timestampPrefix = id.getMostSignificantBits() >>> 16;
        assertThat(timestampPrefix).isEqualTo(instant.toEpochMilli());
    }
}
