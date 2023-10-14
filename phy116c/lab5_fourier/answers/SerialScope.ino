// Instructor solution

// note, A0 is sampled in free running ADC mode, below.
const int adc = 0;


// the serial driver command interface:
boolean acquire = false;  // was data requested from the serial port?

// the sample buffer:
const int max_samples = 1500; // the size of the sample buffer
byte buf[max_samples]; // the sample buffer
int isamp = 0;  // the current position in the buffer

// this example uses test pattern data, calculated from sine wave:
void fill_buffer_with_test_pattern(){
  float f = 4 * PI / (float) max_samples;
  while(isamp < max_samples){
    buf[isamp] = 124*(1.0+cos(f*isamp));
    isamp++;     
  }
}

// the ADC read interrupt:
//  -> simply write every sample to the buffer until full
ISR(ADC_vect){
  if (isamp < max_samples){
    buf[isamp]=ADCH;
    isamp++;      
  }
}    


// write the contents of a full buffer on the serial port:
void write_buffer_to_serial_port(){
    // write header only for the first sample:
    Serial.println(max_samples);
    // write payload:
    for(int i=0; i<max_samples; i++){
      char line[100];
      sprintf(line, "%d %d", i, buf[i]);
      Serial.println(line);
      Serial.flush();
    }
}

// Setup the serial port and send the initialized message:
void setup() {

  // Low-level driver commands which set the ADC to free-running mode:  
  ADCSRA = 0;             // clear ADCSRA register
  ADCSRB = 0;             // clear ADCSRB register
  ADMUX |= (adc & 0x07);    // set A(adc) analog input pin
  ADMUX |= (1 << REFS0);  // set reference voltage
  ADMUX |= (1 << ADLAR);  // left align ADC value to 8 bits from ADCH register
  // sampling rate is [ADC clock] / [prescaler] / [conversion clock cycles]
  // for Arduino Uno ADC clock is 16 MHz and a conversion takes 13 clock cycles
  ADCSRA |= (1 << ADPS2);                     // 16 prescaler for 76.9 KHz
  ADCSRA |= (1 << ADATE); // enable auto trigger
  ADCSRA |= (1 << ADIE);  // enable interrupts when measurement complete
  ADCSRA |= (1 << ADEN);  // enable ADC
  ADCSRA |= (1 << ADSC);  // start ADC measurements

  // set the buffer to empty:
  //isamp = 0;
  
  // initialize serial:
  Serial.begin(115200);
  Serial.print("Arduino Initialized\n");
}


void loop() {    
  // fill buffer with test pattern data if it is empty:
  //fill_buffer_with_test_pattern();

  // if an acquire signal has been received, and the buffer is full, write the contents:
  if (acquire & (isamp == max_samples)) {
    write_buffer_to_serial_port();
    acquire = false;
  }
}

// serialEvent is called each time the loop function exits and 
// new serial data is available in the hardware serial receiver.
// If a character "a" has been sent, the buffer is reset and the 
// the acquire flag is set to false.
void serialEvent() {
  delay(1000);
  char inChar = (char) Serial.read();
  if (inChar == 'a'){
      isamp = 0;
      acquire = true;
  }
}
