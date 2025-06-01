/**************************************************************************
screen control 
based on the adafruit ssd1306 example

serial communication based on 
https://forum.arduino.cc/t/serial-input-basics-updated/382007/2

 **************************************************************************/

#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels

#define SDA_PIN 8 // define sda pin 
#define SCL_PIN 9 // define scl pin 

#define E1A 4
#define E1B 5
#define E2A 6
#define E2B 7

#define AIN1 14
#define AIN2 13
#define BIN1 12
#define BIN2 11

#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32 my screen is 0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

char receivedChar;
boolean newData = false;

String str_f = "move forward";
String str_b = "move back";
String str_l = "turn left";
String str_r = "trun right";
String str_s = "stop";


void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN,SCL_PIN); 

  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);


  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }

  // Clear the buffer
  display.clearDisplay();

}

void loop() {

  if (Serial.available() > 0) {
    recvOneChar();
    showNewData();
  }                     

}

void drawmessage(const String message) {
  display.clearDisplay();

  display.setTextSize(1);      // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setCursor(0, 0);     // Start at top-left corner
  display.println(message);
  
  display.display();
  //delay(2000);
}

void recvOneChar() {
  if (Serial.available() > 0) {
    receivedChar = Serial.read();
    if (receivedChar != '\n') {
      newData = true;
    }
  }
}

void showNewData() {
  if (newData == true) {
    Serial.print("this is ...");
    Serial.println(receivedChar);
    newData = false;
    motorcontrol();
  }
}

void motorcontrol() {
  switch (receivedChar) {
    case 'f': {
      drawmessage(str_f);
      moveForward(30);
    }
      break;
    case 'b': {
      drawmessage(str_b);
      moveReverse(30);
    }
      break;
    case 'l': {
      drawmessage(str_l);
      leftRotate(15);
    }
      break;
    case 'r': {
      drawmessage(str_r);
      rightRotate(15);
    }
      break;
    default: 
      drawmessage(str_s);
      movestop();
      break;
  }
}



void moveForward(int pwm) {
  analogWrite(AIN2, 255);
  analogWrite(AIN1, 255-pwm);
  analogWrite(BIN1, 255);
  analogWrite(BIN2, 255-pwm);
}


void moveReverse(int pwm) {
  analogWrite(AIN1, 255);
  analogWrite(AIN2, 255-pwm);
  analogWrite(BIN2, 255);
  analogWrite(BIN1, 255-pwm);
}


void leftRotate(int pwm) {
  analogWrite(AIN2, 255);
  analogWrite(AIN1, 255-pwm);
  analogWrite(BIN2, 255);
  analogWrite(BIN1, 255-pwm);
}


void rightRotate(int pwm) {
  analogWrite(AIN1, 255);
  analogWrite(AIN2, 255-pwm);
  analogWrite(BIN1, 255);
  analogWrite(BIN2, 255-pwm);
}

void movestop() {
  analogWrite(AIN2, 0);
  analogWrite(AIN1, 0);
  analogWrite(BIN1, 0);
  analogWrite(BIN2, 0);
}

