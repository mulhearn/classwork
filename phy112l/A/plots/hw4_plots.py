"""Plots for PHY 112L HW 4 (hw4_ising.tex), written next to this file:

    python3 hw4_plots.py

ssb.pdf:  graphical solution of the mean-field equation s = tanh(Jn s / kT):  the line x against
          tanh(x/2) (Jn/kT < 1, one solution) and tanh(2x) (Jn/kT > 1, three solutions).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

x = np.linspace(-np.pi, np.pi, 100)
plt.figure()
plt.plot(x, x, "k--", label="x")
plt.plot(x, np.tanh(0.5*x), "r-", label="tanh(x / 2)")
plt.plot(x, np.tanh(2*x), "b:", label="tanh(2 x)")
plt.ylim(-1.2, 1.2)
plt.legend()
plt.xlabel("x")
plt.ylabel("f(x)")
plt.savefig(os.path.join(HERE, "ssb.pdf"))
plt.close()
