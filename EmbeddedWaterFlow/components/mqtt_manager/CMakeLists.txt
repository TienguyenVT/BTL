idf_component_register(
    SRCS
    "mqtt_manager.c"
    INCLUDE_DIRS "include"
    REQUIRES "esp_netif" "mqtt" "esp_driver_gpio" "water_data" "relay_control"
)
