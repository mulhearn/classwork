#
# serial_driver.py
# by Michael Mulhearn
#
# An example program for acquiring data from an Arduino over the serial link and 
# graphically displaying it with SciPy.
#
# 1) Opens a serial connection  
# 2) Waits for Arduino init message.
# 3) Waits for user to press enter to acquire data.
# 4) Sends acquire signal to Arduino
# 5) Retrieves data of the serial link
# 6) Plots the data
#
# *** Requires Anaconda (scipy) plus pyserial ***
#

import time, serial
import matplotlib.pyplot as plt
import numpy as np

#SERIAL_PORT="COM4"
#SERIAL_PORT="/dev/cu.usbmodem1421"
SERIAL_PORT=input("Enter the serial port for the Arduino (e.g. COM4):  ")

print("connecting to the Arduino...")

# open the serial connection
ser = serial.Serial(SERIAL_PORT, 115200)
time.sleep(1)

# that resets Arduino, so first we wait to receive initializing string from Arduino
print(ser.readline().strip().decode("ASCII"))


# Now wait for a key press to acquire the data:
input("Press Enter to Acquire...")    
# Now we can send our acquire data signal:
ser.write(str.encode("a"))
# first line is the length of the payload:
nsamp = int(ser.readline().strip().decode("ASCII"))

t_dat = np.zeros(nsamp, dtype=float)
f_dat = np.zeros(nsamp, dtype=float)
print("receiving payload from Arduion of length ", nsamp, "\n")

for i in range(nsamp):
	str = ser.readline().strip().decode("ASCII")
	t,f = str.split()
	if (i<5):
		print("t: ", t, "f(t): ", f)
	t_dat[i] = float(t)
	f_dat[i] = float(f)
ser.close()

plt.plot(t_dat, f_dat)
plt.xlabel("time [arbitrary]")
plt.ylabel("f(t) [ADC counts]")
plt.show();

from scipy import signal
fs=76.900        # Arduino sample frequency in kHz
f, psd = signal.periodogram(f_dat, fs)
plt.semilogy(f, psd)
plt.xlim(0.0,5.0)
plt.xlabel('frequency [kHz]')
plt.ylabel('PSD [COUNT^2/kHz]')
plt.show()



