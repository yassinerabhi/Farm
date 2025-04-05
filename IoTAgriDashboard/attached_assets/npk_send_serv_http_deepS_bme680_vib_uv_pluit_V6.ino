#include <ArduinoHttpClient.h>
#include <HardwareSerial.h>
#include <array>
#include <vector>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>
#include <EEPROM.h>
#define TINY_GSM_MODEM_SIM800
#include <TinyGsmClient.h>
#include <TinyGSM.h>
#include <SPIFFS.h>
#include <ArduinoJson.h>

// Constants
constexpr int RE_PIN = 18;
constexpr int DE_PIN = 19;
constexpr int VBAT_PIN = 34;
constexpr float BATTV_MAX = 4.18;
constexpr float BATTV_MIN = 3.5;
constexpr float BATTV_LOW = 3.7;
constexpr int NUM_SAMPLES = 20;
constexpr int BAUD_RATE = 9600;
constexpr int MOD_BAUD_RATE = 4800;
constexpr int RX_PIN = 13;
constexpr int TX_PIN = 23;
constexpr uint32_t TIMEOUT = 1000UL;
constexpr int TIME_TO_SLEEP = 30 * 60; // 30 minutes in seconds
constexpr float VOLT_CONVERSION = 3.3 / 4095 * 5.78;
constexpr int UV_SENSOR_PIN = 36;
const int rainSensorPin = 39;


// Seuils pour la détection de la pluie
const int rainThreshold = 30; // Pourcentage en dessous duquel il pleut
const int heavyRainThreshold = 70; // Pourcentage en dessous duquel il pleut beaucoup

#define SEALEVELPRESSURE_HPA (1013.25)

// SIM800C module pins
#define MODEM_RST            5
#define MODEM_PWKEY          4
#define MODEM_POWER_ON       25
#define MODEM_TX             27
#define MODEM_RX             26
#define MODEM_DTR            32
#define MODEM_RI             33
#define I2C_SDA_2            14
#define I2C_SCL_2            15
#define VIBRATION_SENSOR_PIN GPIO_NUM_12

// GPRS configurations
const char apn[] = "weborange";
const char gprsUser[] = "";
const char gprsPass[] = "";
const char serverAddress[] = "148.113.202.219";
const int serverPort = 5000;

const int EEPROM_SIZE = 512;
const int DEVICE_ID_ADDRESS = 0;
const int DEVICE_ID_LENGTH = 12;

// Data structures
struct SensorData {
    float moisture;
    float temperature;
    int ec;
    float ph;
    int nitrogen;
    int phosphorous;
    int potassium;
    float salinity;
    float bme_temperature;
    float bme_humidity;
    float bme_pressure;
    float bme_gas;
    float uv_index;
};

// Global variables
RTC_DATA_ATTR int bootCount = 0;
HardwareSerial mod(1);
HardwareSerial SerialAT(2);
TinyGsm modem(SerialAT);
TinyGsmClient client(modem);
HttpClient http(client, serverAddress, serverPort);

std::array<float, NUM_SAMPLES> samples;
int sampleIndex = 0;
float total = 0;
float battv = 0;
uint8_t battpc = 0;
SensorData sensorData;
Adafruit_BME680 bme;
String wakeupReason;
String deviceId;

// Variables pour la moyenne glissante
const int numReadings = 10;
int readings[numReadings];      // Les lectures du capteur
int readIndex = 0;              // L'index actuel
int totalR = 0;                  // La somme des lectures
int average = 0;                // La moyenne des lectures

// Sensor commands
const std::vector<std::array<byte, 8>> sensorCommands = {
    {0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A},
    {0x01, 0x03, 0x00, 0x01, 0x00, 0x01, 0xD5, 0xCA},
    {0x01, 0x03, 0x00, 0x02, 0x00, 0x01, 0x25, 0xCA},
    {0x01, 0x03, 0x00, 0x03, 0x00, 0x01, 0x74, 0x0A},
    {0x01, 0x03, 0x00, 0x04, 0x00, 0x01, 0xC5, 0xCB},
    {0x01, 0x03, 0x00, 0x05, 0x00, 0x01, 0x94, 0x0B},
    {0x01, 0x03, 0x00, 0x06, 0x00, 0x01, 0x64, 0x0B},
    {0x01, 0x03, 0x00, 0x07, 0x00, 0x01, 0x35, 0xCB}
};

// Function prototypes
void checkWakeupReason();
void resetModem();
bool isModemResponding();
void initModem();
void initRS485();
void initBME680();
uint16_t getValue(byte sensorIndex);
void readBME680();
float readUVSensor();
void readAllSensors();
void updateBatteryInfo();
String createPayload();
void sendData();
String getUniqueDeviceId();
void storeDataLocally(const String& payload);
void sendStoredData();
void initSPIFFS();
void readAndAnalyzeRainSensor();

void checkSignalStrength() {
    int csq = modem.getSignalQuality();
    Serial.println("Signal quality: " + String(csq));
}

void setup() {
    Serial.begin(BAUD_RATE);
    delay(1000);

    checkWakeupReason();
    deviceId = getUniqueDeviceId();
    Serial.println("Device ID: " + deviceId);

    delay(4000);

    mod.begin(MOD_BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
    pinMode(2, OUTPUT);
    pinMode(VIBRATION_SENSOR_PIN, INPUT);
    pinMode(UV_SENSOR_PIN, INPUT);

    initModem();
    initSPIFFS();

    if (!isModemResponding()) {
        Serial.println("Modem not responding. Trying to reset...");
        resetModem();
        if (!isModemResponding()) {
            Serial.println("Modem still not responding. Power cycling...");
            initModem();
        }
    }

    initRS485();
    initBME680();
    pinMode(VBAT_PIN, INPUT);

    for (int i = 0; i < NUM_SAMPLES; i++) {
        samples[i] = analogRead(VBAT_PIN) * VOLT_CONVERSION;
        total += samples[i];
    }

  // Initialiser le tableau des lectures à 0
  for (int i = 0; i < numReadings; i++) {
    readings[i] = 0;
  }

    digitalWrite(2, HIGH);
    delay(1000);

    for (int i = 0; i < 5; i++) {
        readAllSensors();
        updateBatteryInfo();
        readAndAnalyzeRainSensor();
    }
    digitalWrite(2, LOW);
    delay(1000);
    sendData();
    sendStoredData();

    // Configure wake-up sources
    esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * 1000000ULL);
    esp_sleep_enable_ext0_wakeup(VIBRATION_SENSOR_PIN, HIGH);

    Serial.println("Going to sleep for 30 minutes. Will wake up by timer or vibration.");
    Serial.flush();
    esp_deep_sleep_start();
}

void loop() {
    // This function will never be executed due to the use of deep sleep
}


void readAndAnalyzeRainSensor() {
  // Variables pour stocker les valeurs du capteur
  int sensorValue = 0;
  int mappedValue = 0;

  // Soustraire la dernière lecture de la somme
  totalR = totalR - readings[readIndex];
  
  // Lire la nouvelle valeur du capteur de pluie
  sensorValue = analogRead(rainSensorPin);
  
  // Mapper la valeur lue (4095 à 0) sur une échelle de 0 à 100 (pourcentage)
  mappedValue = map(sensorValue, 4095, 0, 0, 100);
  
  // Ajouter la nouvelle valeur à la somme
  totalR = totalR + mappedValue;
  
  // Stocker la nouvelle lecture dans le tableau
  readings[readIndex] = mappedValue;
  
  // Avancer à la prochaine position dans le tableau
  readIndex = readIndex + 1;
  
  // Si nous avons atteint la fin du tableau, recommencer au début
  if (readIndex >= numReadings) {
    readIndex = 0;
  }
  
  // Calculer la moyenne des lectures
  average = totalR / numReadings;
  
  // Afficher la valeur lue, la valeur mappée et la moyenne
  Serial.print("Valeur du capteur de pluie: ");
  Serial.print(sensorValue);
  Serial.print(" | Valeur mappée: ");
  Serial.print(mappedValue);
  Serial.print(" | Moyenne: ");
  Serial.println(average);
  
  // Déterminer s'il pleut ou non
  if (average > rainThreshold) {
    if (average > heavyRainThreshold) {
      Serial.println("Il pleut beaucoup.");
    } else {
      Serial.println("Il pleut.");
    }
  } else {
    Serial.println("Pas de pluie.");
  }
}

// Function implementations
void checkWakeupReason() {
    esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();

    switch(wakeup_reason) {
        case ESP_SLEEP_WAKEUP_EXT0:
            Serial.println("Wakeup caused by external signal using RTC_IO (vibration detected)");
            wakeupReason = "vibration";
            break;
        case ESP_SLEEP_WAKEUP_TIMER:
            Serial.println("Wakeup caused by timer");
            wakeupReason = "timer";
            break;
        default:
            Serial.println("Wakeup was not caused by deep sleep");
            wakeupReason = "unknown";
            break;
    }
}

void resetModem() {
    digitalWrite(MODEM_PWKEY, LOW);
    delay(1000);
    digitalWrite(MODEM_PWKEY, HIGH);
    delay(3000);
    digitalWrite(MODEM_RST, LOW);
    delay(100);
    digitalWrite(MODEM_RST, HIGH);
    delay(1000);
}

bool isModemResponding() {
    for (int i = 0; i < 5; i++) {
        if (modem.testAT()) {
            return true;
        }
        delay(1000);
    }
    return false;
}

void initModem() {
    pinMode(MODEM_PWKEY, OUTPUT);
    pinMode(MODEM_RST, OUTPUT);
    pinMode(MODEM_POWER_ON, OUTPUT);
    digitalWrite(MODEM_PWKEY, LOW);
    digitalWrite(MODEM_RST, HIGH);
    digitalWrite(MODEM_POWER_ON, HIGH);

    SerialAT.begin(115200, SERIAL_8N1, MODEM_RX, MODEM_TX);
    delay(4000);

    Serial.println("Initializing modem...");
    modem.restart();
}

void initRS485() {
    pinMode(RE_PIN, OUTPUT);
    pinMode(DE_PIN, OUTPUT);
    digitalWrite(DE_PIN, LOW);
    digitalWrite(RE_PIN, LOW);
    delay(3000);
}

void initBME680() {
    Wire.begin(I2C_SDA_2, I2C_SCL_2);
    if (!bme.begin()) {
        Serial.println("Could not find a valid BME680 sensor, check wiring!");
        while (1);
    }
    
    bme.setTemperatureOversampling(BME680_OS_8X);
    bme.setHumidityOversampling(BME680_OS_2X);
    bme.setPressureOversampling(BME680_OS_4X);
    bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
    bme.setGasHeater(320, 150); // 320*C for 150 ms
}

uint16_t getValue(byte sensorIndex) {
    if (sensorIndex >= sensorCommands.size()) return 0;
    
    digitalWrite(DE_PIN, HIGH);
    digitalWrite(RE_PIN, HIGH);
    delay(10);
    mod.write(sensorCommands[sensorIndex].data(), sensorCommands[sensorIndex].size());
    mod.flush();
    digitalWrite(DE_PIN, LOW);
    digitalWrite(RE_PIN, LOW);

    uint32_t startTime = millis();
    std::array<byte, 20> buff;
    size_t byteCount = 0;
    while (millis() - startTime <= TIMEOUT && byteCount < buff.size()) {
        if (mod.available()) {
            buff[byteCount++] = mod.read();
        }
    }

    if (byteCount >= 5) {
        return (uint16_t)(buff[3] << 8 | buff[4]);
    } else {
        Serial.println("Communication error");
        return 0;
    }
}

void readBME680() {
    if (!bme.performReading()) {
        Serial.println("Failed to perform reading from BME680");
        return;
    }
    
    sensorData.bme_temperature = bme.temperature;
    sensorData.bme_humidity = bme.humidity;
    sensorData.bme_pressure = bme.pressure / 100.0;
    sensorData.bme_gas = bme.gas_resistance / 1000.0;

    Serial.println("BME680 Readings:");
    Serial.println("Temperature: " + String(sensorData.bme_temperature) + " °C");
    Serial.println("Humidity: " + String(sensorData.bme_humidity) + " %");
    Serial.println("Pressure: " + String(sensorData.bme_pressure) + " hPa");
    Serial.println("Gas: " + String(sensorData.bme_gas) + " KOhms");
}

float readUVSensor() {
    int sensorValue = analogRead(UV_SENSOR_PIN);
    float voltage = sensorValue * (3.3 / 4095.0);
    float uvIndex = voltage / 0.1;
    return uvIndex;
}

void readAllSensors() {
    sensorData.moisture = getValue(0) / 10.0;
    sensorData.temperature = getValue(1) / 10.0;
    sensorData.ec = getValue(2);
    sensorData.ph = getValue(3) / 10.0;
    sensorData.nitrogen = getValue(4);
    sensorData.phosphorous = getValue(5);
    sensorData.potassium = getValue(6);
    sensorData.salinity = getValue(7) / 10.0;
    sensorData.uv_index = readUVSensor();

    Serial.println("Sensor Readings:");
    Serial.println("Moisture: " + String(sensorData.moisture));
    Serial.println("Temperature: " + String(sensorData.temperature));
    Serial.println("EC: " + String(sensorData.ec));
    Serial.println("pH: " + String(sensorData.ph));
    Serial.println("Nitrogen: " + String(sensorData.nitrogen));
    Serial.println("Phosphorous: " + String(sensorData.phosphorous));
    Serial.println("Potassium: " + String(sensorData.potassium));
    Serial.println("Salinity: " + String(sensorData.salinity));
    Serial.println("UV Index: " + String(sensorData.uv_index));

    readBME680();
    delay(1000);
}

void updateBatteryInfo() {
    int rawValue = analogRead(VBAT_PIN);
    float currentValue = rawValue * VOLT_CONVERSION;
    Serial.println("Raw battery value: " + String(rawValue));
    total -= samples[sampleIndex];
    samples[sampleIndex] = currentValue;
    total += currentValue;
    sampleIndex = (sampleIndex + 1) % NUM_SAMPLES;

    battv = total / NUM_SAMPLES;
    battpc = (uint8_t)(((battv - BATTV_MIN) / (BATTV_MAX - BATTV_MIN)) * 100);

    Serial.println("Battery Voltage: " + String(battv));
    Serial.println("Battery Percentage: " + String(battpc));
}

String createPayload() {
    String payload = "{";
    payload += "\"device_id\":\"" + deviceId + "\",";
    payload += "\"battv\":" + String(battv) + ",";
    payload += "\"battpc\":" + String(battpc) + ",";
payload += "\"moisture\":" + String(sensorData.moisture) + ",";
    payload += "\"temperature\":" + String(sensorData.temperature) + ",";
    payload += "\"ec\":" + String(sensorData.ec) + ",";
    payload += "\"ph\":" + String(sensorData.ph) + ",";
    payload += "\"nitrogen\":" + String(sensorData.nitrogen) + ",";
    payload += "\"phosphorous\":" + String(sensorData.phosphorous) + ",";
    payload += "\"potassium\":" + String(sensorData.potassium) + ",";
    payload += "\"salinity\":" + String(sensorData.salinity) + ",";
    payload += "\"bme_temperature\":" + String(sensorData.bme_temperature) + ",";
    payload += "\"bme_humidity\":" + String(sensorData.bme_humidity) + ",";
    payload += "\"bme_pressure\":" + String(sensorData.bme_pressure) + ",";
    payload += "\"bme_gas\":" + String(sensorData.bme_gas) + ",";
    payload += "\"uv_index\":" + String(sensorData.uv_index) + ",";
    payload += "\"pluie\":" + String(average) + ",";
    payload += "\"wakeup_reason\":\"" + wakeupReason + "\"";
    payload += "}";
    return payload;
}

void sendData() {
    Serial.println("Connecting to GPRS network...");
    if (!modem.gprsConnect(apn, gprsUser, gprsPass)) {
        Serial.println("GPRS connection failed");
        String payload = createPayload();
        storeDataLocally(payload);
        return;
    }
    Serial.println("GPRS connected");

    Serial.println("Sending data to server...");
    http.beginRequest();
    http.post("/data");
    http.sendHeader("Content-Type", "application/json");
    String payload = createPayload();
    http.sendHeader("Content-Length", payload.length());
    http.beginBody();
    http.print(payload);
    http.endRequest();

    int statusCode = http.responseStatusCode();
    String response = http.responseBody();

    Serial.println("Status code: " + String(statusCode));
    Serial.println("Response: " + response);

    if (statusCode != 200) {
        Serial.println("Failed to send data to server. Storing locally.");
        storeDataLocally(payload);
    }

    http.stop();
    modem.gprsDisconnect();
    Serial.println("GPRS disconnected");
}

String getUniqueDeviceId() {
    EEPROM.begin(EEPROM_SIZE);
    String id = "";
    for (int i = 0; i < DEVICE_ID_LENGTH; i++) {
        char c = EEPROM.read(DEVICE_ID_ADDRESS + i);
        if (c != 0 && c != 255) {
            id += c;
        }
    }
    
    if (id.length() != DEVICE_ID_LENGTH) {
        id = "";
        for (int i = 0; i < DEVICE_ID_LENGTH; i++) {
            char c = random(0, 36) < 26 ? char('A' + random(0, 26)) : char('0' + random(0, 10));
            id += c;
            EEPROM.write(DEVICE_ID_ADDRESS + i, c);
        }
        EEPROM.commit();
    }
    
    EEPROM.end();
    return id;
}

void initSPIFFS() {
    if (!SPIFFS.begin(true)) {
        Serial.println("An error has occurred while mounting SPIFFS");
        return;
    }
    Serial.println("SPIFFS mounted successfully");
}

void storeDataLocally(const String& payload) {
    File file = SPIFFS.open("/stored_data.json", FILE_APPEND);
    if (!file) {
        Serial.println("Failed to open file for appending");
        return;
    }
    if (file.println(payload)) {
        Serial.println("Data stored locally");
    } else {
        Serial.println("Failed to store data locally");
    }
    file.close();
}

void sendStoredData() {
    if (!SPIFFS.exists("/stored_data.json")) {
        Serial.println("No stored data to send");
        return;
    }

    File file = SPIFFS.open("/stored_data.json", FILE_READ);
    if (!file) {
        Serial.println("Failed to open file for reading");
        return;
    }

    Serial.println("Sending stored data...");
    if (!modem.gprsConnect(apn, gprsUser, gprsPass)) {
        Serial.println("GPRS connection failed");
        file.close();
        return;
    }

    bool allDataSent = true;
    String line;
    while (file.available()) {
        line = file.readStringUntil('\n');
        line.trim();
        if (line.length() > 0) {
            http.beginRequest();
            http.post("/data");
            http.sendHeader("Content-Type", "application/json");
            http.sendHeader("Content-Length", line.length());
            http.beginBody();
            http.print(line);
            http.endRequest();

            int statusCode = http.responseStatusCode();
            String response = http.responseBody();

            Serial.println("Status code: " + String(statusCode));
            Serial.println("Response: " + response);

            if (statusCode != 200) {
                allDataSent = false;
                break;
            }
        }
    }

    file.close();
    http.stop();
    modem.gprsDisconnect();

    if (allDataSent) {
        Serial.println("All stored data sent successfully. Deleting local file.");
        SPIFFS.remove("/stored_data.json");
    } else {
        Serial.println("Not all data could be sent. Keeping remaining data in local storage.");
    }
}