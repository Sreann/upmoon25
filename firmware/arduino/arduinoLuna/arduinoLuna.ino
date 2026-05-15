#include <Servo.h>
#include <math.h>
// Jack Gallagher; Arduino code for UPR 2026 bot
//
// Input is of the form:
// int:int
// ex. 1:50 == function ServoPos Position 50
//
// Wheel encoders — electrical / logical interface (quadrature rotary):
//   Each encoder exposes two digital lines, A and B, in quadrature (Gray-coded 2-bit state).
//   Pins use INPUT_PULLUP (idle HIGH); the encoder switches lines LOW per edge/detent.
//
//   ATmega328P (Arduino Uno-class) pin assignment:
//     Right: A -> D4 (PD4), B -> D5 (PD5) — sampled atomically via PIND.
//     Left:  A -> D11 (PB3), B -> D12 (PB4) — sampled atomically via PINB.
//
//   Firmware inputs:  two digital phases per encoder.
//   Firmware outputs: '#' serial telemetry: IR cm, encoder ticks, then pin phases (0–3),
//     decoder phases (0–3), cumulative illegal quadrature transitions per side.

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

/*
 * Encoder quadrature ticks: often ~4 valid edges per mechanical detent. Publishing raw ticks can
 * look uneven (+4/+5 per click, jitter). Set ENCODER_PUBLISH_DIVISOR to 4 for Serial values that
 * track roughly one step per detent; truncation is symmetric so forward/reverse magnitudes match.
 * ROS / arduino_driver receive whatever we print — keep divisor 1 if downstream expects raw ticks.
 */
#ifndef ENCODER_PUBLISH_DIVISOR
#define ENCODER_PUBLISH_DIVISOR 1
#endif

#include "encoder_quadrature.h"

char input[INPUT_SIZE];
Servo cam_servo;
Servo lin_cam_servo;
Servo lin_bucket_servo;

int servo_pos;
int cam_height;
int bucket_height;
bool actuators_armed;
long encoder_right_count;
long encoder_left_count;
int8_t last_encoded_right;
int8_t last_encoded_left;
uint32_t encoder_right_invalid;
uint32_t encoder_left_invalid;

int convertRangeToDutyCycle(int percent);

static void armActuatorsIfNeeded() {
  if (actuators_armed) {
    return;
  }
  actuators_armed = true;

  // Apply known-safe command targets before enabling PWM output pins.
  cam_servo.write(servo_pos);
  lin_cam_servo.writeMicroseconds(convertRangeToDutyCycle(cam_height));
  lin_bucket_servo.writeMicroseconds(convertRangeToDutyCycle(bucket_height));

  cam_servo.attach(SERVO_PIN);
  lin_cam_servo.attach(CAM_PIN);
  lin_bucket_servo.attach(BUCKET_PIN);
}

/*
 * Two back-to-back digitalRead() calls can sample channel A and B at different times. At a
 * quadrature edge that often yields a fake 2-bit pattern (or illegal step), which the decoder
 * may interpret as forward then backward — especially when reversing or with backlash. On
 * ATmega328P, right encoder uses PD4/PD5 and left uses PB3/PB4; read both via one PINx snapshot.
 */
#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
static inline int8_t readEncoderStateRight() {
  uint8_t p = PIND;
  int8_t a = (int8_t)((p >> 4) & 1);
  int8_t b = (int8_t)((p >> 5) & 1);
  return (int8_t)((a << 1) | b);
}

static inline int8_t readEncoderStateLeft() {
  uint8_t p = PINB;
  int8_t a = (int8_t)((p >> 3) & 1);
  int8_t b = (int8_t)((p >> 4) & 1);
  return (int8_t)((a << 1) | b);
}
#else
static int8_t readEncoderStatePair(uint8_t pin_a, uint8_t pin_b) {
  int8_t a = (int8_t)digitalRead(pin_a);
  int8_t b = (int8_t)digitalRead(pin_b);
  return (int8_t)((a << 1) | b);
}
#endif

static void updateEncoderReading(int8_t *last_encoded, long *count, int8_t encoded,
                                 uint32_t *invalid_quadrature_count) {
  int8_t prev = *last_encoded & 3;
  encoded &= 3;
  int8_t delta = encoder_quadrature_step(last_encoded, encoded);
  if (delta != 0) {
    *count += delta;
  } else if (encoded != prev) {
    (*invalid_quadrature_count)++;
  }
}

/** Maps internal tick count to what we publish (symmetric toward zero for negative counts). */
static inline long encoder_publish_value(long raw_ticks) {
#if ENCODER_PUBLISH_DIVISOR <= 1
  return raw_ticks;
#else
  if (raw_ticks >= 0) {
    return raw_ticks / (long)ENCODER_PUBLISH_DIVISOR;
  }
  return -((-raw_ticks) / (long)ENCODER_PUBLISH_DIVISOR);
#endif
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
      armActuatorsIfNeeded();
      if (DEBUG_SERIAL) {
        Serial.print("servo_pos set to: ");
        Serial.println(servo_pos);
      }
      break;

    case CAM_PIN:
      cam_height = constrain(value, MIN_RANGE, MAX_RANGE);
      armActuatorsIfNeeded();
      if (DEBUG_SERIAL) {
        Serial.print("cam_height set to: ");
        Serial.println(cam_height);
      }
      break;

    case BUCKET_PIN:
      bucket_height = constrain(value, MIN_RANGE, MAX_RANGE);
      armActuatorsIfNeeded();
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
  actuators_armed = false;
  encoder_right_count = 0;
  encoder_left_count = 0;
  encoder_right_invalid = 0;
  encoder_left_invalid = 0;

  // Set linear actuator pins
  // Keep servo/actuator control pins high-impedance until we get explicit commands.
  pinMode(BUCKET_PIN, INPUT);
  pinMode(CAM_PIN, INPUT);
  pinMode(SERVO_PIN, INPUT);

  // Set dump motor pin and turn off
  digitalWrite(DUMP_MOTOR, HIGH);
  pinMode(DUMP_MOTOR, OUTPUT);

  // Wheel encoders: quadrature on digital pins with internal pull-ups
  pinMode(ENCODE_R_A, INPUT_PULLUP);
  pinMode(ENCODE_R_B, INPUT_PULLUP);
  pinMode(ENCODE_L_A, INPUT_PULLUP);
  pinMode(ENCODE_L_B, INPUT_PULLUP);
#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
  last_encoded_right = readEncoderStateRight() & 3;
  last_encoded_left = readEncoderStateLeft() & 3;
#else
  last_encoded_right = readEncoderStatePair(ENCODE_R_A, ENCODE_R_B) & 3;
  last_encoded_left = readEncoderStatePair(ENCODE_L_A, ENCODE_L_B) & 3;
#endif

  Serial.begin(115200);
  Serial.setTimeout(5);
}

void loop() {
  if (Serial.available() > 0) {
    parseInput();
  }

  if (actuators_armed) {
    cam_servo.write(servo_pos);
    lin_cam_servo.writeMicroseconds(convertRangeToDutyCycle(cam_height));
    lin_bucket_servo.writeMicroseconds(convertRangeToDutyCycle(bucket_height));
  }

  int8_t pin_phase_right;
  int8_t pin_phase_left;
#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
  pin_phase_right = readEncoderStateRight() & 3;
  pin_phase_left = readEncoderStateLeft() & 3;
  updateEncoderReading(&last_encoded_right, &encoder_right_count, pin_phase_right,
                       &encoder_right_invalid);
  updateEncoderReading(&last_encoded_left, &encoder_left_count, pin_phase_left,
                       &encoder_left_invalid);
#else
  pin_phase_right = readEncoderStatePair(ENCODE_R_A, ENCODE_R_B) & 3;
  pin_phase_left = readEncoderStatePair(ENCODE_L_A, ENCODE_L_B) & 3;
  updateEncoderReading(&last_encoded_right, &encoder_right_count, pin_phase_right,
                       &encoder_right_invalid);
  updateEncoderReading(&last_encoded_left, &encoder_left_count, pin_phase_left,
                       &encoder_left_invalid);
#endif

  int ir_right_raw = analogRead(IR_SENSOR_RIGHT);
  int ir_left_raw = analogRead(IR_SENSOR_LEFT);
  int ir_right_cm = (int)(irRawToDistanceCm(ir_right_raw) + 0.5f);
  int ir_left_cm = (int)(irRawToDistanceCm(ir_left_raw) + 0.5f);
  Serial.print("#");
  Serial.print(ir_right_cm);
  Serial.print(":");
  Serial.print(ir_left_cm);
  Serial.print(":");
  Serial.print(encoder_publish_value(encoder_left_count));
  Serial.print(":");
  Serial.print(encoder_publish_value(encoder_right_count));
  Serial.print(":");
  Serial.print((int)pin_phase_right);
  Serial.print(":");
  Serial.print((int)pin_phase_left);
  Serial.print(":");
  Serial.print((int)(last_encoded_right & 3));
  Serial.print(":");
  Serial.print((int)(last_encoded_left & 3));
  Serial.print(":");
  Serial.print(encoder_right_invalid);
  Serial.print(":");
  Serial.println(encoder_left_invalid);

  delay(10);
}
