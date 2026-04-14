idf_component_register(
    SRCS "dht11_sensor.c"
    INCLUDE_DIRS "include"
    PRIV_INCLUDE_DIRS "../health_data/include" "../app_ds18b20/include"
    REQUIRES driver esp_driver_gpio esp_common freertos esp_timer health_data
)