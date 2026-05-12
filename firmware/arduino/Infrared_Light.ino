const int sensorPin = A0; 
 
void setup() { 
 Serial.begin(9600); 
} 
 
void loop() { 
 int rawValue = analogRead(sensorPin); 
  
 // Convert analog value to distance (approximate formula) 
 float distance = 27.728 * pow(map(rawValue, 0, 1023, 0, 5000) / 1000.0, -1.2045); 
  
 Serial.print("Distance: "); 
 Serial.print(distance); 
 Serial.println(" cm"); 
  
 delay(100); // Small delay for stability 
} 