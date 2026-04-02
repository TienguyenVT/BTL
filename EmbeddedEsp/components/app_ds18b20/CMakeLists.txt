idf_component_register(SRCS "thermal_processor.c" "ds18b20.c"
                    INCLUDE_DIRS "include"
                    REQUIRES "health_data" "espressif__ds18b20")
