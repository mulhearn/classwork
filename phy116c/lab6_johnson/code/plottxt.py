#
# plot.py
#
# An example program for plotting data saved by psd.py
# 

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from matplotlib import ticker

max_samples = 1538
fs = 76.9
fup = 40

txtdat = np.loadtxt("raw_waveforms.txt")
#txtdat = np.loadtxt("one_run.txt")

print txtdat.size
nruns = txtdat.size // (max_samples*2)
print "detected data for ", nruns, " runs."
if (nruns==1):
    txtdat = np.reshape(txtdat,(1,2*max_samples))


f = []
pavg = []
for i in range(nruns):
    print "processing run ", i
    x = txtdat[i,:max_samples]
    y = txtdat[i,max_samples:]
    plt.plot(x,y)
    f, psd = signal.periodogram(y, fs)
    if (i == 0):
        pavg = psd
    else:
        pavg += psd

pavg = pavg / float(nruns)

plt.xlim(0,0.5)
plt.show()

fig, ax = plt.subplots(1,1)
ax.semilogy(f, pavg)
ax.set_xlabel('frequency [kHz]')
ax.set_ylabel('PSD [mV^2/kHz]')
ax.set_ylim(1E-10, 1E10)
ax.set_xlim(0, fup)
tick_spacing = 0.1
ax.xaxis.set_minor_locator(ticker.MultipleLocator(tick_spacing))
plt.show()

