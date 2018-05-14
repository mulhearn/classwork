#
# serial_eg.py
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
from scipy import signal
from matplotlib import ticker

#SERIAL_PORT="COM4"
SERIAL_PORT="/dev/cu.usbmodem1421"
#SERIAL_PORT=raw_input("Enter the serial port for the Arduino (e.g. COM4):  ")

print "connecting to the Arduino..."


# open the serial connection
ser = serial.Serial(SERIAL_PORT, 115200)
time.sleep(1)

# that resets Arduino, so first we wait to receive initializing string from Arduino
print ser.readline().strip()


# Now wait for a key press to acquire the data:
raw_input("Press Enter to Acquire...")    
# Now we can send our acquire data signal:
nrun=int(10)
dt = int(1)
print nrun
print dt
s = "a {0:d} {1:d}".format(nrun, dt)
print "sending acquire command:  " + s 
ser.write(s)
# first line is the length of the payload:
nsamp = int(ser.readline().strip())
nrun  = int(ser.readline().strip())
scale = int(ser.readline().strip())
mv    = (4675/255.0)*(scale/255.0)

xl = np.zeros((nrun,nsamp), dtype=float)
yl = np.zeros((nrun,nsamp), dtype=float)
print "receiving payload from Arduion of length ", nsamp, " x ", nrun, "\n"
print "voltage scale is ", scale

for i in range(nrun):
    print "run ", i
    for j in range(nsamp):
        str = ser.readline().strip()
        # print str
        x,y = str.split()
        if ((i<5) and (j<5)):
            print "x: ", x, "y: ", y
        xl[i][j] = float(x);
        yl[i][j] = float(y)
ser.close()

tau = dt/76.9
xl = tau * xl
mean = np.mean(yl)
yl = mv * (yl-mean)
for i in range(nrun):
    plt.plot(xl[i], yl[i])
plt.xlabel("time [milliseconds]")
plt.ylabel("voltage m[V]")
plt.savefig('waveform.png')
np.savetxt('waveform.txt', np.column_stack((xl,yl)))
plt.show();

fs = 76.9/dt;

max = nsamp
f = []
pavg = []
var  = 0;
for i in range(nrun):
    f, psd = signal.periodogram(yl[i], fs)
    if (i == 0):
        pavg = psd
        var = np.var(yl[i])
    else:
        pavg += psd
        var += np.var(yl[i])

pavg = pavg / float(nrun)
var  = var / float(nrun)
rms  = (var**0.5)
#print favg
#print pavg

imax = np.argmax(pavg)
pmax = pavg[imax]
fmax = f[imax]
vmax = (2*pmax*fs/nsamp)**0.5
print "sample rms is ", rms
print "peak at f=", fmax, " with Vrms=", vmax


a = imax - 10
b = imax + 10
if (a < 0):
    a = 0
if (b > len(f)):
    b = len(f);

vtot = 2*(np.sum(pavg)/fs)**0.5
vint = 2*(np.sum(pavg[a:b])/fs)**0.5
print "total integrated rms is ", vtot
print "in region of peak is ", vint
print "mean of PSD:  ", np.mean(pavg), "mV^2/kHz"
ia = (1.0/fs)*nsamp
ib = (5.0/fs)*nsamp
print "mean of PSD in region:  ", np.mean(pavg[ia:ib]), "mV^2/kHz"

fig, ax = plt.subplots(1,1)
ax.semilogy(f, pavg)
ax.set_xlabel('frequency [kHz]')
ax.set_ylabel('PSD [mV^2/kHz]')
ax.set_ylim(1E-10, 1E10)
ax.set_xlim(0, 10.0)
tick_spacing = 0.1
ax.xaxis.set_minor_locator(ticker.MultipleLocator(tick_spacing))
plt.savefig('psd.png')
plt.show()


#ser.close()
