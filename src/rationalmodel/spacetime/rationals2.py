import numpy
c = 0.5


class Rational():
    def __init__(self, m: numpy.longlong, n: numpy.longlong, dim=1):
        self.m = m
        self.n = n
        self.dim = dim
        self.sequences = self.getSequence()
        self.period =self.getPeriod()
        self.positions = [self.getPosition(t) for t in range(self.period + 1)]

    def getSequence(self):
        base = int(2**self.dim)
        if self.m == 0:
            reminders = [0]
            digits = [0]
            return (digits, reminders)
        elif self.m == self.n:
            reminders = [self.m]
            digits = [base - 1]
            return (digits, reminders)
        digits = []
        reminders = []
        reminder = self.m
        digit = int(reminder * base / float(self.n))
        while True:
            digits.append(digit)
            reminders.append(reminder)
            reminder = (reminder * base) % self.n
            digit = int(reminder * base / float(self.n))
            if reminder == self.m:
                break
        return (digits, reminders)

    def getPeriod(self):
        base = int(pow(2, self.dim))
        p = 1
        reminder = 1
        while True:
            reminder = (reminder * base) % self.n
            if reminder == 1:
                break
            p = p + 1
        return p

    def getPosition(self, t):
        (digits, _) = self.sequences
        period = len(digits)
        x = 0.0
        y = 0.0
        z = 0.0
        for i in range(t):
            digit = digits[i % period]
            dx = (digit % 2)
            dy = (int(digit / 2) % 2)
            dz = (int(digit / 4) % 2)
            x += c - dx
            y += c - dy
            z += c - dz
        return (x, y, z)

    def period(self):
        return self.period

    def path(self):
        digits = self.sequences[0]
        return ''.join([str(d) for d in digits])

    def reminders(self):
        return self.sequences[1]

    def position(self, t):
        px = 0.0
        py = 0.0
        pz = 0.0
        nt = int(t / self.period)
        for _ in range(nt):
            x, y, z = self.positions[self.period]
            px += x
            py += y
            pz += z
        if t % self.period != 0:
            x, y, z = self.positions[t % self.period]
            px += x
            py += y
            pz += z
        if self.dim == 1:
            return (px, )
        elif self.dim == 2:
            return px, py
        return px, py, pz

    def digit(self, t):
        digits = self.sequences[0]
        T = len(digits)
        return digits[t % T]
