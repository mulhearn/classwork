"""Plots for PHY 112L HW 1 (hw1_ideal_compression.tex), written next to this file:

    python3 hw1_plots.py

mbvelocity.pdf:  velocity-component PDFs at three temperatures.
vinit.pdf:       velocities of the gas just after initialization (uniform, not thermal).
vself.pdf:       the same gas after 100,000 collisions among its own molecules.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NGAS = 10000          # molecules
VMAX = 3              # initial velocities uniform in (-VMAX, VMAX)
NCOLL = 100000        # self-collisions before vself.pdf

rng = np.random.default_rng(112)
v = np.linspace(-5, 5, 200)


# mbvelocity:  PDF of one velocity component at temperature T (our units)
def mbvelocity(v, T):
    return np.sqrt(1 / (2*np.pi*T)) * np.exp(-v**2 / (2*T))


def temp(vx, vy):
    return 0.5 * (np.mean(vx**2) + np.mean(vy**2))


# collide:  elastic collision of molecules a and b, scattered by theta in the center of mass
def collide(ax, ay, bx, by, theta):
    ux = (ax - bx) / 2
    uy = (ay - by) / 2
    dax = (np.cos(theta) - 1)*ux - np.sin(theta)*uy
    day = (np.cos(theta) - 1)*uy + np.sin(theta)*ux
    return ax + dax, ay + day, bx - dax, by - day


# plot_vx_vy:  histograms of vx and vy, with Maxwell-Boltzmann at the gas temperature
def plot_vx_vy(vx, vy, name):
    hvx, bins = np.histogram(vx, bins=20, range=(-5, 5))
    hvy, bins = np.histogram(vy, bins=20, range=(-5, 5))
    cbins = (bins[1:] + bins[:-1]) / 2
    T = temp(vx, vy)
    plt.figure()
    plt.errorbar(cbins, hvx, yerr=np.sqrt(hvx), fmt="ro", label="vx")
    plt.errorbar(cbins, hvy, yerr=np.sqrt(hvy), fmt="bs", label="vy")
    plt.plot(v, len(vx) * (bins[1] - bins[0]) * mbvelocity(v, T), "k--", label="Maxwell-Boltzmann")
    plt.legend()
    plt.text(0.05, 0.95, rf"$T = {T:.1f}\;T_0$", transform=plt.gca().transAxes, ha="left", va="top")
    plt.xlabel("velocity ($v_0$)")
    plt.ylabel("molecules")
    plt.savefig(os.path.join(HERE, name))
    plt.close()


plt.figure()
plt.plot(v, mbvelocity(v, 1), "r-", label=r"$T=1\,T_0$")
plt.plot(v, mbvelocity(v, 2), "g--", label=r"$T=2\,T_0$")
plt.plot(v, mbvelocity(v, 5), "b:", label=r"$T=5\,T_0$")
plt.xlabel("velocity ($v_0$)")
plt.ylabel("PDF ($1/v_0$)")
plt.legend(frameon=False)
plt.savefig(os.path.join(HERE, "mbvelocity.pdf"))
plt.close()

vx = rng.uniform(-VMAX, VMAX, NGAS)
vy = rng.uniform(-VMAX, VMAX, NGAS)
plot_vx_vy(vx, vy, "vinit.pdf")

for i in range(NCOLL):
    a, b = rng.choice(NGAS, size=2, replace=False)
    theta = rng.uniform(0, 2*np.pi)
    vx[a], vy[a], vx[b], vy[b] = collide(vx[a], vy[a], vx[b], vy[b], theta)
plot_vx_vy(vx, vy, "vself.pdf")
