idf_component_register(SRCS "wifi_manager.c"
                    INCLUDE_DIRS "include"
                    REQUIRES "esp_wifi" "esp_netif" "esp_event" "esp_timer" "nvs_flash" "water_data" "esp_http_server" "mqtt_manager" "relay_control")