
// Arduino Pinout Definitions:
// clock-related signals:
const int CLK = 2;     // Clock output
const int PWM_PIN = 3; // PWM pin for use as clock
const int TRIG = 4;    // a handy trigger at count=0 state=0
// ALU control signals:
const int LCH = 5;  // common latch for reg A/B/C on rising edge
const int OES = 6; // output enable for the shift register (active low)
// the four-bit data bus:
const int DAT0 = 8;
const int DAT1 = 9;
const int DAT2 = 10;
const int DAT3 = 11;

// Utilities for reading/writing the 4-bit data bus from Arduino
void data_out();
void data_in();
void write_data_bus(unsigned int dat);
unsigned int read_data_bus();

// Program Counter Register (emulated on Arduino)
unsigned int pc=0;

// Processor Memory (emulated on Arduino)
const int MAX=256;  // 8-bit addresses
unsigned int memory[MAX];
// each 8-bit location contains either:
// a 4-bit command plus and 8-bit associated address
// a 4-bit value 
// implemented commands:
// COB:   coffee break... just kidding!  Go back to pc=0!
// LOAD:  latch contents of address into registers A/B/C
// NAND:  assert NAND operation output onto data bus, store at address
// SHIFT: assert SHIFT operation output onto data bus, store at address.
// GOTO:  (not implemented)
// BRZ:   (not implemented)
enum{COB=0, LOAD=1, NAND=2, SHIFT=3, GOTO=4, BRZ=5};
// utility for dumping non-zero memory contents to serial port:
void dump_memory();

// State Logic Definitions:
// Start: begin program execution at next falling edge, starting with PC=0
// Run:  program exectution in progress
// Done:  program completed, update the serial port
enum {START, RUN, DONE};
unsigned int state;
unsigned int rising = 1;  // clock rising/falling
unsigned int dumps = 0;  // have we dumped to serial port already?

// Available Example Programs:
// nand_demo: test patterns sent to NAND operation
// correct output:
// at address 64:  0b1100 NAND 0b1010 = 0x7
// at address 65:  0b0110 NAND 0b0101 = 0xB
// at address 66:  0b0011 NAND 0b1010 = 0xD
// at address 67:  0b1001 NAND 0b0101 = 0xE



void nand_demo();
// shift_demo: test patterns sent to SHIFT operation 
// correct output:
// at address 67:  0b0001<<1 = 2
// at address 68:  0b0010<<1 = 4
// at address 69:  0b0100<<1 = 8
// at address 70:  0b1000<<1 = 1

// DAT0 scope:  10 00 00 01
// DAT2 scope   01 10 00 00

void shift_demo();
// add implements a 4-bit adder
// correct output:
// at address 152:  sum of a+b
void add(unsigned int a, unsigned int b);


// setup Arduino:
const int HALF_DUTY_CYCLE=127;
void setup() {
  data_in();
  pinMode(PWM_PIN,  OUTPUT);
  pinMode(CLK,      OUTPUT);
  pinMode(TRIG,     OUTPUT);
  pinMode(LCH,      OUTPUT);
  pinMode(OES,      OUTPUT);
  digitalWrite(OES, 1); 
  analogWrite(PWM_PIN, HALF_DUTY_CYCLE);
  Serial.begin(38400) ;
  Serial.println("Serial Port Initialized");

  for (int i=0;i<MAX;i++) 
    memory[i]=0;
  // use one or more of the following example programs:
  //add(2,3);
  //shift_demo();  
  nand_demo();  
  Serial.println("Program Initialized:");
  dump_memory();
  state=START;  
  attachInterrupt(digitalPinToInterrupt(PWM_PIN), pwm_change,  CHANGE);
}

void loop() {  
  if (state==DONE){
    //detachInterrupt(digitalPinToInterrupt(PWM_PIN));  
    Serial.println("Program Finished:");
    dump_memory();
    dumps++;
    state=START;
    //attachInterrupt(digitalPinToInterrupt(PWM_PIN), pwm_change,  CHANGE);
  }
}

void pwm_change(){
  if (rising){
    clk_rising();
    rising = 0;
  } else {
    clk_falling();
    rising = 1;
  }
}

void clk_falling(){
  digitalWrite(CLK,  0);

  //clock A/B always goes to zero on falling edge.
  digitalWrite(LCH, 0);
  
  // run starts with program counter at zero on falling edge pf clock
  if (state==START){
    pc = 0;
    state = RUN;
    digitalWrite(TRIG, 1);
  } else {
    digitalWrite(TRIG, 0);     
  }
  
  unsigned cmd = memory[pc]&0xf;
  unsigned adr = (memory[pc]>>4)&0xff;

  if (cmd==COB){    
    // to avoid confusion, we'll assert 0 on the data bus during COB
    data_out();    
    write_data_bus(0);      
    digitalWrite(OES, 1);
    // if we've already updated serial port once, we just go right 
    // to start, otherwise, we pass through DONE state, triggering 
    // serial port memory dump:
    if (dumps){
      state = START;
    } else {
      state = DONE;
    }
    return;
  } else if (cmd == LOAD){
    data_out();
    write_data_bus(memory[adr]);      
    digitalWrite(OES, 1);
  } else if (cmd == NAND){
    data_in();
    digitalWrite(OES, 1);
  } else if (cmd == SHIFT){
    data_in();
    digitalWrite(OES, 0);    
  } else {  // no-op
    data_out();    
    write_data_bus(0);      
    digitalWrite(OES, 1);
  }
}

void clk_rising(){  
  digitalWrite(CLK,  1);

  if (state!=RUN) return;

  unsigned cmd = memory[pc]&0xf;
  unsigned adr = (memory[pc]>>4)&0xff;

  if (cmd == LOAD){
    digitalWrite(LCH, 1);
  } else if (cmd == NAND){
    memory[adr] = read_data_bus();
  } else if (cmd == SHIFT){
    memory[adr] = read_data_bus();
  }  
  pc++;
}


//
// Utility program implementations:
//

void dump_memory(){
  int zero=0;
  for (int i=0;i<MAX;i++){
      unsigned int m = memory[i];
      if (m==0) {
        if (zero!=0) continue;
        zero = 1;        
      }
      Serial.print(i);
      Serial.print(" ");
      Serial.println(memory[i], HEX);      
  }
}

void data_out(){
  pinMode(DAT0,     OUTPUT);
  pinMode(DAT1,     OUTPUT);
  pinMode(DAT2,     OUTPUT);
  pinMode(DAT3,     OUTPUT);
}

void data_in(){
  pinMode(DAT0,     INPUT);
  pinMode(DAT1,     INPUT);
  pinMode(DAT2,     INPUT);
  pinMode(DAT3,     INPUT);
}

void write_data_bus(unsigned int dat){
  //digitalWrite(DAT0, 1);
  digitalWrite(DAT0, (dat&1)!=0);
  digitalWrite(DAT1, (dat&2)!=0);
  digitalWrite(DAT2, (dat&4)!=0);
  digitalWrite(DAT3, (dat&8)!=0);
}

unsigned int read_data_bus(){
  unsigned int x = 0;
  x |= digitalRead(DAT0);
  x |= (digitalRead(DAT1)<<1);
  x |= (digitalRead(DAT2)<<2);
  x |= (digitalRead(DAT3)<<3);
  return x;
}

//
// Example programs implementations in assembly
//

// utility for writing a command to memory:
void write_cmd(unsigned int cmd, unsigned int addr){
  memory[pc] = cmd;
  memory[pc] |= (addr << 4);  
  pc++;
}

void add(unsigned int a, unsigned int b){  
  // user inputs, to be added:
  memory[150]=a;  // a  
  memory[151]=b;  // b

  memory[152]=0;  // reserved for answer
  memory[153]=0;  // reserved carry
  memory[154]=0;  // reserved for not a
  memory[155]=0;  // reserved for not b

  // constants:
  memory[156]=1;  // one
  memory[157]=0;  // reserved for not one

  // calculate not one:
  write_cmd(LOAD, 156);
  write_cmd(LOAD, 156);  
  write_cmd(NAND, 157);  
  
  // not a:
  write_cmd(LOAD, 150);
  write_cmd(LOAD, 150);  
  write_cmd(NAND, 154);  

  // not b:
  write_cmd(LOAD, 151);
  write_cmd(LOAD, 151);  
  write_cmd(NAND, 155);  

  // put a -> ans  
  write_cmd(LOAD, 154);
  write_cmd(LOAD, 154);  
  write_cmd(NAND, 152);  

  // put b -> carry  
  write_cmd(LOAD, 155);
  write_cmd(LOAD, 155);  
  write_cmd(NAND, 153);  

  // the next part is simply repeated three times:
  for (int i=0; i<3;i++){
  // pass 1:
  // (A nand B) -> 158
  write_cmd(LOAD, 152);
  write_cmd(LOAD, 153);  
  write_cmd(NAND, 158);
  // (A and B) = not (A nand B) -> 159
  write_cmd(LOAD, 158);
  write_cmd(LOAD, 158);  
  write_cmd(NAND, 159);
  // A or B = (not A nand not B) -> 160
  write_cmd(LOAD, 154);
  write_cmd(LOAD, 155);  
  write_cmd(NAND, 160);

  // for next round, not A = not (A xor B) 
  // calculate: not (A xor B) = (A or B) nand (A nand B)
  // save to !A for next round:
  write_cmd(LOAD, 160);
  write_cmd(LOAD, 158);  
  write_cmd(NAND, 154);

  // put a -> ans  
  write_cmd(LOAD, 154);
  write_cmd(LOAD, 154);  
  write_cmd(NAND, 152);  

  // ... shift ...
  write_cmd(LOAD,  159);
  write_cmd(SHIFT, 159);  

  // calcualte not B for next round
  write_cmd(LOAD, 159);
  write_cmd(LOAD, 157);
  write_cmd(NAND, 155);  
  
  // calculate B for next round
  write_cmd(LOAD, 155);
  write_cmd(LOAD, 155);
  write_cmd(NAND, 153);  
  }  
}

// test pattern for shift:
void shift_demo(){
    memory[128]=1;
    memory[129]=2;
    memory[130]=4;
    memory[131]=8;
    write_cmd(LOAD, 128);
    write_cmd(SHIFT, 68);
    write_cmd(LOAD, 129);
    write_cmd(SHIFT, 69);  
    write_cmd(LOAD, 130);
    write_cmd(SHIFT, 70);
    write_cmd(LOAD, 131);
    write_cmd(SHIFT, 71);
}

void nand_demo(){
  memory[132]=0b1100;
  memory[133]=0b1010;
  memory[134]=0b0110;
  memory[135]=0b0101;
  memory[136]=0b0011;
  memory[137]=0b1010;
  memory[138]=0b1001;
  memory[139]=0b0101;
  // test pattern for nand:
  write_cmd(LOAD, 132);
  write_cmd(LOAD, 133);  
  write_cmd(NAND, 64);  
  
  write_cmd(LOAD, 134);
  write_cmd(LOAD, 135);  
  write_cmd(NAND, 65);  

  write_cmd(LOAD, 136);
  write_cmd(LOAD, 137);  
  write_cmd(NAND, 66);  

  write_cmd(LOAD, 138);
  write_cmd(LOAD, 139);  
  write_cmd(NAND, 67);  
}

