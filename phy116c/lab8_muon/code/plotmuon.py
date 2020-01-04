#
# plotmuon.py
#
# An example program for plotting the muon decay time distribution
# 

import matplotlib.pyplot as plt
import numpy as np

delta,tstamp = np.loadtxt("muon.txt",unpack=True) # read the muon lifetime data
delta = delta / 1000.0 # convert to microseconds (1 ADC count = 1 ns)


# build a histogram of the decay data:
bins = np.arange(0,20,0.5)
h,bins = np.histogram(delta,bins=bins)
hunc = h ** 0.5 # assume Gaussian uncertatinties

#plot the histogram, with error bars:
fig, ax = plt.subplots(1,1)
ax.set_xlabel('decay time [microseconds]')
ax.set_ylabel('events')
ax.errorbar(bins[:-1],h,yerr=hunc,fmt="ko")
ax.set_yscale("log")
plt.savefig("muon.pdf")
plt.show()
