package com.iomt.dashboard.common;

/**
 * Utility class for user ID extraction from request headers.
 * Centralizes the fallback logic used across all Controllers.
 */
public final class UserUtils {

    public static final String HEADER_USER_ID = "X-User-Id";
    public static final String DEFAULT_USER = "demo_user";

    private UserUtils() {
    }

    /**
     * Extract userId from header, with fallback to default demo user.
     *
     * @param userId the raw userId from @RequestHeader (may be null or blank)
     * @return the effective userId to use
     */
    public static String extractUserId(String userId) {
        return (userId != null && !userId.isBlank()) ? userId : DEFAULT_USER;
    }
}
