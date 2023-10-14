/*

Simple Thermostat
 
This is a simpld thermostat that turns on and off heating 
and cooling through a differential output voltage.

This is a rather lousy algorithm, as it only uses to fixed 
values for the output voltage (one for heating one for cooling),
and it uses a temperature range to avoid rapid cycling.

The intention is to demonstrate control with feedback from 
the thermoelectric device.  The logic should be modified to 
implement a PID algorithm.

 */

// set PWM outputs pwm_plus and pwm_minus 
// to a differential voltage of vout in Volts
// (kept in range +/- 5 V)
int pwm_plus  = 9;
int pwm_minus = 10;

// the input pin for feedback from thermo-resistor
int inp = A0;

// This defines the safe output voltage range.
// It is set to a narrow range initially, but 
// should be extended through testing while monitoring
// the supply currents.
double safe_vout_max = 2.0;
double safe_vout_min = -2.0;

//This is the manual voltage mode, it just sets a constant
// output voltage, and monitors the voltage from the thermistor.

int manual = 1;  // 0 turns manual mode off, 1 turns it on
// The Manually set constand Arduino ouput voltage:
double vman = -1.0;

//These are parameters of the simple thermostat:
int thermostat = 0;  // 0 turns thermostat mode off, 1 turns it on
enum {COOL, STANDBY, HEAT};

// The voltage across thermoristor:
// V = 3.0 HOT
// V = 2.3 COLD


double vset   = 4.0; // target voltage
double vswing = 0.1; // allowed voltage swing (to avoid rapid cycling)
int mode = STANDBY;  
// note that some controllers have opposite polarity 
// ... if you are cooling when you need heat, switch these!
double vcool = 2.0;
double vheat = -2.0;

// set the output voltage to specified value 
// (or the maximum/minimum safe voltage if out of range)
// returns the value set in case needed for PID algorithm.
double set_vout(double vout){
  // these thresholds are absolute maximums:
  if (vout > 5.0)  vout =  5.0;
  if (vout < -5.0) vout = -5.0;
  
  // these thresholds are adjustable... with care:
  if (vout > safe_vout_max)  vout =  safe_vout_max;
  if (vout < safe_vout_min)  vout =  safe_vout_min;

  // now convert to binary format:  5V = 255   
  unsigned uval = 255*(fabs(vout) / 5.0);
  if (uval > 255) uval = 255;

  // we use a differtial volatge to manage +/- 5 V output.
  // if vout is less than 0, we set pwm_minus to -vout
  // if vout is more than 0, we set pwm_plus to vout    
  if (vout < 0.0){
     analogWrite(pwm_minus, uval);
     analogWrite(pwm_plus, 0);     
   } else {
     analogWrite(pwm_minus, 0);
     analogWrite(pwm_plus, uval);     
   }
    Serial.print("vout ");
    Serial.println(vout);
   
   // return actual value set, for possible use in PID algorithm
   return vout;    
}




// the setup routine runs once when you press reset:
void setup()  { 
  // increase frequency of PWM output to maximum:
  // (note this effects output of millis!!!)
  //TCCR0B = (TCCR0B & 0b1111100) | 0b001;
  // declare output pin to be an output:
  pinMode(pwm_plus, OUTPUT);
  pinMode(pwm_minus, OUTPUT);
  set_vout(0.0);
  Serial.begin(9600); 
  
  if (manual){
     Serial.print("Manual mode:  fixed voltage ");
     Serial.println("");
     return;
  }
  if (thermostat){
     Serial.print("Thermostat mode");
     Serial.print("vset ");
     Serial.println(vset);
     Serial.print("vswing ");
     Serial.println(vswing);     
     return;
  }
  
  Serial.print("vset is ");   
  Serial.println(vset);
}


void loop()  {
    // read the voltage across a voltage divider composed of the thermoresistor   
  unsigned x = analogRead(inp);  
  double vx = 5.0 * ((double) x) / 1023.0;
  Serial.print("vx is ");
  Serial.println(vx);
  
  // this is manual mode, just set a fixed output voltage,
  // useful for initial debugging of circuit:
  if (manual){  
    set_vout(vman);  
    delay(1000);
    return;
  }

  if (thermostat){
    // In our system, a higher voltage across the reference resistance 
    // means a lower resistance on the (negative thermal constant) termistor.
    // So orientation is:  high voltage means time to cool. 
    if (vx > vset + vswing){
       mode = COOL; 
    } 
    if (vx < vset - vswing){
       mode = HEAT;
    } 
    if ((mode == COOL) && (vx < vset)){
       mode = STANDBY;
    }
    if ((mode == HEAT) && (vx > vset)){
       mode = STANDBY;
    }
  
    if (mode == COOL) set_vout(vcool);
    if (mode == HEAT) set_vout(vheat);
    if (mode == STANDBY) set_vout(0.0);
    delay(1000);
    return;
  }
  
  

  
}

