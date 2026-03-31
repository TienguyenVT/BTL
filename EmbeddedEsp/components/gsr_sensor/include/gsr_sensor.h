#ifndef __GSR_SENSOR_H__
#define __GSR_SENSOR_H__

#include "gsr_config.h"

// FreeRTOS task function — đọc GSR, phát hiện stress, cập nhật health_data
void gsr_sensor_task(void *pvParameters);

#endif // __GSR_SENSOR_H__
