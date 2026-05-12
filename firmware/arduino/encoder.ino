#include <Servo.h>
// Jack Gallagher; Arduino code for UPR 2026 bot
//
// Input is of the form:
// int:int
// ex. 1:50 == function ServoPos Position 50

//input: 
//	Bucket Lin. Actuators
//	Camera Lin. Actuator
//	Camera Servo
//	Dump Belt Motor
//output:
//	IR sensor data
//	Hall-Effect Sensor data
//	Rotary Encoder data

#define INPUT_SIZE 12 //Max input size

//These are all for the linear actuators
#define MAX_RANGE 100
#define MIN_RANGE 0
#define PWM_FREQUENCY 50
#define MIN_DC 4.7
#define MAX_DC 9.5

//Define pins
#define BUCKET_PIN 10
#define CAM_PIN 9
#define SERVO_PIN 3
#define DUMP_MOTOR 7
#define ENCODE_R_A 4
#define ENCODE_R_B 5
#define ENCODE_L_A 11
#define ENCODE_L_B 12
#define IR_SENSOR A0 
#define IR_SENSOR A1

int input[INPUT_SIZE];
Servo cam_servo;
Servo lin_cam_servo;
Servo lin_bucket_servo; 

int servo_pos;
int cam_height;
int bucket_height;

//Right Encoder
volatile long encoderCountRight = 0; //Total encoder tick count
volatile int lastEncodedRight = 0; //Stores the previous AB state

//Left Encoder
volatile long encoderCountLeft = 0; //Total encoder tick count
volatile int lastEncodedLeft = 0; //Stores the previous AB state

const int countsPerRevolution = 2400;

void setup() {
	servo_pos = 0;
	cam_height = 0;
	bucket_height = 0;
	
	//set lin actuator pins
	pinMode(BUCKET_PIN, OUTPUT);
	pinMode(CAM_PIN,OUTPUT);

	//set dump motor pin and turn off
	pinMode(DUMP_MOTOR,OUTPUT);
	digitalWrite(DUMP_MOTOR, HIGH);

	//Rotary Encoders; config encoer channels as inputs with internal pull-up resistors
	pinMode(ENCODE_R_A, INPUT_PULLUP); //Right channel A
	pinMode(ENCODE_R_B, INPUT_PULLUP); //Right channel B
	attachInterrupt(digitalPinToInterrupt(2), updateEncoder, CHANGE); 	
	attachInterrupt(digitalPinToInterrupt(2), updateEncoder, CHANGE);
	//IR Sensor

	//INA226 Voltage Current Sensor Reader

	lin_cam_servo.attach(CAM_PIN);
	lin_bucket_servo.attach(BUCKET_PIN);
	cam_servo.attach(SERVO_PIN); 
	Serial.begin(115200);

}

//Converts 0->100 percent range to servo
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
      servo_pos = value;
      Serial.print("servo_pos set to: ");
      Serial.println(servo_pos);
      break;

    case CAM_PIN:
      cam_height = value;
      Serial.print("cam_height set to: ");
      Serial.println(cam_height);
      break;

    case BUCKET_PIN:
      bucket_height = value;
      Serial.print("bucket_height set to: ");
      Serial.println(bucket_height);
      break;

    case DUMP_MOTOR:
      if (value == 0) {
        digitalWrite(DUMP_MOTOR, LOW);
      } else {
        digitalWrite(DUMP_MOTOR, HIGH);
      }
      Serial.print("pin7 set to: ");
      Serial.println(value);
      break;

    default:
      Serial.print("Unknown command: ");
      Serial.println(command_id);
      break;
  }
}
//Extracts command values from input
void parseInput() {
	byte size = Serial.readBytes(input, INPUT_SIZE-1);
	input[size] = 0;
	char* command = strtok(input, ":");
	char* value = strtok(0, ":");
	
	if(command != 0 && value != 0) {
		int command_id = atoi(command);
		int command_val = atoi(value);
		dispatchCommand(command_id, command_val);
	} else {
		Serail.println("Bad input"); 
	}
}


//Called whenever Channel A or B changes state Encoders Left + right
void updateEncoder(int ChA, int ChB) {
	// Read the current state of encoder channels
	int MSB = digitalRead(ChA); //Channel A
	int LSB = digitalRead(ChB); //Channel B

	//Combine the two singals into a 2-bit number
	int encoded = (MSB << 1) | LSB; 

	//Create a 4-bit transition value from previous + current state
	if(ChA == 4) { //Right Encoder
		int sum = (lastEncodedRight << 2) | encoded; 
		//Determine the direction based on value quarature transistions 
		//These patterns correspond to clockwise roatation
		if (sum == 0b1101 || sum == 0b011 || sum == 0b0010 || sum == 0b1011) {
			encoderCountRight--;
		}
		//These patterns correspond to counter-clockwise rotation
		if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) {
			encoderCountRight++;
		}
		//Store current state for the next interrupt 
		lastEncodedRight = encoded; 
	} else { //Left Encoder
		int sum = (lastEncodedLeft << 2) | encoded;
		if (sum == 0b1101 || sum == 0b011 || sum == 0b0010 || sum == 0b1011) {
			encoderCountLeft--;
		}
		if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) {
			encoderCountLeft++; 
		}
		lastEncodedLeft = encodedLeft; 
	}
}


void loop() { 
	if (Serial.available() > 0) {
		parseInput();
	}
	cam_servo.write(servo_pos);
	lin_cam_servo.writeMicroseconds(convertRangeToDutyCycle(cam_height));
	lin_bucket_servo.writeMicroseconds(convertRangeToDutyCycle(bucket_height)); 
}
	
