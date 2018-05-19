#
# plot.py
#
# An example program for plotting data saved by psd.py
# 

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from matplotlib import ticker

def get_psd(filename):
    infile = open("data.npy", "r")
    npz = np.load(infile);
    f = npz["arr_0"];
    pavg = npz["arr_1"];
    return f, pavg


fup = 10

f,pavg_2k get_psd("data_2k.npy")
f,pavg_5k get_psd("data_5k.npy")
f,pavg_8k get_psd("data_8k.npy")




fig, ax = plt.subplots(1,1)
ax.semilogy(f, pavg)
ax.set_xlabel('frequency [kHz]')
ax.set_ylabel('PSD [mV^2/kHz]')
ax.set_ylim(1E-10, 1E10)
ax.set_xlim(0, fup)
tick_spacing = 0.1
ax.xaxis.set_minor_locator(ticker.MultipleLocator(tick_spacing))
plt.show()

