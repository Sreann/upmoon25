#include <Servo.h>

/*
 * Arduino Firmware for upmoon25-auto
 * 
 * Protocol:
 * Incoming (Serial): "PAN:HGT:BKT\n"
 *   - PAN: 000-180 (Camera Pan)
 *   - HGT: 000-100 (Camera Height Actuator)
 *   - BKT: 000-100 (Bucket Extension Actuator)
 * 
 * Outgoing (Serial): "#IR_R:IR_L\n"
 *   - Raw analog values from IR sensors
 */

Servo panServo;
Servo heightServo;
Servo bucketServo;

// Pin definitions aligned with the older arduinoLuna firmware:
// - SERVO_PIN  -> camera pan
// - CAM_PIN    -> camera height linear actuator
// - BUCKET_PIN -> bucket linear actuator
const int PIN_PAN    = 3;
const int PIN_HEIGHT = 9; 
const int PIN_BUCKET = 10;
const int PIN_IR_R   = A0;
const int PIN_IR_L   = A1;

const int MIN_RANGE = 0;
const int MAX_RANGE = 100;
const int MIN_US = 1100;
const int MAX_US = 1900;

int percentToMicros(int percent) {
  int clamped = constrain(percent, MIN_RANGE, MAX_RANGE);
  return map(clamped, MIN_RANGE, MAX_RANGE, MIN_US, MAX_US);
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);
  
  panServo.attach(PIN_PAN);
  heightServo.attach(PIN_HEIGHT);
  bucketServo.attach(PIN_BUCKET);
  
  // Initial positions
  panServo.write(90);
  heightServo.writeMicroseconds(percentToMicros(0));
  bucketServo.writeMicroseconds(percentToMicros(0));
}

void loop() {
  // 1. Read Commands from ROS 2
  if (Serial.available() > 0) { // Expecting "000:000:000\n"
    String data = Serial.readStringUntil('\n');
    data.trim();
    if (data.length() == 11 && data.charAt(3) == ':' && data.charAt(7) == ':') {
      int pan = data.substring(0, 3).toInt();
      int hgt = data.substring(4, 7).toInt();
      int bkt = data.substring(8, 11).toInt();
      
      panServo.write(constrain(pan, 0, 180));

      // The linear actuators expect calibrated servo pulse widths,
      // not simple 0-180 hobby-servo angle commands.
      heightServo.writeMicroseconds(percentToMicros(hgt));
      bucketServo.writeMicroseconds(percentToMicros(bkt));
    }
  }

  // 2. Send Sensor Data to ROS 2
  int irR = analogRead(PIN_IR_R);
  int irL = analogRead(PIN_IR_L);
  
  Serial.print("#");
  Serial.print(irR);
  Serial.print(":");
  Serial.println(irL);
  
  delay(10); // ~100Hz update rate
}
