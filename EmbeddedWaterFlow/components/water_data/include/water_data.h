#ifndef __WATER_DATA_H__
#define __WATER_DATA_H__

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

#define WIFI_CONNECTED_BIT BIT0

typedef enum {
    FLOW_MODE_CONFIG,   
    FLOW_MODE_IDLE,     
    FLOW_MODE_ACTIVE,   
    FLOW_MODE_LEAK,   
} flow_mode_t;

typedef struct {
    float flow_rate;         
    float total_volume;      
    volatile uint32_t pulse_count;  
    bool flow_detected;      
    flow_mode_t mode;        

    float voltage;           
    float current;           
    float power;            

    float total_energy_wh;   
    float total_energy_kwh;  
    uint32_t last_energy_tick; 

    char mac_address[18];    
} water_sensor_data_t;

water_sensor_data_t *water_data_get(void);
EventGroupHandle_t water_data_get_event_group(void);
void water_data_init(void);
void water_data_update_energy(uint32_t current_tick_ms);

#endif 
