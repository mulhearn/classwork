#!/usr/bin/env python

#Made an ordinary python version because ipython isn't working on my laptop

from numpy import *
import numpy as np
import matplotlib.pyplot as plt

f = 5E3 # 5 kHz
phi = 0.25
w = 2*pi* f *(1E-6) # in units of 1/ms
t = np.arange(0,200,1, dtype=np.float)

tx = [100]
ty = [0]

ya = -2.0*sin(w*t)
yb = -(2.0/sqrt(2.0))*sin(w*t-pi/4.0)
plt.plot(t,ya, label="Vin",linestyle="dashed",color="red")
plt.plot(t,yb, label="Vout",linestyle="dotted",color="green")
plt.plot(tx,ty,"o",label="Trigger",color="blue")
plt.xlabel("Time [ms]")
plt.ylabel("Voltage [V]")
plt.legend(numpoints=1,loc=4)
plt.axhline(0,color="blue")
plt.axvline(100,color="blue")
plt.axvline(125,color="blue")
plt.axhline(sqrt(2),color="blue")
plt.axhline(2.0,color="blue")
plt.ylim(-2.5,2.5)
plt.savefig("scope_gain.pdf")
plt.xticks(np.arange(0, 201, 25.0))
plt.yticks(np.arange(-2.5, 2.51, 0.5))

 
