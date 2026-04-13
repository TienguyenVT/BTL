#include "wifi_manager.h"
#include "water_data.h"
#include "mqtt_manager.h"
#include "relay_control.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_http_server.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_netif_sntp.h"
#include "esp_sntp.h"
#include <string.h>

static const char *TAG = "WIFI_AP";

static char s_mac_str[18] = {0};
static bool s_wifi_connected = false;

static void format_mac(uint8_t *mac, char *out) {
    snprintf(out, 18, "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

static esp_err_t wifi_config_save(const char *ssid, const char *password) {
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("wifi", NVS_READWRITE, &nvs);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(err));
        return err;
    }
    err = nvs_set_str(nvs, "ssid", ssid);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to save SSID");
        nvs_close(nvs);
        return err;
    }
    err = nvs_set_str(nvs, "password", password);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to save password");
        nvs_close(nvs);
        return err;
    }
    err = nvs_commit(nvs);
    nvs_close(nvs);
    return err;
}

static esp_err_t wifi_config_load(char *ssid, size_t *ssid_len, char *password, size_t *pass_len) {
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("wifi", NVS_READONLY, &nvs);
    if (err != ESP_OK) return err;
    err = nvs_get_str(nvs, "ssid", ssid, ssid_len);
    if (err != ESP_OK) { nvs_close(nvs); return err; }
    err = nvs_get_str(nvs, "password", password, pass_len);
    nvs_close(nvs);
    return err;
}

static bool wifi_config_exists(void) {
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("wifi", NVS_READONLY, &nvs);
    if (err != ESP_OK) return false;
    size_t len = 0;
    err = nvs_get_str(nvs, "ssid", NULL, &len);
    nvs_close(nvs);
    return err == ESP_OK && len > 0;
}

bool wifi_manager_is_configured(void) {
    return wifi_config_exists();
}

void wifi_manager_clear_config(void) {
    nvs_handle_t nvs;
    if (nvs_open("wifi", NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_erase_key(nvs, "ssid");
        nvs_erase_key(nvs, "password");
        nvs_commit(nvs);
        nvs_close(nvs);
    }
}

// ==================== HTTP SERVER HANDLERS ====================

static esp_err_t root_get_handler(httpd_req_t *req) {
    const char *html = 
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<title>WaterFlow - WiFi Setup</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:0;padding:20px;"
        "background:#1a1a2e;color:#eee;}"
        ".container{max-width:400px;margin:0 auto;background:#16213e;"
        "padding:30px;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,0.3);}"
        "h1{text-align:center;color:#00d4ff;margin-bottom:30px;}"
        ".info{background:#0f3460;padding:15px;border-radius:8px;margin-bottom:20px;text-align:center;}"
        ".info strong{color:#e94560;}"
        "label{display:block;margin-bottom:5px;color:#aaa;}"
        "input{width:100%;padding:12px;margin-bottom:15px;border:none;border-radius:5px;"
        "background:#0f3460;color:#fff;box-sizing:border-box;font-size:16px;}"
        "button{width:100%;padding:15px;background:#00d4ff;color:#1a1a2e;"
        "border:none;border-radius:5px;font-size:18px;font-weight:bold;"
        "cursor:pointer;transition:background 0.3s;}"
        "button:hover{background:#00a8cc;}"
        ".status{margin-top:15px;text-align:center;font-size:14px;}"
        ".ssid-info{margin-top:20px;padding:15px;background:#0f3460;"
        "border-radius:5px;font-size:14px;}"
        "</style></head><body>"
        "<div class='container'>"
        "<h1>WaterFlow Setup</h1>"
        "<div class='info'>Ket noi WiFi <strong>WaterFlow-Setup</strong><br>de cau hinh</div>"
        "<form method='POST' action='/connect'>"
        "<label>WiFi SSID:</label>"
        "<input type='text' name='ssid' placeholder='Ten WiFi' required>"
        "<label>Mat khau:</label>"
        "<input type='password' name='password' placeholder='Mat khau WiFi'>"
        "<button type='submit'>Ket Noi</button>"
        "</form>"
        "<div class='ssid-info'>"
        "<strong>Luu y:</strong> Sau khi nhap thong tin, bam Ket Noi va cho 10-15 giay<br>"
        "neu khong thanh cong, thu lai voi mat khau dung"
        "</div>"
        "</div></body></html>";
    httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

static esp_err_t connect_post_handler(httpd_req_t *req) {
    char content[512] = {0};
    int ret = httpd_req_recv(req, content, sizeof(content) - 1);
    if (ret <= 0) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    content[ret] = '\0';

    char ssid[64] = {0}, password[64] = {0};
    char *ssid_start, *ssid_end, *pass_start, *pass_end;

    ssid_start = strstr(content, "ssid=");
    if (ssid_start) {
        ssid_start += 5;
        ssid_end = strchr(ssid_start, '&');
        if (ssid_end) {
            int len = ssid_end - ssid_start;
            if (len > 63) len = 63;
            strncpy(ssid, ssid_start, len);
        } else {
            strncpy(ssid, ssid_start, 63);
        }
    }

    pass_start = strstr(content, "password=");
    if (pass_start) {
        pass_start += 9;
        pass_end = strchr(pass_start, '&');
        if (pass_end) {
            int len = pass_end - pass_start;
            if (len > 63) len = 63;
            strncpy(password, pass_start, len);
        } else {
            strncpy(password, pass_start, 63);
        }
    }

    if (strlen(ssid) == 0) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Saving WiFi config: SSID=%s", ssid);
    if (wifi_config_save(ssid, password) == ESP_OK) {
        const char *ok_html =
            "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            "<title>WiFi Saved</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;margin:0;padding:20px;"
            "background:#1a1a2e;color:#eee;text-align:center;}"
            ".box{max-width:400px;margin:50px auto;background:#16213e;"
            "padding:40px;border-radius:10px;}"
            "h1{color:#00d4ff;}"
            ".blink{animation:blink 1s infinite;}"
            "@keyframes blink{50%{opacity:0;}}"
            "p{color:#aaa;}"
            "</style></head><body>"
            "<div class='box'>"
            "<h1>Da Luu!</h1>"
            "<p class='blink'>Dang ket noi toi WiFi...</p>"
            "<p>Neu khong tu dong, nhan nut RESET tren ESP32</p>"
            "</div></body></html>";
        httpd_resp_send(req, ok_html, HTTPD_RESP_USE_STRLEN);
        
        vTaskDelay(pdMS_TO_TICKS(500));
        esp_restart();
    } else {
        httpd_resp_send_500(req);
    }
    return ESP_OK;
}

static esp_err_t http_404_error_handler(httpd_req_t *req, httpd_err_code_t err) {
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "/");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

static httpd_handle_t start_http_server(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = HTTP_PORT;
    config.stack_size = 4096;

    esp_log_level_set("httpd_uri", ESP_LOG_ERROR);
    esp_log_level_set("httpd_txrx", ESP_LOG_ERROR);

    httpd_handle_t server = NULL;
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_register_err_handler(server, HTTPD_404_NOT_FOUND, http_404_error_handler);
        
        httpd_uri_t root = {.uri = "/", .method = HTTP_GET, .handler = root_get_handler};
        httpd_uri_t connect = {.uri = "/connect", .method = HTTP_POST, .handler = connect_post_handler};
        
        httpd_register_uri_handler(server, &root);
        httpd_register_uri_handler(server, &connect);
        ESP_LOGI(TAG, "HTTP server started on port %d", HTTP_PORT);
    }
    return server;
}

static void wifi_ap_event_handler(void *arg, esp_event_base_t event_base,
                                   int32_t event_id, void *event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t *event = (wifi_event_ap_staconnected_t *)event_data;
        ESP_LOGI(TAG, "Thiet bi ket noi AP: " MACSTR, MAC2STR(event->mac));
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STADISCONNECTED) {
        ESP_LOGI(TAG, "Thiet bi ngat ket noi AP");
    }
}

static void wifi_sta_event_handler(void *arg, esp_event_base_t event_base,
                                   int32_t event_id, void *event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Da ket noi WiFi - IP: " IPSTR, IP2STR(&event->ip_info.ip));

        uint8_t mac[6];
        ESP_ERROR_CHECK(esp_wifi_get_mac(WIFI_MODE_STA, mac));
        format_mac(mac, s_mac_str);
        memcpy(water_data_get()->mac_address, s_mac_str, sizeof(s_mac_str));
        ESP_LOGI(TAG, "MAC: %s", s_mac_str);

        s_wifi_connected = true;
        xEventGroupSetBits(water_data_get_event_group(), WIFI_CONNECTED_BIT);
        ESP_LOGI(TAG, "=> Da co ket noi WiFi. Cac sensor bat dau hoat dong!");

        mqtt_manager_init_relay(RELAY_GPIO_PIN);
        mqtt_manager_start();
        esp_wifi_set_ps(WIFI_PS_NONE);

        setenv("TZ", "ICT-7", 1);
        tzset();
        esp_sntp_config_t sntp_cfg = ESP_NETIF_SNTP_DEFAULT_CONFIG("pool.ntp.org");
        sntp_cfg.sync_cb = NULL;
        esp_netif_sntp_init(&sntp_cfg);
        water_data_get()->mode = FLOW_MODE_IDLE;
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "Mat ket noi WiFi. Dang thu ket noi lai...");
        xEventGroupClearBits(water_data_get_event_group(), WIFI_CONNECTED_BIT);
        s_wifi_connected = false;
        esp_wifi_connect();
    }
}

static void wifi_init_sta(const char *ssid, const char *password) {
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_sta_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, ESP_EVENT_ANY_ID, &wifi_sta_event_handler, NULL));

    wifi_config_t sta_config = {
        .sta = {
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
            .pmf_cfg = { .capable = true, .required = false },
        },
    };
    memcpy(sta_config.sta.ssid, ssid, sizeof(sta_config.sta.ssid));
    if (password && strlen(password) > 0) {
        memcpy(sta_config.sta.password, password, sizeof(sta_config.sta.password));
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi STA ket noi toi SSID=%s", ssid);
}

static void wifi_init_softap(void) {
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_ap_event_handler, NULL));

    wifi_config_t ap_config = {
        .ap = {
            .ssid_hidden = 0,
            .channel = 6,
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
            .pmf_cfg = { .capable = true, .required = false },
        },
    };
    strncpy((char *)ap_config.ap.ssid, WATER_WIFI_AP_SSID, sizeof(ap_config.ap.ssid));
    if (strlen(WATER_WIFI_AP_PASSWORD) >= 8) {
        strncpy((char *)ap_config.ap.password, WATER_WIFI_AP_PASSWORD, sizeof(ap_config.ap.password));
        ap_config.ap.authmode = WIFI_AUTH_WPA_WPA2_PSK;
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "SoftAP '%s' dang phat song WiFi!", WATER_WIFI_AP_SSID);
    ESP_LOGI(TAG, "Password: %s", strlen(WATER_WIFI_AP_PASSWORD) >= 8 ? WATER_WIFI_AP_PASSWORD : "(khong co)");
    ESP_LOGI(TAG, "Vao 192.168.4.1 de cau hinh WiFi");
}

void wifi_manager_init(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    char saved_ssid[64] = {0};
    char saved_pass[64] = {0};
    size_t ssid_len = sizeof(saved_ssid);
    size_t pass_len = sizeof(saved_pass);
    esp_err_t err = wifi_config_load(saved_ssid, &ssid_len, saved_pass, &pass_len);

    if (err == ESP_OK && strlen(saved_ssid) > 0) {
        ESP_LOGI(TAG, "Tim thay cau hinh WiFi da luu: %s", saved_ssid);
        ESP_LOGI(TAG, "Dang thu ket noi...");
        wifi_init_sta(saved_ssid, saved_pass);
    } else {
        ESP_LOGI(TAG, "Chua co cau hinh WiFi. Phat SoftAP de cau hinh...");
        wifi_init_softap();
        start_http_server();
        water_data_get()->mode = FLOW_MODE_CONFIG;
    }
}

void wifi_manager_reset(void) {
    wifi_manager_clear_config();
    esp_restart();
}