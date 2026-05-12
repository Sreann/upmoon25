#include <Servo.h>
// Expected max input size
// Input is of the form:
// <servo pos>:<cam height>:<bucket height> 
#define INPUT_SIZE 12

// These are all for the linear actuators
#define MAX_RANGE 100
#define MIN_RANGE 0
#define PWM_FREQUENCY 50
#define MIN_DC 4.7
#define MAX_DC 9.5

#define BUCKET_PIN 10
#define CAM_PIN 9
#define SERVO_PIN 3

char input[INPUT_SIZE + 1];
Servo cam_servo;
Servo lin_cam_servo;
Servo lin_bucket_servo;


int servo_pos;
int cam_height;
int bucket_height;

void setup() {
  servo_pos = 0;
  cam_height = 0;
  bucket_height = 0;

  pinMode(BUCKET_PIN, OUTPUT);
  pinMode(CAM_PIN, OUTPUT);

  lin_cam_servo.attach(CAM_PIN);
  lin_bucket_servo.attach(BUCKET_PIN);
  cam_servo.attach(SERVO_PIN);
  Serial.begin(115200);
}

int convertRangeToDutyCycle(int percent) {
  if (percent < MIN_RANGE) {
    percent = MIN_RANGE;
  } else if (percent > MAX_RANGE) {
    percent = MAX_RANGE;
  }

  return 1100 + (8 * percent);
}

// Extracts command values from input string
void parseInput() {
    byte size = Serial.readBytes(input, INPUT_SIZE);
    input[size] = 0;

    int command_pos = 0;
    char* command = strtok(input, ":");
    while (command != 0) {
      if (command_pos == 0) {
        servo_pos = atoi(command);
      }
      else if (command_pos == 1) {
        cam_height = atoi(command);
      }
      else if (command_pos == 2) {
        bucket_height = atoi(command);
      }
      command_pos++;
      command = strtok(0, ":");
    }
    Serial.print("pan: ");
    Serial.print(servo_pos);
    Serial.print(" cam: ");
    Serial.print(cam_height);
    Serial.print(" bucket: ");
    Serial.println(bucket_height);
}

void loop() {
  
  if (Serial.available() > 0) {
    parseInput();
  }

  cam_servo.write(servo_pos);  

  lin_cam_servo.writeMicroseconds(convertRangeToDutyCycle(cam_height));

  lin_bucket_servo.writeMicroseconds(convertRangeToDutyCycle(bucket_height));

  
  delay(15);
}
