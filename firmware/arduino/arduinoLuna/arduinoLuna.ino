#include <Servo.h>
#include <math.h>
// Jack Gallagher; Arduino code for UPR 2026 bot
//
// Input is of the form:
// int:int
// ex. 1:50 == function ServoPos Position 50

// input:
//   Bucket linear actuator
//   Camera linear actuator
//   Camera servo
//   Dump Belt Motor
// output:
//   IR sensor data

#define INPUT_SIZE 12

// These are all for the linear actuators
#define MAX_RANGE 100
#define MIN_RANGE 0
#define PWM_FREQUENCY 50
#define MIN_DC 4.7
#define MAX_DC 9.5

// Define pins
#define BUCKET_PIN 10
#define CAM_PIN 9
#define SERVO_PIN 3
#define DUMP_MOTOR 7
#define ENCODE_R_A 4
#define ENCODE_R_B 5
#define ENCODE_L_A 11
#define ENCODE_L_B 12
#define IR_SENSOR_RIGHT A0
#define IR_SENSOR_LEFT A1
#define DEBUG_SERIAL 0

char input[INPUT_SIZE];
Servo cam_servo;
Servo lin_cam_servo;
Servo lin_bucket_servo;

int servo_pos;
int cam_height;
int bucket_height;
long encoder_right_count;
long encoder_left_count;
int8_t last_encoded_right;
int8_t last_encoded_left;

int8_t readEncoderState(uint8_t pin_a, uint8_t pin_b) {
  int8_t a = (int8_t)digitalRead(pin_a);
  int8_t b = (int8_t)digitalRead(pin_b);
  return (int8_t)((a << 1) | b);
}

float irRawToDistanceCm(int raw_value) {
  // Uses the provided GP2Y-like inverse power-law fit:
  // distance_cm ~= 27.728 * voltage^-1.2045
  // where voltage is approximated from the ADC reading.
  float voltage = (float(raw_value) * 5.0f) / 1023.0f;
  if (voltage <= 0.01f) {
    return 999.0f;
  }
  float distance = 27.728f * powf(voltage, -1.2045f);
  if (distance < 0.0f) {
    return 0.0f;
  }
  if (distance > 999.0f) {
    return 999.0f;
  }
  return distance;
}

void updateEncoder(uint8_t pin_a, uint8_t pin_b, int8_t *last_encoded, long *count) {
  int8_t encoded = readEncoderState(pin_a, pin_b);
  int8_t sum = (int8_t)((*last_encoded << 2) | encoded);

  // Valid quadrature transitions only. Any other transition is treated as noise.
  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) {
    (*count)--;
  } else if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) {
    (*count)++;
  }
  *last_encoded = encoded;
}

// Converts 0->100 percent range to servo
// 0 -> 1100; 100 -> 1900
int convertRangeToDutyCycle(int percent) {
  if (percent < MIN_RANGE) {
    percent = MIN_RANGE;
  } else if (percent > MAX_RANGE) {
    percent = MAX_RANGE;
  }

  return 1100 + (8 * percent);
}

// Handles command:value
void dispatchCommand(int command_id, int value) {
  switch (command_id) {
    case SERVO_PIN:
      servo_pos = constrain(value, 0, 180);
      if (DEBUG_SERIAL) {
        Serial.print("servo_pos set to: ");
        Serial.println(servo_pos);
      }
      break;

    case CAM_PIN:
      cam_height = constrain(value, MIN_RANGE, MAX_RANGE);
      if (DEBUG_SERIAL) {
        Serial.print("cam_height set to: ");
        Serial.println(cam_height);
      }
      break;

    case BUCKET_PIN:
      bucket_height = constrain(value, MIN_RANGE, MAX_RANGE);
      if (DEBUG_SERIAL) {
        Serial.print("bucket_height set to: ");
        Serial.println(bucket_height);
      }
      break;

    case DUMP_MOTOR:
      // Match the old conveyor node semantics: 1 = ON (active low), 0 = OFF.
      if (value != 0) {
        digitalWrite(DUMP_MOTOR, LOW);
      } else {
        digitalWrite(DUMP_MOTOR, HIGH);
      }
      if (DEBUG_SERIAL) {
        Serial.print("dump_motor set to: ");
        Serial.println(value != 0 ? 1 : 0);
      }
      break;

    default:
      if (DEBUG_SERIAL) {
        Serial.print("Unknown command: ");
        Serial.println(command_id);
      }
      break;
  }
}

// Extracts command values from input
void parseInput() {
  size_t size = Serial.readBytesUntil('\n', input, INPUT_SIZE - 1);
  input[size] = '\0';

  char *command = strtok(input, ":");
  char *value = strtok(NULL, ":");

  if (command != NULL && value != NULL) {
    int command_id = atoi(command);
    int command_val = atoi(value);
    dispatchCommand(command_id, command_val);
  } else {
    if (DEBUG_SERIAL) {
      Serial.println("Bad input");
    }
  }
}

void setup() {
  servo_pos = 90;
  cam_height = 0;
  bucket_height = 0;
  encoder_right_count = 0;
  encoder_left_count = 0;

  // Set linear actuator pins
  pinMode(BUCKET_PIN, OUTPUT);
  pinMode(CAM_PIN, OUTPUT);

  // Set dump motor pin and turn off
  pinMode(DUMP_MOTOR, OUTPUT);
  digitalWrite(DUMP_MOTOR, HIGH);

  // Encoder pins reserved for later bring-up
  pinMode(ENCODE_R_A, INPUT_PULLUP);
  pinMode(ENCODE_R_B, INPUT_PULLUP);
  pinMode(ENCODE_L_A, INPUT_PULLUP);
  pinMode(ENCODE_L_B, INPUT_PULLUP);
  last_encoded_right = readEncoderState(ENCODE_R_A, ENCODE_R_B);
  last_encoded_left = readEncoderState(ENCODE_L_A, ENCODE_L_B);

  lin_cam_servo.attach(CAM_PIN);
  lin_bucket_servo.attach(BUCKET_PIN);
  cam_servo.attach(SERVO_PIN);
  Serial.begin(115200);
  Serial.setTimeout(5);

  cam_servo.write(servo_pos);
  lin_cam_servo.writeMicroseconds(convertRangeToDutyCycle(cam_height));
  lin_bucket_servo.writeMicroseconds(convertRangeToDutyCycle(bucket_height));
}

void loop() {
  if (Serial.available() > 0) {
    parseInput();
  }

  cam_servo.write(servo_pos);
  lin_cam_servo.writeMicroseconds(convertRangeToDutyCycle(cam_height));
  lin_bucket_servo.writeMicroseconds(convertRangeToDutyCycle(bucket_height));

  updateEncoder(ENCODE_R_A, ENCODE_R_B, &last_encoded_right, &encoder_right_count);
  updateEncoder(ENCODE_L_A, ENCODE_L_B, &last_encoded_left, &encoder_left_count);

  int ir_right_raw = analogRead(IR_SENSOR_RIGHT);
  int ir_left_raw = analogRead(IR_SENSOR_LEFT);
  int ir_right_cm = (int)(irRawToDistanceCm(ir_right_raw) + 0.5f);
  int ir_left_cm = (int)(irRawToDistanceCm(ir_left_raw) + 0.5f);
  Serial.print("#");
  Serial.print(ir_right_cm);
  Serial.print(":");
  Serial.print(ir_left_cm);
  Serial.print(":");
  Serial.print(encoder_left_count);
  Serial.print(":");
  Serial.println(encoder_right_count);

  delay(10);
}
