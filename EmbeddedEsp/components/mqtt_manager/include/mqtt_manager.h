#ifndef __MQTT_MANAGER_H__
#define __MQTT_MANAGER_H__

#include <stdbool.h>

// Khởi tạo và kết nối MQTT client tới HiveMQ Cloud
void mqtt_manager_start(void);

// Publish payload JSON lên topic
void mqtt_manager_publish(const char *topic, const char *payload);

// Kiểm tra trạng thái kết nối MQTT
bool mqtt_manager_is_connected(void);

#endif // __MQTT_MANAGER_H__
