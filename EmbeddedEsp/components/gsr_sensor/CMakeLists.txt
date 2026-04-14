idf_component_register(SRCS "gsr_sensor.c"
                    INCLUDE_DIRS "include"
                    REQUIRES "health_data" "driver" "esp_driver_gpio" "esp_adc" "nvs_flash" "freertos")
