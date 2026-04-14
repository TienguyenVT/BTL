idf_component_register(SRCS "thermal_processor.c" "ds18b20.c"
                    INCLUDE_DIRS "include"
                    REQUIRES "driver" "esp_driver_gpio" "health_data" "espressif__ds18b20" "espressif__onewire_bus")
