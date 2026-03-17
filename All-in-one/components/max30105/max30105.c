#include "max30105.h"
#include "esp_log.h"

static const char *TAG = "MAX30105";

// Register Map
#define MAX30105_INTSTAT1 0x00
#define MAX30105_INTSTAT2 0x01
#define MAX30105_INTENABLE1 0x02
#define MAX30105_INTENABLE2 0x03
#define MAX30105_FIFOWRITEPTR 0x04
#define MAX30105_OVFCOUNTER 0x05
#define MAX30105_FIFOREADPTR 0x06
#define MAX30105_FIFODATA 0x07
#define MAX30105_FIFOCONFIG 0x08
#define MAX30105_MODECONFIG 0x09
#define MAX30105_PARTICLECONFIG 0x0A
#define MAX30105_LED1_PULSEAMP 0x0C
#define MAX30105_LED2_PULSEAMP 0x0D
#define MAX30105_LED3_PULSEAMP 0x0E
#define MAX30105_LED_PROX_AMP 0x10
#define MAX30105_MULTILEDCONFIG1 0x11
#define MAX30105_MULTILEDCONFIG2 0x12
#define MAX30105_DIE_TEMP_INT 0x1F
#define MAX30105_DIE_TEMP_FRAC 0x20
#define MAX30105_DIE_TEMP_CONFIG 0x21
#define MAX30105_PROXINTTHRESH 0x30
#define MAX30105_REVID 0xFE
#define MAX30105_PARTID 0xFF

// Settings
#define MAX30105_SAMPLEAVG_MASK 0xE0
#define MAX30105_SAMPLEAVG_1 0x00
#define MAX30105_SAMPLEAVG_2 0x20
#define MAX30105_SAMPLEAVG_4 0x40
#define MAX30105_SAMPLEAVG_8 0x60
#define MAX30105_SAMPLEAVG_16 0x80
#define MAX30105_SAMPLEAVG_32 0xA0

#define MAX30105_ROLLOVER_MASK 0x10
#define MAX30105_ROLLOVER_ENABLE 0x10

#define MAX30105_A_FULL_MASK 0x0F

#define MAX30105_SHUTDOWN_MASK 0x80
#define MAX30105_SHUTDOWN 0x80
#define MAX30105_WAKEUP 0x00

#define MAX30105_RESET_MASK 0x40
#define MAX30105_RESET 0x40

#define MAX30105_MODE_MASK 0x07
#define MAX30105_MODE_REDONLY 0x02
#define MAX30105_MODE_REDIRONLY 0x03
#define MAX30105_MODE_MULTILED 0x07

#define MAX30105_ADCRANGE_MASK 0x60
#define MAX30105_ADCRANGE_2048 0x00
#define MAX30105_ADCRANGE_4096 0x20
#define MAX30105_ADCRANGE_8192 0x40
#define MAX30105_ADCRANGE_16384 0x60

#define MAX30105_SAMPLERATE_MASK 0x1C
#define MAX30105_SAMPLERATE_50 0x00
#define MAX30105_SAMPLERATE_100 0x04
#define MAX30105_SAMPLERATE_200 0x08
#define MAX30105_SAMPLERATE_400 0x0C
#define MAX30105_SAMPLERATE_800 0x10
#define MAX30105_SAMPLERATE_1000 0x14
#define MAX30105_SAMPLERATE_1600 0x18
#define MAX30105_SAMPLERATE_3200 0x1C

#define MAX30105_PULSEWIDTH_MASK 0x03
#define MAX30105_PULSEWIDTH_69 0x00
#define MAX30105_PULSEWIDTH_118 0x01
#define MAX30105_PULSEWIDTH_215 0x02
#define MAX30105_PULSEWIDTH_411 0x03

// Internal buffer for simplified interaction (simulating Arduino library
// behavior)
#define STORAGE_SIZE 4 // Must be power of 2
typedef struct {
  uint32_t red[STORAGE_SIZE];
  uint32_t ir[STORAGE_SIZE];
  uint32_t green[STORAGE_SIZE];
  uint8_t head;
  uint8_t tail;
} sense_struct;

static sense_struct sense;

// --- Low Level I2C ---

uint8_t max30105_readRegister8(max30105_t *sensor, uint8_t reg) {
  uint8_t data = 0;
  i2c_cmd_handle_t cmd = i2c_cmd_link_create();
  i2c_master_start(cmd);
  i2c_master_write_byte(cmd, (sensor->i2c_address << 1) | I2C_MASTER_WRITE,
                        true);
  i2c_master_write_byte(cmd, reg, true);
  i2c_master_start(cmd);
  i2c_master_write_byte(cmd, (sensor->i2c_address << 1) | I2C_MASTER_READ,
                        true);
  i2c_master_read_byte(cmd, &data, I2C_MASTER_LAST_NACK);
  i2c_master_stop(cmd);
  i2c_master_cmd_begin(sensor->i2c_port, cmd, pdMS_TO_TICKS(100));
  i2c_cmd_link_delete(cmd);
  return data;
}

void max30105_writeRegister8(max30105_t *sensor, uint8_t reg, uint8_t value) {
  i2c_cmd_handle_t cmd = i2c_cmd_link_create();
  i2c_master_start(cmd);
  i2c_master_write_byte(cmd, (sensor->i2c_address << 1) | I2C_MASTER_WRITE,
                        true);
  i2c_master_write_byte(cmd, reg, true);
  i2c_master_write_byte(cmd, value, true);
  i2c_master_stop(cmd);
  i2c_master_cmd_begin(sensor->i2c_port, cmd, pdMS_TO_TICKS(100));
  i2c_cmd_link_delete(cmd);
}

// --- Public API ---

bool max30105_begin(max30105_t *sensor, i2c_port_t port, uint32_t speed) {
  sensor->i2c_port = port;
  sensor->i2c_address = MAX30105_ADDRESS;

  // Check Part ID
  uint8_t partId = max30105_readRegister8(sensor, MAX30105_PARTID);
  if (partId != 0x15) { // MAX30105 and MAX30102 usually return 0x15
    // Some variants might be different, but 0x15 is standard
    ESP_LOGW(TAG, "Device not found or Part ID mismatch: 0x%02X", partId);
    // Don't fail hard for now, just warn
    // return false;
  }

  // Reset
  max30105_writeRegister8(sensor, MAX30105_MODECONFIG, MAX30105_RESET);
  vTaskDelay(pdMS_TO_TICKS(10));

  // Initial State: FIFO Config
  // smp_ave = 8, rollover = enable, fifo_a_full = 17
  max30105_writeRegister8(sensor, MAX30105_FIFOCONFIG,
                          (0x04 << 5) | 0x10 | 0x0F);

  return true;
}

void max30105_setup(max30105_t *sensor, uint8_t powerLevel,
                    uint8_t sampleAverage, uint8_t ledMode, int sampleRate,
                    int pulseWidth, int adcRange) {
  // Soft Reset
  max30105_writeRegister8(sensor, MAX30105_MODECONFIG, MAX30105_RESET);
  vTaskDelay(pdMS_TO_TICKS(10));

  // FIFO Config
  uint8_t sampleAvgVal = MAX30105_SAMPLEAVG_4; // Default to 4
  if (sampleAverage == 1)
    sampleAvgVal = MAX30105_SAMPLEAVG_1;
  else if (sampleAverage == 2)
    sampleAvgVal = MAX30105_SAMPLEAVG_2;
  else if (sampleAverage == 4)
    sampleAvgVal = MAX30105_SAMPLEAVG_4;
  else if (sampleAverage == 8)
    sampleAvgVal = MAX30105_SAMPLEAVG_8;
  else if (sampleAverage == 16)
    sampleAvgVal = MAX30105_SAMPLEAVG_16;
  else if (sampleAverage == 32)
    sampleAvgVal = MAX30105_SAMPLEAVG_32;

  max30105_writeRegister8(sensor, MAX30105_FIFOCONFIG,
                          sampleAvgVal | MAX30105_ROLLOVER_ENABLE | 0x0F);

  // Mode Config
  uint8_t modeVal = MAX30105_MODE_REDIRONLY;
  if (ledMode == 3)
    modeVal = MAX30105_MODE_MULTILED;
  else if (ledMode == 2)
    modeVal = MAX30105_MODE_REDIRONLY;
  else
    modeVal = MAX30105_MODE_REDONLY;

  max30105_writeRegister8(sensor, MAX30105_MODECONFIG, modeVal);

  // Particle Config
  uint8_t srVal = MAX30105_SAMPLERATE_100;
  if (sampleRate < 100)
    srVal = MAX30105_SAMPLERATE_50;
  else if (sampleRate < 200)
    srVal = MAX30105_SAMPLERATE_100;
  else if (sampleRate < 400)
    srVal = MAX30105_SAMPLERATE_200;
  else if (sampleRate < 800)
    srVal = MAX30105_SAMPLERATE_400;
  else if (sampleRate < 1000)
    srVal = MAX30105_SAMPLERATE_800;
  else if (sampleRate < 1600)
    srVal = MAX30105_SAMPLERATE_1000;
  else if (sampleRate < 3200)
    srVal = MAX30105_SAMPLERATE_1600;
  else
    srVal = MAX30105_SAMPLERATE_3200;

  uint8_t pwVal = MAX30105_PULSEWIDTH_411;
  if (pulseWidth < 118)
    pwVal = MAX30105_PULSEWIDTH_69;
  else if (pulseWidth < 215)
    pwVal = MAX30105_PULSEWIDTH_118;
  else if (pulseWidth < 411)
    pwVal = MAX30105_PULSEWIDTH_215;
  else
    pwVal = MAX30105_PULSEWIDTH_411;

  uint8_t adcVal = MAX30105_ADCRANGE_4096;
  if (adcRange < 4096)
    adcVal = MAX30105_ADCRANGE_2048;
  else if (adcRange < 8192)
    adcVal = MAX30105_ADCRANGE_4096;
  else if (adcRange < 16384)
    adcVal = MAX30105_ADCRANGE_8192;
  else
    adcVal = MAX30105_ADCRANGE_16384;

  max30105_writeRegister8(sensor, MAX30105_PARTICLECONFIG,
                          adcVal | srVal | pwVal);

  // LED Pulse Amplitude
  max30105_writeRegister8(sensor, MAX30105_LED1_PULSEAMP, powerLevel); // Red
  max30105_writeRegister8(sensor, MAX30105_LED2_PULSEAMP, powerLevel); // IR
  max30105_writeRegister8(sensor, MAX30105_LED3_PULSEAMP,
                          powerLevel); // Green (MAX30105 only)
  max30105_writeRegister8(sensor, MAX30105_LED_PROX_AMP, powerLevel); // Pilot

  // Multi-LED Mode Config (if needed)
  max30105_writeRegister8(sensor, MAX30105_MULTILEDCONFIG1,
                          0x03); // Slot1=Red, Slot2=IR
  max30105_writeRegister8(sensor, MAX30105_MULTILEDCONFIG2, 0x00); //

  // Reset FIFO
  max30105_writeRegister8(sensor, MAX30105_FIFOWRITEPTR, 0);
  max30105_writeRegister8(sensor, MAX30105_OVFCOUNTER, 0);
  max30105_writeRegister8(sensor, MAX30105_FIFOREADPTR, 0);

  // Initialize local buffer
  sense.head = 0;
  sense.tail = 0;
}

uint32_t max30105_getRed(void) { return sense.red[sense.tail]; }

uint32_t max30105_getIR(void) { return sense.ir[sense.tail]; }

uint32_t max30105_getGreen(void) { return sense.green[sense.tail]; }

bool max30105_available(void) {
  int8_t numberOfSamples = sense.head - sense.tail;
  if (numberOfSamples < 0)
    numberOfSamples += STORAGE_SIZE;
  return (numberOfSamples > 0);
}

void max30105_nextSample(void) {
  if (max30105_available()) {
    sense.tail++;
    sense.tail %= STORAGE_SIZE;
  }
}

void max30105_check(max30105_t *sensor) {
  // Read Write/Read Pointers
  uint8_t readPointer = max30105_readRegister8(sensor, MAX30105_FIFOREADPTR);
  uint8_t writePointer = max30105_readRegister8(sensor, MAX30105_FIFOWRITEPTR);

  int numberOfSamples = writePointer - readPointer;
  if (numberOfSamples < 0)
    numberOfSamples += 32;

  // Read bytes
  // int bytesToRead = numberOfSamples * 6; // 3 bytes for red, 3 for IR (Mode
  // 2) Note: If Mode 3 (MultiLED) with Green, it might be 9 bytes or different
  // slots

  // For simplicity, we assume Red + IR (Mode 2 standard) or MultiLED config
  // with Slot1/2 = Red/IR To be safer, we can read up to STORAGE_SIZE samples
  // to fill our local buffer

  while (numberOfSamples > 0) {
    // Read one sample (6 bytes)
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (sensor->i2c_address << 1) | I2C_MASTER_WRITE,
                          true);
    i2c_master_write_byte(cmd, MAX30105_FIFODATA, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (sensor->i2c_address << 1) | I2C_MASTER_READ,
                          true);

    uint8_t temp[6];
    i2c_master_read(cmd, temp, 6, I2C_MASTER_LAST_NACK);
    i2c_master_stop(cmd);
    i2c_master_cmd_begin(sensor->i2c_port, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);

    // Parse 3 bytes Red, 3 bytes IR
    uint32_t redLed = ((uint32_t)temp[0] << 16) | ((uint32_t)temp[1] << 8) |
                      (uint32_t)temp[2];
    redLed &= 0x3FFFF; // Mask to 18 bits

    uint32_t irLed = ((uint32_t)temp[3] << 16) | ((uint32_t)temp[4] << 8) |
                     (uint32_t)temp[5];
    irLed &= 0x3FFFF;

    // Store to buffer
    sense.red[sense.head] = redLed;
    sense.ir[sense.head] = irLed;
    sense.head++;
    sense.head %= STORAGE_SIZE; // Circular buffer

    numberOfSamples--;
  }
}
