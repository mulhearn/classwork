/*
  Serial Data Service Example

  A program to demonstrate serial handshaking in order to transmit data from the Arduino 
  to a PC over the serial connection.

  The Arduino sends a message to the serial link after initialization is
  complete.  It then waits until it receives an acquire command over the serial 
  interface:  
  
     a <nruns> <dt>

  the parameters are:
    integer <nruns> the number of full buffers to send
    integer <dt>  time sampling slow down factor
    the time sampling, 
    (1 is full speed) 
  
  (char 'c' over
  serial link).  Upon receiving this signal, it sends the size of its payload
  (n) followed by n lines containing one x and one y coordinate on each line.

  The corresponding PC driver code (based on PySerial) is in serial_eg.py.
  
  by Michael Mulhearn
 
 */

// the serial driver command interface:
boolean acquire = false;  // was data requested on the serial port?
int nruns = 0; // number of waveforms requested
int dt = 0; // example timing parameter (default 1)

// the sample buffer:
const int max_samples = 10; // the size of the sample buffer
byte buf[max_samples]; // the sample buffer
int isamp = 0;  // the current position in the circular buffer

// serial_output:
int count = 0;  // number of requested samples that have been sent

void fill_buffer_with_test_pattern(){
  float f = 2*PI*dt / (float) max_samples;
  int offset = count*20;
  if (isamp < max_samples){
    buf[isamp] = 124*(1.0+cos(f*(isamp+offset)));
    //buf[isamp] = isamp;
    isamp++;     
  }
}

void write_buffer_to_serial_port(){
    // write header only for the first sample:
    if (count==0){
      Serial.println(max_samples);
      Serial.println(nruns);
    }
    // write payload:
    for(int i=0; i<max_samples; i++){
      char line[100];
      sprintf(line, "%d %d", i*dt, buf[i]);
      Serial.println(line);
      Serial.flush();
    }
}

void setup() {
  // initialize serial:
  Serial.begin(115200);
  Serial.print("Arduino Initialized\n");
}

void loop() {    
  fill_buffer_with_test_pattern();
  
  if (acquire & (isamp == max_samples)) {
    write_buffer_to_serial_port();
    isamp = 0;    
    count++;
  }

  if (count >= nruns){
    acquire = false;
  }
}

// serialEvent is called each time the loop function exits and 
// new serial data is available in the hardware serial receiver.
void serialEvent() {
  delay(1000);
  char inChar = (char) Serial.read();
  if (inChar == 'a'){
      nruns = (int) Serial.parseInt();
      dt = (int) Serial.parseInt();        
      acquire = 1;
      isamp = 0;
  }
  while(Serial.available()){
    char inChar = (char) Serial.read();  
  }
  //Serial.println(param_n);
  //Serial.println(param_t);
}


