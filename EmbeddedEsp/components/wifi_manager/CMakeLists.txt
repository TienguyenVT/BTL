idf_component_register(SRCS "wifi_manager.c"
                    INCLUDE_DIRS "include"
                    REQUIRES health_data mqtt_manager wifi_provisioning esp_wifi esp_event esp_netif)
