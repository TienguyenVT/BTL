idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES max30105 spo2_algorithm driver esp_driver_i2c freertos log esp_adc ds18b20 nvs_flash esp_wifi esp_netif esp_event wifi_provisioning mqtt esp-tls ssd1306)
