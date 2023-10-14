import random
import numpy as np
import matplotlib.pyplot as plt

resistors={ 'R1' : 3.3 , 'R2' : 3.9 , 'R3' : 8.2 }
voltages={ 'V1' : 10 , 'V2' : 5 }
rerror=.05
verror=.01

def experiment(rng):
    r1=resistors['R1']+rerror*rng.uniform(-1,1)
    r2=resistors['R2']+rerror*rng.uniform(-1,1)
    r3=resistors['R3']+rerror*rng.uniform(-1,1)
    v1=voltages['V1']+rerror*rng.uniform(-1,1)
    v2=voltages['V2']+rerror*rng.uniform(-1,1)
    Req=r2/(r1+r2)
    Voc=(r2/(r1+r2)*v1)-v2
    return Voc/(r3+Req)

rng=random.SystemRandom()
experiments=[experiment(rng) for _ in xrange(100000)]
print "Mean: ",np.mean(experiments)
print "Std Dev: ",np.std(experiments)
print "Percent error: ",np.std(experiments)/np.mean(experiments)*100

plt.hist(experiments,normed=True)
plt.xlabel("Current [mA]")
plt.ylabel("Probability density")
plt.savefig('random_error.pdf')
