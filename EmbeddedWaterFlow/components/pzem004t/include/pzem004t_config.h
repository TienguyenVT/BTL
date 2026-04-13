#pragma once

#include "driver/gpio.h"

#define PZEM_UART_NUM              UART_NUM_1

#define PZEM_TX_PIN                GPIO_NUM_25

#define PZEM_RX_PIN                GPIO_NUM_26

#define PZEM_BAUD_RATE             9600
#define PZEM_DATA_BITS             UART_DATA_8_BITS
#define PZEM_PARITY               UART_PARITY_DISABLE
#define PZEM_STOP_BITS             UART_STOP_BITS_1

#define PZEM_READ_INTERVAL_MS      1000

#define PZEM_MAX_RETRIES           3

#define PZEM_UART_TIMEOUT_MS       500

#define PZEM_DEFAULT_ADDR          0xF8
