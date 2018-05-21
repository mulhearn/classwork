//
// Fast ADC with PWM controlled ADC dynamic range adjustment.
//

// You should only have to edit these parameters, if at all...

const int MAX_SCALE    = 220;  // Calibrated full scale: minimal clipping
const int MIN_SCALE    = 40;   // Calibrated min scale: ADC fails below
const int RUN_SCALE    = 80;   // User selected value for PWM 
const bool TEST_PATTERN = false; // Send test pattern instead of ADC data
//
// You shouldn't have to change anything below here...
//


// the serial driver command interface:
boolean acquire = false;  // was data requested on the serial port?
int nruns = 0; // number of waveforms requested
int dt = 0; // example timing parameter (default 1)

// the sample buffer:
const int max_samples = 1538; // the size of the sample buffer
                              // 1538 => f0 = 50 Hz
byte buf[max_samples]; // the sample buffer
int sum = 0; // sum, for digital low-pass filter
int isum = 0;
int isamp = 0;  // the current position in the circular buffer

// PWM pin for programmable reference voltage
const int pwm = 5;


// the ADC read interrupt:
//  -> simply write every sample to the buffer until full
ISR(ADC_vect){
  if (isamp >= max_samples) return;
  
  switch(dt){
    case 1:
        buf[isamp]=ADCH;
        isamp++;
        return;
    case 2:
      sum += ADCH;
      isum++;
      if (isum == dt){
        buf[isamp]=(byte) (sum>>1);
        isamp++;
        isum=0;
        sum = 0; 
      }     
      return;
    default:
      sum += ADCH;
      isum++;
      if (isum == dt){
        buf[isamp]=(byte) (sum/dt);
        isamp++;
        isum=0;
        sum = 0; 
      }
      return;         
  }
}
  
const int NOMINAL_SCALE = 255;
int current_scale = MAX_SCALE;
void set_voltage_scale(int scale){
  current_scale = scale;      
  analogWrite(pwm, current_scale); 
}


void start_adc(int adc){    
  ADCSRA = 0;             // clear ADCSRA register
  ADCSRB = 0;             // clear ADCSRB register
  ADMUX = 0;
  ADMUX |= (adc & 0x07);    // set A(adc) analog input pin
  ADMUX |= (0 << REFS0);  // set reference voltage
  ADMUX |= (1 << ADLAR);  // left align ADC value to 8 bits from ADCH register
  // sampling rate is [ADC clock] / [prescaler] / [conversion clock cycles]
  // for Arduino Uno ADC clock is 16 MHz and a conversion takes 13 clock cycles
  ADCSRA |= (1 << ADPS2);                     // 16 prescaler for 76.9 KHz
  ADCSRA |= (1 << ADATE); // enable auto trigger
  ADCSRA |= (1 << ADIE);  // enable interrupts when measurement complete
  ADCSRA |= (1 << ADEN);  // enable ADC
  ADCSRA |= (1 << ADSC);  // start ADC measurements
}



void setup()
{
  Serial.begin(115200);
  Serial.print("Arduino Initialized\n");
   
  if (!TEST_PATTERN){
    analogReference(EXTERNAL);
    set_voltage_scale(RUN_SCALE);
    analogRead(A0);  
    start_adc(0);
  }    
  isum = 0;
  sum = 0;
  isamp = 0;
}
  


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
      Serial.println(RUN_SCALE);
    }
    // write payload:
    for(int i=0; i<max_samples; i++){
      char line[100];
      sprintf(line, "%d %d", i, buf[i]);
      Serial.println(line);
      Serial.flush();
    }
}

void loop() {    
  if (TEST_PATTERN){
    fill_buffer_with_test_pattern();
  }
  
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
  char inChar = (char) Serial.read();
  if (inChar == 'a'){
      nruns = (int) Serial.parseInt();
      dt = (int) Serial.parseInt();        
      isamp = 0;
      sum = 0;
      isum = 0;
      acquire = true;
  }
  while(Serial.available()){
    char inChar = (char) Serial.read();  
  }
  //Serial.println(param_n);
  //Serial.println(param_t);
}

