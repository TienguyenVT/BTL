idf_component_register(SRCS "sensor_hub.c"
                       INCLUDE_DIRS "include"
                       REQUIRES driver esp_driver_i2c max30105 health_data ssd1306 freertos)
