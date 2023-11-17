import numpy as np
import atexit

c = 0.5


class Rational():
    def __init__(self, m: int, n: int, dim=1):
        self.m = m
        self.n = n
        self.dim = dim
        self.period =self.getPeriod()

        self.digits: list = []
        self.reminders: list = []
        self.digits, self.reminders = self.getSequence()
        self.positions = [self.getPosition(t) for t in range(self.period + 1)]
        # del self.digits
        del self.reminders
        atexit.register(self.cleanup)

    def cleanup(self):
        del self.positions

    def getSequence(self):
        base = int(2**self.dim)
        if self.m == 0:
            reminders: list = [0]
            digits: list = [0]
            return (digits, reminders)
        elif self.m == self.n:
            reminders: list = [self.m]
            digits: list = [base - 1]
            return (digits, reminders)
        digits: list = []
        reminders: list = []
        reminder: np.uint16 = self.m
        digit: np.uint8 = reminder * base // self.n
        while True:
            digits.append(digit)
            # reminders.append(reminder)
            reminder = (reminder * base) % self.n
            digit = reminder * base // self.n
            if reminder == self.m:
                break
        return (digits, reminders)

    def getPeriod(self):
        if self.n == 1:
            return 1
        base = 2**self.dim
        p = 1
        reminder = 1
        while True:
            reminder = (reminder * base) % self.n
            if reminder == 1:
                break
            p = p + 1
        return p

    def getPosition(self, t):
        period = len(self.digits)
        x: np.float16 = 0.0
        y: np.float16 = 0.0
        z: np.float16 = 0.0
        for i in range(t):
            digit = self.digits[i % period]
            dx = (digit % 2)
            dy = (digit // 2) % 2
            dz = (digit // 4) % 2
            x += c - dx
            y += c - dy
            z += c - dz
        return (x, y, z)

    def period(self):
        return self.period

    def path(self):
        return ''.join([str(d) for d in self.digits])

    def reminders(self):
        return self.reminders

    def position(self, t):
        px: np.float16 = 0.0
        py: np.float16 = 0.0
        pz: np.float16 = 0.0
        nt = t // self.period
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
        T = len(self.digits)
        return self.digits[t % T]
    
    def time(self, t):
        T = len(self.digits)
        time = 0
        for i in range(t):
            if self.digits[i % T] != self.digits[(i + 1) % T]:
                time += 1
        return time

    def __str__(self) -> str:
        return f'({self.m} / {self.n})'

if __name__ == '__main__':
    dim = 1
    T = 10
    n = (2**dim)**int(T) - 1
    r = Rational(682, n, dim=dim)
    print(r, r.path(), r.time(10))
