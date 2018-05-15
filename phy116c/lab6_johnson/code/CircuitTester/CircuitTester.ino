// 
//  CircuitTester:  This is a stripped down sketch useful for testing
//     your circuit during construction... it continuously samples
//     the analog input and displays the mean and rms on the serial port.
//

// You should only have to edit these parameters, if at all...

const float CALIB_MV = 4800;   // Calibrated MV scale (nominal 5000 mV)
const int MAX_SCALE    = 220;  // Calibrated full scale: minimal clipping
const int MIN_SCALE    = 40;   // Calibrated min scale: ADC fails below
const int RUN_SCALE    = 40;

//
// You shouldn't have to change anything below here...
//

const int pwm = 5;
const int max_samples = 1500; // the size of the sample buffer
byte buf[max_samples]; // the sample buffer
int isamp = 0;  // the current position in the circular buffer

// the ADC read interrupt:
//  -> simply write every sample to the buffer until full
ISR(ADC_vect){
  if (isamp < max_samples){
    buf[isamp]=ADCH;
    isamp++;      
  }
}    

const int NOMINAL_SCALE = 255;
int current_scale = MAX_SCALE;
void set_voltage_scale(int scale){
  current_scale = scale;      
  analogWrite(pwm, current_scale); 
}

float mv(){
  return CALIB_MV * current_scale / NOMINAL_SCALE / NOMINAL_SCALE;    
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
  analogReference(EXTERNAL);
  set_voltage_scale(RUN_SCALE);
  analogRead(A0);  
  start_adc(0);    
  isamp = 0;
}
  
void loop()
{
   // check if buffer is full:   
  if (isamp == max_samples){
      long sum = 0;
      long sumsq = 0;
      for (int i=0; i<max_samples; i++){
        sumsq += ((long) buf[i])*buf[i];
        sum += buf[i];
      }
      
      double avgsum = ((double) sum) / max_samples;      
      double avgsumsq = sumsq / max_samples;            
      double mvmean = avgsum * mv();                  
      double var = avgsumsq - avgsum*avgsum;
      if (var < 0.0){
        var = 0.0;
      }
      double mvrms = sqrt(var) * mv();

      Serial.println("-------------------");        
      Serial.print("Voltage scale:  ");
      Serial.print(mv()*255);
      Serial.println(" mV");
      Serial.print("mean:  ");
      Serial.print((int) avgsum);
      Serial.println(" counts");         
      Serial.print("var:  ");
      Serial.print((int) var);      
      Serial.println(" counts^2");
      Serial.print("mean:  ");
      Serial.print((long) mvmean);
      Serial.println(" mV");
      if (mvrms >= 100.0){
        Serial.print("rms:  ");
        Serial.print((long) mvrms);
        Serial.println(" mV");
      } else {
        Serial.print("rms:  ");
        Serial.print((long) (mvrms*10));
        Serial.println("/10 mV");        
      }      
      delay(1000);
      isamp = 0;
  }
}

