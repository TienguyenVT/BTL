package com.iomt.dashboard.components.health;

import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Scheduler: Tu dong goi SessionService.rebuildSessions() moi 1 giay.
 *
 * Luc trinh:
 * 1. Doc final_result
 * 2. Phat hien phiên moi / cap nhat phiên active
 * 3. De-activate phiên cu khi gap > 15 phut
 * 4. Luu vao bang sessions
 *
 * Chay ngay khi ung dung khoi dong (initialDelay = 2000ms),
 * sau do lap lai moi 1000ms.
 */
@Component
@RequiredArgsConstructor
public class SessionScheduler {

    private static final Logger log = LoggerFactory.getLogger(SessionScheduler.class);

    private final SessionService sessionService;

    /**
     * Chay ngay 2 giay sau khi khoi dong, sau do lap 1 giay/lan.
     */
    @Scheduled(initialDelay = 2000, fixedRate = 1000)
    public void runSessionBuilder() {
        log.info("[SessionScheduler] Running scheduled session rebuild...");
        try {
            sessionService.rebuildSessions();
        } catch (Exception e) {
            log.error("[SessionScheduler] Error during session rebuild", e);
        }
    }
}
