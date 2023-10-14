#
# serial_driver.py
# by Michael Mulhearn
#
# An example program for acquiring data from an Arduino over the serial link and 
# graphically displaying it with SciPy.
#
# 1) Opens a serial connection (you will probably need to adjust this) 
# 2) Waits for Arduino init message.
# 3) Waits for user to press enter to acquire data.
# 4) Sends acquire signal to Arduino
# 5) Retrieves data of the serial link
# 6) Plots the data
#
# *** Requires on Anaconda (SciPy) and PySerial libraries. ***
#

import time, serial
import matplotlib.pyplot as plt
import numpy as np

#SERIAL_PORT="COM4"
#SERIAL_PORT="/dev/cu.usbmodem1421"
SERIAL_PORT=raw_input("Enter the serial port for the Arduino (e.g. COM4):  ")

print "connecting to the Arduino..."

# open the serial connection
ser = serial.Serial(SERIAL_PORT, 115200)
time.sleep(1)

# that resets Arduino, so first we wait to receive initializing string from Arduino
print ser.readline().strip()


# Now wait for a key press to acquire the data:
raw_input("Press Enter to Acquire...")    
# Now we can send our acquire data signal:
nrun=int(1)
dt = int(1)
print nrun
print dt
s = "a {0:d} {1:d}".format(nrun, dt)
ser.write(s)
# first line is the length of the payload:
nsamp = int(ser.readline().strip())
nrun  = int(ser.readline().strip())

xl = np.zeros((nrun,nsamp), dtype=float)
yl = np.zeros((nrun,nsamp), dtype=float)
print "receiving payload from Arduion of length ", nsamp, " x ", nrun, "\n";

for i in range(nrun):
    for j in range(nsamp):
        str = ser.readline().strip()
        # print str
        x,y = str.split()
        if ((i<5) and (j<5)):
            print "x: ", x, "y: ", y
        xl[i][j] = float(x)
        yl[i][j] = float(y)
ser.close()

tau = dt/76.9
xl = tau * xl
for i in range(nrun):
    plt.plot(xl[i], yl[i])
plt.xlabel("time [milliseconds]")
plt.savefig('waveform.png')
np.savetxt('waveform.txt', np.column_stack((xl,yl)))
plt.show();



