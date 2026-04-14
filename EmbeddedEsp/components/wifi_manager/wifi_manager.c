#include "wifi_manager.h"
#include "health_data.h"
#include "mqtt_manager.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "wifi_provisioning/manager.h"
#include "wifi_provisioning/scheme_softap.h"
#include <string.h>

static const char *TAG = "WIFI_AP";

static bool s_is_provisioned = false;

static char s_mac_str[18] = {0};

static void format_mac(uint8_t *mac, char *out) {
    snprintf(out, 18, "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

static void wifi_prov_event_handler(void *arg, esp_event_base_t event_base,
                                    int32_t event_id, void *event_data) {
    if (event_base == WIFI_PROV_EVENT) {
        switch (event_id) {
            case WIFI_PROV_START:
                ESP_LOGI(TAG, "Bat dau che do Provisioning vao SoftAP IoMT-PTIT de cau hinh");
                health_data_get()->mode = MODE_CONFIG;
                break;
            case WIFI_PROV_CRED_RECV:
                ESP_LOGI(TAG, "Da nhan duoc mat khau WiFi tu App!");
                break;
            case WIFI_PROV_CRED_FAIL:
                ESP_LOGI(TAG, "Ket noi WiFi that bai! Khoi dong lai Provisioning...");
                wifi_prov_mgr_reset_provisioning();
                break;
            case WIFI_PROV_CRED_SUCCESS:
                ESP_LOGI(TAG, "Cau hinh WiFi thanh cong!");
                break;
            case WIFI_PROV_END:
                ESP_LOGI(TAG, "Ket thuc Provisioning hien tai.");
                wifi_prov_mgr_deinit();
                break;
            default:
                break;
        }
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Da ket noi Router Internet thanh cong - IP: " IPSTR, IP2STR(&event->ip_info.ip));

        uint8_t mac[6];
        ESP_ERROR_CHECK(esp_wifi_get_mac(WIFI_MODE_STA, mac));
        format_mac(mac, s_mac_str);
        memcpy(health_data_get()->mac_address, s_mac_str, sizeof(s_mac_str));
        ESP_LOGI(TAG, "MAC address: %s", s_mac_str);

        // MỞ KHÓA HOẠT ĐỘNG KHI ĐÃ LÊN MẠNG
        xEventGroupSetBits(health_data_get_event_group(), WIFI_CONNECTED_BIT);
        ESP_LOGW(TAG, "=> Da co ket noi Internet. MO CUA cho cac cam bien hoat dong!");

        // Tắt WiFi Power Save để tránh interrupt delay gây WDT
        esp_wifi_set_ps(WIFI_PS_NONE);

        // Bắt đầu kết nối MQTT
        mqtt_manager_start();

        // Chuyển sang chế độ IDLE (chờ user)
        health_data_get()->mode = MODE_IDLE;
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (health_data_get()->mode == MODE_CONFIG) {
            if (s_is_provisioned) {
                static int s_retry_num = 0;
                s_retry_num++;
                if (s_retry_num >= 5) {
                    ESP_LOGW(TAG, "Loi ket noi WiFi da luu (%d lan). Xoa cau hinh va mo lai SoftAP...", s_retry_num);
                    esp_wifi_restore();
                    vTaskDelay(pdMS_TO_TICKS(1000));
                    esp_restart();
                } else {
                    ESP_LOGI(TAG, "Mat ket noi mang (%d/5). Dang thu ket noi lai...", s_retry_num);
                    esp_wifi_connect();
                }
            } else {
                // Đang trong lúc SoftAP setup, không tự connect lại để Provisioning Manager xử lý.
                ESP_LOGI(TAG, "Dang cho user cau hinh WiFi (SoftAP)...");
                xEventGroupClearBits(health_data_get_event_group(), WIFI_CONNECTED_BIT);
            }
        } else {
            ESP_LOGI(TAG, "Mat ket noi mang. Dang thu ket noi lai...");

            // ĐÓNG KHÓA
            xEventGroupClearBits(health_data_get_event_group(), WIFI_CONNECTED_BIT);
            ESP_LOGW(TAG, "=> Mat ket noi Internet. DUNG tiep nhan du lieu tu cam bien!");
            esp_wifi_connect();
        }
    }
}

void wifi_manager_init(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // Cần tạo cả 2 interface cho Provisioning qua SoftAP
    esp_netif_create_default_wifi_sta();
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // Đăng ký Event
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_PROV_EVENT, ESP_EVENT_ANY_ID, &wifi_prov_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_prov_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, ESP_EVENT_ANY_ID, &wifi_prov_event_handler, NULL));

    // Cấu hình Provisioning Manager (Sử dụng scheme SoftAP)
    wifi_prov_mgr_config_t config = {
        .scheme = wifi_prov_scheme_softap,
        .scheme_event_handler = WIFI_PROV_EVENT_HANDLER_NONE
    };
    ESP_ERROR_CHECK(wifi_prov_mgr_init(config));

    bool provisioned = false;
    ESP_ERROR_CHECK(wifi_prov_mgr_is_provisioned(&provisioned));
    s_is_provisioned = provisioned;

    if (!provisioned) {
        ESP_LOGI(TAG, "Thiet bi chua co cau hinh mang. Dang phat SoftAP 'IoMT-PTIT' de cho setup...");
        ESP_ERROR_CHECK(wifi_prov_mgr_start_provisioning(WIFI_PROV_SECURITY_0, NULL, "IoMT-PTIT", NULL));
    } else {
        ESP_LOGI(TAG, "Da luu san thong tin WiFi trong NVS. Dang ket noi mang...");
        wifi_prov_mgr_deinit();
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        ESP_ERROR_CHECK(esp_wifi_start());  
    }
}
