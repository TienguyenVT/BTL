idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES max30105 spo2_algorithm driver esp_driver_i2c freertos log)
