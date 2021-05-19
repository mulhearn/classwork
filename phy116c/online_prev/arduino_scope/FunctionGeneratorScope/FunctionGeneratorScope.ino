/*
  FunctionGeneratorScope

  FunctionGenerator and Digital Oscilloscope
*/

// -------------------------------
// Fast Sine Function:
//--------------------------------


// Evaluating the sin function is expensive, so we'll
// calcuate it once and save the values in a look-up-table:

const int MAX_LUT=50;
float sin_lut[MAX_LUT];

void fill_sin_lut(){ 
  for (int i=0;i<MAX_LUT;i++){
    sin_lut[i] = 0.5*sin(M_PI*i/(2*MAX_LUT));     
  }
}

unsigned fast_sin(unsigned period, unsigned amp, unsigned index){  
  index = index%period;
  unsigned i = 4 * MAX_LUT * (index%period) / period;  
  unsigned quad = (i / MAX_LUT) % 4;
  switch(quad){
    case 0:
      return 127+amp*sin_lut[i%MAX_LUT];
    case 1:
      return 127+amp*sin_lut[MAX_LUT-1-(i%MAX_LUT)];
    case 2:
      return 127-amp*sin_lut[i%MAX_LUT];
    case 3:
      return 127-amp*sin_lut[MAX_LUT-1-(i%MAX_LUT)];      
  }
  return 0;  
}

// -------------------------------
// Digital Oscillocope:
//--------------------------------

// We use the Arduino's build in serial plotter for displaying the waveforms:
const int plotter_window = 500; // fixed num of lines used by serial plotter
//const int plotter_window = 10;

// the circular buffer used to collect digital scope data:
const int max_samples = 500;  // the size of the sample buffer 
uint16_t buf[max_samples]; // the sample buffer
int offset = 250;       //
int isamp = 0;          // the current position in the circular buffer


void serial_readout(){  
  //noInterrupts();
    for(int i=0; i<plotter_window; i++){
      //The following two lines will add a sample index, for debugging the plotter
      int index = (isamp + i)%max_samples;
      //Serial.print((int) (buf[index]*1.96));
      Serial.print((int) (buf[index]));      
      //The following two lines will debug the sin LUT:
      //Serial.print(" ");
      //Serial.print(fast_sin(500,255,i));
      //The following two lines will add a sample index, for debugging the plotter
      //Serial.print(" ");
      //Serial.print(i);
      // Poor man's tick marks:
      //Serial.print(" ");
      //if (i == 100)      Serial.print(500);
      //else if (i == 119)  Serial.print(10);
      //else if (i == 138)  Serial.print(10);
      //else               Serial.print(0);
      //End line:
      Serial.println("");
   }
  //interrupts();
}

// State Machine for Digital Scope:
// READY: start of waveform acquisition... buffer has not collected enough 
//    samples to cover the trigger offset, so triggers are ignored.
// ARMED: enough samples have been collected to cover the trigger offset,
//    but trigger condition has not yet been met
// TRIGGERED:  trigger condition has been met, collecting samples to complete
//    the waveform
// FULL:  the complete waveform is available for read out
//
enum {READY, ARMED, TRIGGERED, FULL};
int scope_state = READY;
int state_count = 0;    // samples collected in the present state

// The digital scope input:
const int scope_pin = A5;
const int scope_adc = 5;

// The ADC interrupt also updates the parameter:
unsigned param = 0;
const int param_adc = 1; 

// the ADC read interrupt service routine:
//  -> simply write every sample to the buffer until full
ISR(ADC_vect){  
  if ((ADMUX & 0x7) == scope_adc){
    int scope_sample = ADCH;
    buf[isamp]= scope_sample;        
    isamp=(isamp+1)%max_samples;
    state_count++;  
    if (state_count==500){
      scope_state=FULL;
    }
    ADMUX &= ~(0x07);
    ADMUX |= (param_adc & 0x07);  
    ADCSRA |= (1 << ADSC);
  } else {
    param = ADCH;
    ADMUX &= ~(0x07);
    ADMUX |= (scope_adc & 0x07);
  }
}    

void sample_scope(){
  if (scope_state==FULL){
    return;
  }
  ADCSRA |= (1 << ADSC);
}

void setup_scope(){
// setup the ADC in free running mode:    
  ADCSRA = 0;             // clear ADCSRA register
  ADCSRB = 0;             // clear ADCSRB register
  ADMUX |= (scope_adc & 0x07);  // set A(adc) analog input pin
  ADMUX |= (1 << REFS0);  // set reference voltage
  ADMUX |= (1 << ADLAR);  // left align ADC value to 8 bits from ADCH register
  // sampling rate is [ADC clock] / [prescaler] / [conversion clock cycles]
  // for Arduino Uno ADC clock is 16 MHz and a conversion takes 13 clock cycles
  //ADCSRA |= (0b001 << ADPS0);                 // 2 prescaler for 76.9 KHz * 8
  //ADCSRA |= (0b010 << ADPS0);                 // 4 prescaler for 76.9 KHz * 4
  //ADCSRA |= (0b011 << ADPS0);                 // 8 prescaler for 76.9 KHz * 2
  ADCSRA |= (0b100 << ADPS0);                 // 16 prescaler for 76.9 KHz (fastest reliable)
  //ADCSRA |= (0b101 << ADPS0);                 // 32 prescaler for 76.9 KHz/2
  //ADCSRA |= (0b110 << ADPS0);                 // 64 prescaler for 76.9 KHz/4
  //ADCSRA |= (0b111 << ADPS0);                   // 128 prescaler for 76.9 KHz/8
  //ADCSRA |= (1 << ADATE); // enable auto trigger
  ADCSRA |= (1 << ADIE);  // enable interrupts when measurement complete
  ADCSRA |= (1 << ADEN);  // enable ADC
  //ADCSRA |= (1 << ADSC);  // start ADC measurements
}

// -------------------------------
// Function Generator:
//--------------------------------

// the function generator output modes (square=0, saw=1, sine=2):
int modes = 3;
int output_mode=0;

// We'll set the amplitude as digital value from 0-255 here:
unsigned waveform_amplitude = 255;
// We'll set the frequency in Hz here:
double waveform_frequency = 100;
// We'll keep track of the waveform update rate here (Hz):
double waveform_update_frequency;

// the functions are generally produced by PWM output, which must be RC
// filtered to obtain smooth functions.  However some functions include sharp
// edges.  For this reason, the function generator output is driven at two 
// places in an RC filter:
// 
//  (filtered) -> R -> (unfiltered)-> (output) -> C -> Ground
//
// To see the filtered content, the unfiltered output must be high-impedance.
//
// This allows us to have smooth PWM output *AND* sharp transitions. Who
// says you can't have your cake and eat it too?
//
// step function at one-half sample rate (for debugging):
const int sample_rate_pin   = 7;

// the RC filtered output pin:  (smooth, PWM functions)
const int filtered_pin   = 5;
// the non-RC filtered output pin: (sharp edges)
const int unfiltered_pin = 8;

void setup_function_generator(){
  fill_sin_lut();
  pinMode(sample_rate_pin, OUTPUT);  
  setup_for_output_mode();
}

// We use filtered or non-filtered pin depending on the output mode.
// Note: Saw-tooth uses non-filtered pin at the sharp edage.
void setup_for_output_mode(){
  if (output_mode == 0){
    pinMode(unfiltered_pin, OUTPUT);
    pinMode(filtered_pin, INPUT);    
  } else {
    pinMode(unfiltered_pin, INPUT);
    pinMode(filtered_pin, OUTPUT);         
  }
}

// waveform update interrupt:
unsigned long waveform_count = 0;

void waveform_update(){
  waveform_count++;
  // debugging square wave at 1/2 the update frequency:
  digitalWrite(sample_rate_pin,waveform_count%2);

  // calculate the period (in number of updates) common to all
  // the output modes:
  unsigned period = waveform_update_frequency/waveform_frequency;

  if (output_mode == 0){ // square wave
    if (waveform_count%period > period/2){
      digitalWrite(unfiltered_pin, HIGH);      
    } else {
      digitalWrite(unfiltered_pin, LOW);            
    }    
  } else if (output_mode == 1){  // saw tooth function
    OCR0B = (waveform_count*(waveform_amplitude+1)/period)%(waveform_amplitude+1);
    // drive the sharp edge by enabling unfiltered output:
    if (waveform_count%period == 0){
      // pull output hard low:
      pinMode(unfiltered_pin, OUTPUT);
      digitalWrite(unfiltered_pin,0);
    }
    if (waveform_count%period == 2){
      pinMode(unfiltered_pin, INPUT);      
    }    
  } else if (output_mode == 2){  // sine function
    OCR0B = fast_sin(period, waveform_amplitude, waveform_count); 
  }    
}


// -------------------------------
// Timers:
//--------------------------------

// Arduino Timers:
// The PWM pins are controlled by three timers T0,T1, and T2.
// Each timer has two associated PWM channels A and B.
// These definitions show how timer channels map to Arduino pins:
#define OC0A_PIN 6
#define OC0B_PIN 5
#define OC1A_PIN 9
#define OC1B_PIN 10
#define OC2A_PIN 11
#define OC2B_PIN 3

// The timers are configured by setting hardware registers.
// To get the fasted possible PWM out of the Arduino, we will 
// use T0 with a prescale (clock divider or 1).  The speeds up 
// the T0 clock by a factor of 64.  These definitions don't set 
// any registers, the HW registers are set to these values in the setup:

//TIMER 0 SETTINGS:  (PWM pins 5 and 6)
// T0 Fast PWM, Non-Inverting for A and B @ WGM00 on TCCR0A
#define TCCR0A_FAST_PWM_MODE       (0b10100011 << WGM00)
#define TCCR0B_CLOCK_PRESCALE_1    (0b001 << CS00)
#define TCCR0B_CLOCK_PRESCALE_8    (0b010 << CS00)
#define TCCR0B_CLOCK_PRESCALE_64   (0b011 << CS00)

// We won't use PWM on pins 9 and 10, and will instead use Timer 1 to
// give us regular interrupts.  This will let us make nice sharp jitter
// free waveforms for the function generator and ADC readout at well 
// defined times for the digital scope.  We set Timer1 to Clear Timer 
// on Compare Match (CTC) mode.  This lets us dial in the exact rate 
// we want interrupts to occur at.

//TIMER 1 SETTINGS:  (PWM pins 9 and 10... unused)
#define TCCR1A_CTC_MODE        0
#define TCCR1B_CTC_MODE        (0b01 << WGM12)
#define TCCR1B_CLOCK_PRESCALE_1    (0b001 << CS10)
#define TCCR1B_CLOCK_PRESCALE_8    (0b010 << CS10)
#define TCCR1B_CLOCK_PRESCALE_64   (0b011 << CS10)

// Specific 

const int button_pin  = 2; 
const int analed_pin  =  11;
const int bltled_pin = 13;   

// We'll be speeding up the timer T0 which also controls,
// millis() and micros()... We'll keep track of the speedup
// here so we can correct for it if needed:
unsigned speedup = 1;

// We'll keep track of the scope readout rate here (Hz):
double scope_update_frequency;


int last_button = HIGH;

// waveform update interrupt:
ISR(TIMER1_COMPA_vect){
  sample_scope();
  waveform_update();
}

unsigned long last_readout = 0;
unsigned long last_update  = 0;

void setup() {
  // the pushbutton is installed at button_pin.
  // it pulls to ground when pressed, so enable
  // the built-in pullup resistor so that this 
  // pin is high when button is not being pressed. 
  pinMode(button_pin, INPUT_PULLUP);
  
  // initialize the LED pins and blink a few times
  // at startup:
  pinMode(analed_pin, OUTPUT);
  pinMode(bltled_pin, OUTPUT);
  for (int i = 0; i<5; i++){
    digitalWrite(analed_pin, HIGH);
    digitalWrite(bltled_pin, HIGH);
    delay(100);
    digitalWrite(analed_pin, LOW);
    digitalWrite(bltled_pin, LOW);
    delay(100);
  }

  // The potentiometer is installed at A0-A1-A2.
  // Set A0 to VCC and A2 to ground
  pinMode(A0, OUTPUT);
  pinMode(A2, OUTPUT);
  digitalWrite(A0, HIGH);
  digitalWrite(A2, LOW);
  // A1 is the wiper:  

  // setup the serial connection
  Serial.begin(115200);
  //Serial.println("hello world");  

  // the fastest PWM output is with Timer 0, on pins 5+6
  TCCR0A = TCCR0A_FAST_PWM_MODE;
  TCCR0B = TCCR0B_CLOCK_PRESCALE_1;
  speedup = 64;
  pinMode(OC0A_PIN, OUTPUT);    
  pinMode(OC0B_PIN, OUTPUT);
  // Now to set the PWM output, we simply have to set the 
  // hardware registers:    
  OCR0A = 123;  // -> pin 6
  OCR0B = 123;  // -> pin 5
  
  // setup timer1 for regular interupt driven PWM register updates
  TCCR1A = TCCR1A_CTC_MODE;
  TCCR1B = TCCR1B_CTC_MODE | TCCR1B_CLOCK_PRESCALE_1;
  TCNT1  = 0;//initialize counter value to 0
  // this is 1 kHz updates at 16000
  OCR1A = 16000/4; // PWM update rate
  waveform_update_frequency=4000;
  TIMSK1 |= (1 << OCIE1A);
   
  setup_function_generator();
  setup_scope();
}

void loop() {  
  if (scope_state == FULL){
      if (millis()-last_readout > 1000*speedup){
        digitalWrite(analed_pin, HIGH);
        delay(100*speedup);
        digitalWrite(analed_pin, LOW);
        serial_readout();
        last_readout = millis();        
      }
      state_count=0;
      scope_state=READY;
  }
  if (millis()-last_update > 100*speedup){
    // read the state of the pushbutton value:
    int button     = digitalRead(button_pin);
    waveform_amplitude = 255;
    waveform_frequency = 100;   
    //waveform_amplitude = param;
    waveform_frequency = param/2;
  
    if (button != last_button) {
      last_button = button;
      // go to next output mode if button is pressed:
      if (button == LOW){
        //Serial.print("button pressed...output mode is now:  "); 
        output_mode = (output_mode+1) % modes;
        //Serial.println(output_mode);                      
        setup_for_output_mode();
        waveform_count = 0;
      }    
    }
    last_update = millis();    
  }
}
