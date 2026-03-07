package com.lifechiro.auth;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class WerkzeugPasswordEncoderTest {
    private final WerkzeugPasswordEncoder encoder = new WerkzeugPasswordEncoder();

    @Test
    void matchesExistingWerkzeugHash() {
        String existingHash = "pbkdf2:sha256:1000000$n2qc8hn7kM154MQR$aac7b6153bfe8c890629b0e3b34fe5cbd2d911a0a0aa6c2cf7042271a766a6f7";
        assertTrue(encoder.matches("staffpass123", existingHash));
        assertFalse(encoder.matches("wrongpass", existingHash));
    }

    @Test
    void generatedHashesRoundTrip() {
        String encoded = encoder.encode("patientpass123");
        assertTrue(encoder.matches("patientpass123", encoded));
        assertFalse(encoder.matches("different", encoded));
    }
}
