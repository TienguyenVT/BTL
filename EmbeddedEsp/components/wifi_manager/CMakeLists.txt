idf_component_register(SRCS "wifi_manager.c"
                       INCLUDE_DIRS "include"
                       REQUIRES esp_wifi esp_netif esp_event wifi_provisioning health_data mqtt_manager)
