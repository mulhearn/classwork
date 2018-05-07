// note, A0 is sampled in free running ADC mode, below.
const int adc = 0;

const int plotter_window = 500; // fixed num of lines used by serial plotter
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

void setup()
{
  Serial.begin(115200);
  
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

  isamp = 0;
}
  
void loop()
{
   // check if buffer is full:   
  if (isamp == max_samples){
      for(int i=0;i<plotter_window;i++){
        //The following two lines will add a sample index, for debugging the plotter
        //Serial.print(i);
        //Serial.print(" ");
        if (i < max_samples){
          Serial.println(buf[i]);
        } else {
          Serial.println(0);
        }
      }     
      delay(1500);  // display refresh rate   
      isamp = 0;
  }
}

