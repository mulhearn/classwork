/*
  PlanckMeasurement

  Measure I-V curve of LED for determining
  Planck's constant.
*/

double calib_mv = 5000.0/1023;

void setup() {

  // The potentiometer is installed at A0-A1-A2.
  // Set A0 to VCC and A2 to ground
  pinMode(A0, OUTPUT);
  pinMode(A2, OUTPUT);
  digitalWrite(A0, HIGH);
  digitalWrite(A2, LOW);


  // setup the serial connection
  Serial.begin(115200);

  // setup the serial connection
  Serial.println("Setting 5.0 V Scale");
  analogReference(DEFAULT);
  
  //Serial.println("Setting 1.1 V Scale");
  //analogReference(INTERNAL);
  //calib_mv = calib_mv * 5.0/1.1;
  
  analogRead(A1);
  analogRead(A4);
}

void loop() {
    unsigned a1_raw, a4_raw;
  
    a1_raw       = analogRead(A1);
    a4_raw       = analogRead(A4);
    
    //Serial.print("a1: (");
    //Serial.print(a1_raw);    
    //Serial.print(") ");
    //Serial.print((int)(a1_raw*calib_mv));    
    //Serial.print(" mV  ");

    Serial.print("a4: (");
    Serial.print(a4_raw);    
    Serial.print(") ");
    Serial.print((int)(a4_raw*calib_mv));    
    Serial.print(" mV  ");
    
    Serial.println("");
/*
    //double R = 1.0;
    double R = 0.1;
    int vd = a4_raw*calib_mv;
    int id = (a1_raw-a4_raw)*calib_mv/R;

    Serial.print("vd (mV):  ");
    Serial.print(vd);
    Serial.print("  id (uA):  ");
    Serial.print(id);
    Serial.println("");
  */  
    
    delay(1000);
}
