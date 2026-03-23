#include "ds18b20.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_rom_sys.h"

static gpio_num_t ds_pin;
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

static void ds_delay_us(uint32_t us) {
    esp_rom_delay_us(us);
}

static void ds_write_bit(int b) {
    gpio_set_direction(ds_pin, GPIO_MODE_OUTPUT);
    portENTER_CRITICAL(&mux);
    gpio_set_level(ds_pin, 0);
    ds_delay_us(b ? 3 : 60);
    gpio_set_direction(ds_pin, GPIO_MODE_INPUT);
    ds_delay_us(b ? 60 : 3);
    portEXIT_CRITICAL(&mux);
}

static int ds_read_bit(void) {
    int b = 0;
    gpio_set_direction(ds_pin, GPIO_MODE_OUTPUT);
    portENTER_CRITICAL(&mux);
    gpio_set_level(ds_pin, 0);
    ds_delay_us(2);
    gpio_set_direction(ds_pin, GPIO_MODE_INPUT);
    ds_delay_us(10);
    b = gpio_get_level(ds_pin);
    ds_delay_us(50);
    portEXIT_CRITICAL(&mux);
    return b;
}

static void ds_write_byte(uint8_t byte) {
    for (int i = 0; i < 8; i++) {
        ds_write_bit(byte & 0x01);
        byte >>= 1;
    }
}

static uint8_t ds_read_byte(void) {
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        byte >>= 1;
        if (ds_read_bit()) {
            byte |= 0x80;
        }
    }
    return byte;
}

static bool ds_reset(void) {
    int presence = 0;
    gpio_set_direction(ds_pin, GPIO_MODE_OUTPUT);
    
    portENTER_CRITICAL(&mux);
    gpio_set_level(ds_pin, 0);
    ds_delay_us(480);
    gpio_set_direction(ds_pin, GPIO_MODE_INPUT);
    ds_delay_us(70);
    presence = gpio_get_level(ds_pin);
    ds_delay_us(410);
    portEXIT_CRITICAL(&mux);
    
    return (presence == 0);
}

void ds18b20_init(gpio_num_t pin) {
    ds_pin = pin;
    gpio_reset_pin(ds_pin);
    gpio_set_direction(ds_pin, GPIO_MODE_INPUT);
    gpio_set_pull_mode(ds_pin, GPIO_PULLUP_ONLY); // Nội trở kéo lên tích hợp, hoạt động với cáp ngắn
}

float ds18b20_get_temp(void) {
    if (!ds_reset()) return -999.0;
    ds_write_byte(0xCC); // Skip ROM command
    ds_write_byte(0x44); // Convert T command
    
    // Đợi cảm biến chuyển đổi nhiệt độ (độ phân giải 12-bit tốn tối đa ~750ms)
    vTaskDelay(pdMS_TO_TICKS(750));
    
    if (!ds_reset()) return -999.0;
    ds_write_byte(0xCC); // Skip ROM
    ds_write_byte(0xBE); // Read Scratchpad
    
    uint8_t lsb = ds_read_byte();
    uint8_t msb = ds_read_byte();
    
    // Đọc nốt 7 byte còn lại cho chuẩn giao thức
    for (int i = 0; i < 7; i++) {
        ds_read_byte();
    }
    
    // Byte MSB và LSB chứa giá trị nhiệt độ, chia cho 16 để ra độ C
    int16_t raw_temp = (msb << 8) | lsb;
    return (float)raw_temp / 16.0;
}
