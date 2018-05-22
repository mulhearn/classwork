#
# psd.py
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

#
# User settable parameters
#

calib_mv = 5000  # calibrated Arduino full scale determined with CircuitTester
nrun    = 1      # number of full buffers to request with acquire
dt      = 1      # time resolution requested (1 is as fast as possible - 76.9 kHz)
fmin    = 1      # minimum frequency to consider for peak finding
nnarrow = 10*dt  # narrow peak integral (1 kHz width)
nwide   = 30*dt  # wide peak integral (3 kHz width)
fup     = 40     # maximum frequency (kHz) to display in periodogram
fa      = 5      # min of PSD integration window (kHz)
fb      = 10     # max of PSD integration window (kHz) 

#SERIAL_PORT="COM4"
#SERIAL_PORT="/dev/cu.usbmodem1421"
SERIAL_PORT="/dev/tty.usbmodem1411"
#SERIAL_PORT=raw_input("Enter the serial port for the Arduino (e.g. COM4):  ")

#
# You shouldn't have to change anything below here...
#

print "connecting to the Arduino..."


# open the serial connection
ser = serial.Serial(SERIAL_PORT, 115200)
time.sleep(1)

# that resets Arduino, so first we wait to receive initializing string from Arduino
print ser.readline().strip()

# Now wait for a key press to acquire the data:
tag = raw_input("Enter a text tag for this run (or just press enter):  ")    
tag = tag.rstrip()
if (tag != ""):
    tag = "_" + tag
    print "using tag:  ", tag
outfilename = "raw_waveforms" + tag + ".txt"
print "will save output to file ", outfilename



# Now we can send our acquire data signal:
print nrun
print dt
s = "a {0:d} {1:d}".format(nrun, dt)
print "sending acquire command:  " + s 
ser.write(s)
# first line is the length of the payload:
nsamp = int(ser.readline().strip())
nrun  = int(ser.readline().strip())
scale = int(ser.readline().strip())
mv    = (calib_mv/255.0)*(scale/255.0)

xl = np.zeros((nrun,nsamp), dtype=float)
yl = np.zeros((nrun,nsamp), dtype=float)
sat = 0
print "receiving payload from Arduion of length ", nsamp, " x ", nrun, "\n"
print "voltage scale is ", scale

for i in range(nrun):
    print "run ", i
    for j in range(nsamp):
        str = ser.readline().strip()
        # print str
        x,y = str.split()
        if ((int(y)==0) or (int(y)==255)):
            sat = sat + 1
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
np.savetxt(outfilename, np.column_stack((xl,yl)))
plt.show();

fs = 76.9/dt;

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

# find maximum excluding low end
imin = (fmin/fs)*nsamp
imax = imin + np.argmax(pavg[imin:])
pmax = pavg[imax]
fmax = f[imax]
vmax = (pmax*fs/nsamp)**0.5
print "sample rms is ", rms
print "peak at f=", fmax, " with Vrms=", vmax

print imax

# integrals near peak:
an = max(0, imax-nnarrow)
bn = min(len(f),imax + nnarrow)
vintn = (np.sum(pavg[an:bn])*fs/nsamp)**0.5
# wider integral:
aw = max(0, imax-nwide)
bw = min(len(f),imax + nwide)
vintw = (np.sum(pavg[aw:bw])*fs/nsamp)**0.5

# total:
vtot = (np.sum(pavg)*fs/nsamp)**0.5

print "saturated count is ", sat
print "total integrated rms is ", vtot
print "in narrow region of peak is ", vintn
print "in wide region of peak is ", vintw

print "mean of PSD:  ", np.mean(pavg), "mV^2/kHz"
ia = (fa/fs)*nsamp
ib = (fb/fs)*nsamp
print "mean of PSD in region:  ", np.mean(pavg[ia:ib]), "mV^2/kHz"

fig, ax = plt.subplots(1,1)
ax.semilogy(f, pavg)
ax.set_xlabel('frequency [kHz]')
ax.set_ylabel('PSD [mV^2/kHz]')
ax.set_ylim(1E-10, 1E10)
ax.set_xlim(0, fup)
tick_spacing = 0.1
ax.xaxis.set_minor_locator(ticker.MultipleLocator(tick_spacing))
plt.show()
