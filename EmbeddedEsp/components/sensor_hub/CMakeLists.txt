idf_component_register(SRCS "sensor_hub.c"
                    INCLUDE_DIRS "include"
                    REQUIRES "driver" "esp_driver_gpio" "health_data" "max30105" "ssd1306")
