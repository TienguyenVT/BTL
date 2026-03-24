idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES health_data wifi_manager mqtt_manager sensor_hub gsr_sensor ssd1306 app_ds18b20 nvs_flash freertos log driver lwip)
