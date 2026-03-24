idf_component_register(SRCS "gsr_sensor.c"
                       INCLUDE_DIRS "include"
                       REQUIRES driver esp_adc health_data freertos)
