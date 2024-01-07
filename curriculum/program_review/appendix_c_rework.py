A=27
B=35
import numpy as np


def avg(tag, app, phy, col):
    eps = float(A*app + B*phy)/(A+B)/100.
    avg = np.round(eps*100, 0)
    unc = np.round(100*(eps*(1.0-eps)/(A+B))**0.5, 0) # binomial
    col = np.round(col, 0)
    print("%s & %d $\\pm$ %d & %d & " % (tag, avg, unc, col))

avg("C1", 89, 91, 91)
avg("C2", 93, 89, 90)
avg("C3", 81, 77, 85)
avg("C4", 89, 89, 93)
print("")
avg("C5",  54, 56, 64)
avg("C6",  73, 69, 74)
avg("C7",  69, 48, 60)
avg("C8",  77, 79, 79)
avg("C9",  37, 24, 46)
avg("C10", 81, 58, 69)
avg("C11", 76, 64, 69)
print("")    
avg("C23",  62, 46, 76)
avg("C24",  81, 86, 68)
avg("C25",  81, 86, 73)
avg("C26",  74, 89, 76)
avg("C27",  44, 51, 61)
avg("C28",  33, 43, 49)
avg("C29",  48, 55, 66)
avg("C30",  81, 71, 61)
print("")
avg("C38",  52, 58, 52)
avg("C39",  59, 53, 47)
print("")
avg("C44",  48, 44, 37)
avg("C45",  59, 47, 56)
avg("C46",  48, 36, 54)
avg("C47",  59, 52, 59)
print("")


A=16
B=21
avg("C54",  63, 57, 46)
avg("C60",  85, 94, 74)
avg("C75",  50, 48, 42)
avg("C76",  47, 67, 65)
avg("C77",  80, 48, 62)

