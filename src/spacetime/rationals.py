import json
from math import pow
c = 0.5

class Rational():
    def __init__(self, m, n):
        self.m = m
        self.n = n
        self.sequences = [self.getSequence(dim) for dim in range(1, 4)]
        self.positions = [self.getPositions(dim) for dim in range(1, 4)]
        
    def getSequence(self, dim):
        base = int(pow(2, dim))
        digits = []
        reminders = []
        reminder = self.m
        digit = int(reminder*base/self.n)
        while True:
            digits.append(digit)
            reminders.append(reminder)
            reminder = (reminder*base)%self.n
            digit = int(reminder*base/self.n)
            if reminder == self.m:
                break
        return (digits, reminders)
    
    def getPositions(self, dim=1):
        output = []
        (digits, _) = self.sequences[dim-1]
        period = len(digits)
        x = 0.0
        y = 0.0
        z = 0.0
        for i in range(period+1):
            if   dim == 1: output.append([x])
            elif dim == 2: output.append([x, y])
            elif dim == 3: output.append([x, y, z])
            digit = digits[i%period]
            dx =     (digit%2)
            dy = (int(digit/2)%2)
            dz = (int(digit/4)%2)
            x += c-dx
            y += c-dy
            z += c-dz
        return output

    def period(self, dim=1):
        (digits, _) = self.sequences[dim-1]
        return len(digits)
    
    def path(self, dim=1):
        digits, _ = self.sequences[dim-1]
        return ''.join([str(d) for d in digits])
        
    def position(self, t, dim=1):
        return self.positions[dim-1][t%self.period(dim)]

    def digit(self, t, dim=1):
        (digits, _) = self.sequences[dim-1]
        T = len(digits)
        return digits[t%T]

if __name__ == '__main__':
    r = Rational(1, 27)
    print r.period()
    print r.path(dim=1)
    print r.path(dim=2)
    print r.path(dim=3)
    for t in range(r.period(dim=3)+1):
        print t, r.position(t, dim=3)
