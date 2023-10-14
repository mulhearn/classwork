
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from matplotlib import ticker

nrun=1  # number of full buffers to request with acquire
dt = 4  # time resolution requested (1 is as fast as possible - 76.9 kHz)

print nrun
print dt

nsamp = 1500
scale = 220
mv    = (4675/255.0)*(scale/255.0)

A = 2**0.5*100/mv;

xl = np.zeros((nrun,nsamp), dtype=float)
yl = np.zeros((nrun,nsamp), dtype=float)
print "simulating payload from Arduion of length ", nsamp, " x ", nrun, "\n"
print "voltage scale is ", scale

for i in range(nrun):
    print "run ", i
    for j in range(nsamp):
        xl[i][j] = j;
        yl[i][j] = A*np.sin(2*np.pi*j*dt*4/nsamp)

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
vmax = (pmax*fs/nsamp)**0.5
print "sample rms is ", rms
print "peak at f=", fmax, " with Vrms=", vmax

print imax

narrow = 10/dt
wide   = 30/dt
# integrals near peak:
an = max(0, imax-narrow)
bn = min(len(f),imax + narrow)
vintn = (np.sum(pavg[an:bn])*fs/nsamp)**0.5
# wider integral:
aw = max(0, imax-wide)
bw = min(len(f),imax + wide)
vintw = (np.sum(pavg[aw:bw])*fs/nsamp)**0.5

# total:
vtot = (np.sum(pavg)*fs/nsamp)**0.5

print "total integrated rms is ", vtot
print "in narrow region of peak is ", vintn
print "in wide region of peak is ", vintw

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
