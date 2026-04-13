idf_component_register(
    SRCS
    "main.c"
    INCLUDE_DIRS "."
    REQUIRES "nvs_flash" "water_data" "water_flow_sensor" "pzem004t" "wifi_manager" "mqtt_manager" "relay_control"
)
