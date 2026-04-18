package com.iomt.dashboard.components.health;

import com.iomt.dashboard.components.alert.AlertService;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class SessionScheduler {

    private static final Logger log = LoggerFactory.getLogger(SessionScheduler.class);

    private final SessionService sessionService;
    private final AlertService alertService;

    @Scheduled(initialDelay = 2000, fixedRate = 60000)
    public void runSessionBuilder() {
        log.info("[SessionScheduler] Running scheduled session rebuild...");
        try {
            sessionService.rebuildSessions();
            alertService.checkAndCreateAlerts();
        } catch (Exception e) {
            log.error("[SessionScheduler] Error during session rebuild", e);
        }
    }
}
