#!/usr/bin/env python

# these are operations the LMC commands

ADD=1
SUB=2
STA=3
LDA=5
BRA=6
BRZ=7
BRP=8
INP=901  # a bit silly, but we'll live!
OUT=902  # "
COB=0

# we don't print any COB op command, because this might precede data as well
def opname(i):
    if (i==ADD):
        return "ADD"
    if (i==SUB):
        return "SUB"
    if (i==STA):
        return "STA"
    if (i==LDA):
        return "LDA"
    if (i==BRA):
        return "BRA"
    if (i==BRZ):
        return "BRZ"
    if (i==BRP):
        return "BRP"
    if (i==INP):
        return "INP"
    if (i==OUT):
        return "OUT"
    return ""

# we'll keep operation code separate from address.  This is slightly
# different then LMC specs, but easier for us to implement.
OP = []
MB = []

AC = 0 # accumulator
PC = 0 # program counter

# utility functions for programming and emulation:

# initialize the mailboxes
def init():
    for i in range(100):
        OP.append(0)
        MB.append(0)
        
# program line i with op code x and address y
def program(i,x,y):
    OP[i]=x
    MB[i]=y

def print_stack():
    zc = 0
    for i in range(100):
        if ((OP[i] == 0) and (MB[i] == 0)):
            if (zc > 0):
                continue;
            else:
                zc = zc + 1;
        print i, ": ", opname(OP[i]), " ", MB[i] 

def emulate():
    global AC,PC
    while(OP[PC]):
        pc = PC
        op = OP[PC]
        mb = MB[PC]
        print "On command:  ", PC, " ", opname(OP[PC]), " ", MB[PC]
        PC = PC + 1
        if (op == INP):
            AC = input("?")
        if (op == STA):
            MB[mb]=AC
        if (op == LDA):
            AC=MB[mb]
        if (op == ADD):
            AC = AC + MB[mb]
        if (op == OUT):
            print "OUT:  ", AC


def main():
    init()
    program(0,INP,0)
    program(1,STA,50)
    program(2,INP,0)
    program(3,ADD,50)
    program(4,OUT,0)
    program(5,COB,0)
    print_stack()
    emulate()
    print_stack()

if __name__ == '__main__':
    main()


