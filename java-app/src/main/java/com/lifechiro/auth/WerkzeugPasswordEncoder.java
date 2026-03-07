package com.lifechiro.auth;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.HexFormat;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import org.springframework.security.crypto.password.PasswordEncoder;

public class WerkzeugPasswordEncoder implements PasswordEncoder {
    private static final String PREFIX = "pbkdf2:sha256:";
    private static final int DEFAULT_ITERATIONS = 1_000_000;
    private static final int KEY_LENGTH_BITS = 256;
    private static final String SALT_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    private final SecureRandom secureRandom = new SecureRandom();

    @Override
    public String encode(CharSequence rawPassword) {
        String salt = randomSalt(16);
        byte[] hash = pbkdf2(rawPassword, salt, DEFAULT_ITERATIONS);
        return PREFIX + DEFAULT_ITERATIONS + "$" + salt + "$" + HexFormat.of().formatHex(hash);
    }

    @Override
    public boolean matches(CharSequence rawPassword, String encodedPassword) {
        if (encodedPassword == null || encodedPassword.isBlank() || !encodedPassword.startsWith(PREFIX)) {
            return false;
        }
        String[] sections = encodedPassword.split("\\$", 3);
        if (sections.length != 3) {
            return false;
        }
        String header = sections[0];
        String salt = sections[1];
        String expectedHex = sections[2];
        int iterations;
        try {
            iterations = Integer.parseInt(header.substring(PREFIX.length()));
        } catch (NumberFormatException ex) {
            return false;
        }
        byte[] expected = HexFormat.of().parseHex(expectedHex);
        byte[] actual = pbkdf2(rawPassword, salt, iterations);
        return MessageDigest.isEqual(expected, actual);
    }

    private byte[] pbkdf2(CharSequence rawPassword, String salt, int iterations) {
        try {
            PBEKeySpec spec = new PBEKeySpec(
                rawPassword.toString().toCharArray(),
                salt.getBytes(StandardCharsets.UTF_8),
                iterations,
                KEY_LENGTH_BITS
            );
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to create PBKDF2 hash", ex);
        }
    }

    private String randomSalt(int length) {
        StringBuilder builder = new StringBuilder(length);
        for (int index = 0; index < length; index += 1) {
            int selected = secureRandom.nextInt(SALT_ALPHABET.length());
            builder.append(SALT_ALPHABET.charAt(selected));
        }
        return builder.toString();
    }
}
