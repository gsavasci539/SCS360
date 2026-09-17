/**
 * RFID Turnstile & Canteen System
 * Hardware: Wemos D1 Mini + MFRC522 RFID Reader
 * 
 * Features:
 * - Card reading and validation
 * - Canteen payment processing
 * - Balance loading
 * - Turnstile control
 * - Database communication via REST API
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>

// ==================== CONFIGURATION ====================

// WiFi Configuration
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// API Configuration
const char* API_BASE_URL = "http://YOUR_SERVER_IP:8000";
const char* API_KEY = "YOUR_API_KEY"; // Optional: if you implement API key authentication

// Hardware Pin Configuration
#define SS_PIN D2  // SDA/SS pin
#define RST_PIN D1 // RST pin
#define BUZZER_PIN D3
#define TURNSTILE_RELAY_PIN D4
#define LED_GREEN_PIN D5
#define LED_RED_PIN D6

// Device Configuration
const char* DEVICE_ID = "TURNSTILE_001";
const char* DEVICE_TYPE = "TURNSTILE";
const char* BRANCH_ID = "YOUR_BRANCH_ID"; // UUID of the branch

// Timing Configuration
#define CARD_READ_TIMEOUT 3000 // ms
#define API_TIMEOUT 10000 // ms
#define HEARTBEAT_INTERVAL 60000 // ms (1 minute)

// ==================== GLOBAL VARIABLES ====================

MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClient wifiClient;
HTTPClient http;

unsigned long lastHeartbeat = 0;
String lastCardUID = "";
unsigned long lastCardReadTime = 0;

// ==================== SETUP ====================

void setup() {
  Serial.begin(115200);
  while (!Serial);
  
  Serial.println("\n=== RFID Turnstile System Starting ===");
  
  // Initialize pins
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(TURNSTILE_RELAY_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  
  // Initial state
  digitalWrite(TURNSTILE_RELAY_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_RED_PIN, HIGH); // Red = not ready
  
  // Initialize SPI and RFID
  SPI.begin();
  rfid.PCD_Init();
  
  // Show RFID reader info
  rfid.PCD_DumpVersionToSerial();
  
  // Connect to WiFi
  connectWiFi();
  
  // Send device registration
  registerDevice();
  
  // Ready
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, HIGH);
  beepSuccess();
  
  Serial.println("System ready. Waiting for cards...");
}

// ==================== MAIN LOOP ====================

void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting...");
    connectWiFi();
  }
  
  // Send heartbeat
  if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
    sendHeartbeat();
    lastHeartbeat = millis();
  }
  
  // Read RFID card
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    // Debounce: prevent reading same card too quickly
    String currentCardUID = getCardUID();
    unsigned long currentTime = millis();
    
    if (currentCardUID != lastCardUID || (currentTime - lastCardReadTime > CARD_READ_TIMEOUT)) {
      lastCardUID = currentCardUID;
      lastCardReadTime = currentTime;
      
      Serial.println("Card detected: " + currentCardUID);
      
      // Process card
      processCard(currentCardUID);
    }
    
    // Halt PICC
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }
  
  delay(100);
}

// ==================== CARD PROCESSING ====================

void processCard(String cardUID) {
  Serial.println("Processing card: " + cardUID);
  
  // Validate card with database
  bool cardValid = validateCard(cardUID);
  
  if (!cardValid) {
    Serial.println("Card validation failed");
    beepError();
    blinkRed();
    return;
  }
  
  // Get card holder info
  JsonObject cardInfo = getCardInfo(cardUID);
  
  if (!cardInfo) {
    Serial.println("Failed to get card info");
    beepError();
    blinkRed();
    return;
  }
  
  String holderName = cardInfo["holder_name"].as<String>();
  String cardType = cardInfo["card_type"].as<String>();
  String holderId = cardInfo["holder_id"].as<String>();
  String status = cardInfo["status"].as<String>();
  
  Serial.println("Card holder: " + holderName);
  Serial.println("Card type: " + cardType);
  Serial.println("Card status: " + status);
  
  // Check if card is active
  if (status != "ACTIVE") {
    Serial.println("Card is not active");
    beepError();
    blinkRed();
    return;
  }
  
  // Based on device type, perform different actions
  if (String(DEVICE_TYPE) == "TURNSTILE") {
    handleTurnstileAccess(cardUID, holderId, holderName, cardType);
  } else if (String(DEVICE_TYPE) == "CANTEEN_TERMINAL") {
    handleCanteenPayment(cardUID, holderId, holderName);
  }
  
  beepSuccess();
  blinkGreen();
}

// ==================== TURNSTILE ACCESS ====================

void handleTurnstileAccess(String cardUID, String holderId, String holderName, String cardType) {
  Serial.println("Checking turnstile access for: " + holderName);
  
  // Check access permissions with API
  bool accessGranted = checkAccessPermission(holderId, cardType);
  
  if (accessGranted) {
    Serial.println("Access granted. Opening turnstile...");
    
    // Log access
    logAccess(cardUID, holderId, "GRANTED");
    
    // Activate turnstile relay
    digitalWrite(TURNSTILE_RELAY_PIN, HIGH);
    delay(1000); // Keep relay on for 1 second
    digitalWrite(TURNSTILE_RELAY_PIN, LOW);
    
    beepSuccess();
  } else {
    Serial.println("Access denied");
    
    // Log access
    logAccess(cardUID, holderId, "DENIED");
    
    beepError();
    blinkRed();
  }
}

// ==================== CANTEEN PAYMENT ====================

void handleCanteenPayment(String cardUID, String holderId, String holderName) {
  Serial.println("Processing canteen payment for: " + holderName);
  
  // Get wallet balance
  JsonObject walletInfo = getWalletInfo(holderId);
  
  if (!walletInfo) {
    Serial.println("Failed to get wallet info");
    beepError();
    blinkRed();
    return;
  }
  
  float balance = walletInfo["balance"].as<float>();
  float dailyLimit = walletInfo["daily_limit"].as<float>();
  float dailySpent = walletInfo["daily_spent"].as<float>();
  
  Serial.println("Balance: " + String(balance));
  Serial.println("Daily spent: " + String(dailySpent) + " / " + String(dailyLimit));
  
  // For canteen terminal, you would need to integrate with a POS system
  // This is a placeholder for the payment flow
  Serial.println("Canteen payment processing - integrate with POS");
  
  // Example: Process payment (you would get amount from POS)
  // float amount = 5.00;
  // bool paymentSuccess = processPayment(cardUID, holderId, amount);
  
  beepSuccess();
}

// ==================== API COMMUNICATION ====================

bool validateCard(String cardUID) {
  String url = String(API_BASE_URL) + "/api/rfid-cards/number/" + cardUID;
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    http.end();
    
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, payload);
    
    bool success = doc["success"];
    return success;
  } else {
    Serial.println("HTTP Error: " + String(httpCode));
    http.end();
    return false;
  }
}

JsonObject getCardInfo(String cardUID) {
  String url = String(API_BASE_URL) + "/api/rfid-cards/number/" + cardUID;
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    http.end();
    
    DynamicJsonDocument doc(2048);
    deserializeJson(doc, payload);
    
    if (doc["success"]) {
      return doc["data"].as<JsonObject>();
    }
  }
  
  http.end();
  return nullptr;
}

bool checkAccessPermission(String holderId, String cardType) {
  // This would check if the holder has access at this time
  // For now, we'll return true for active cards
  // You can implement time-based access, location-based access, etc.
  
  String url = String(API_BASE_URL) + "/api/access/check";
  
  DynamicJsonDocument doc(512);
  doc["holder_id"] = holderId;
  doc["card_type"] = cardType;
  doc["device_id"] = DEVICE_ID;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == 200) {
    String payload = http.getString();
    http.end();
    
    DynamicJsonDocument responseDoc(512);
    deserializeJson(responseDoc, payload);
    
    return responseDoc["access_granted"].as<bool>();
  }
  
  http.end();
  return true; // Default to allow if API fails
}

JsonObject getWalletInfo(String holderId) {
  String url = String(API_BASE_URL) + "/api/canteen/student/" + holderId + "/wallet";
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    http.end();
    
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, payload);
    
    if (doc["success"]) {
      return doc["data"].as<JsonObject>();
    }
  }
  
  http.end();
  return nullptr;
}

bool processPayment(String cardUID, String holderId, float amount) {
  String url = String(API_BASE_URL) + "/api/canteen/pos/checkout";
  
  DynamicJsonDocument doc(512);
  doc["card_number"] = cardUID;
  doc["holder_id"] = holderId;
  doc["amount"] = amount;
  doc["branch_id"] = BRANCH_ID;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == 200) {
    String payload = http.getString();
    http.end();
    
    DynamicJsonDocument responseDoc(1024);
    deserializeJson(responseDoc, payload);
    
    return responseDoc["authorized"].as<bool>();
  }
  
  http.end();
  return false;
}

bool logAccess(String cardUID, String holderId, String status) {
  String url = String(API_BASE_URL) + "/api/access/log";
  
  DynamicJsonDocument doc(512);
  doc["card_number"] = cardUID;
  doc["holder_id"] = holderId;
  doc["device_id"] = DEVICE_ID;
  doc["access_status"] = status;
  doc["branch_id"] = BRANCH_ID;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  int httpCode = http.POST(jsonString);
  http.end();
  
  return (httpCode == 200);
}

void registerDevice() {
  String url = String(API_BASE_URL) + "/api/devices/register";
  
  DynamicJsonDocument doc(512);
  doc["device_id"] = DEVICE_ID;
  doc["device_type"] = DEVICE_TYPE;
  doc["serial_number"] = DEVICE_ID;
  doc["branch_id"] = BRANCH_ID;
  doc["ip_address"] = WiFi.localIP().toString();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  int httpCode = http.POST(jsonString);
  http.end();
  
  Serial.println("Device registration: " + String(httpCode == 200 ? "Success" : "Failed"));
}

void sendHeartbeat() {
  String url = String(API_BASE_URL) + "/api/devices/" + DEVICE_ID + "/heartbeat";
  
  DynamicJsonDocument doc(256);
  doc["status"] = "ONLINE";
  doc["ip_address"] = WiFi.localIP().toString();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  http.POST(jsonString);
  http.end();
}

// ==================== HELPER FUNCTIONS ====================

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.println("IP address: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

String getCardUID() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

void beepSuccess() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);
  delay(100);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);
}

void beepError() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(500);
  digitalWrite(BUZZER_PIN, LOW);
}

void blinkGreen() {
  digitalWrite(LED_GREEN_PIN, HIGH);
  delay(200);
  digitalWrite(LED_GREEN_PIN, LOW);
}

void blinkRed() {
  digitalWrite(LED_RED_PIN, HIGH);
  delay(200);
  digitalWrite(LED_RED_PIN, LOW);
}
