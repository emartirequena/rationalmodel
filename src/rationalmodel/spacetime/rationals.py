from math import pow
c = 0.5


class Rational():
    def __init__(self, m, n):
        self.m = m
        self.n = n
        self.sequences = [self.getSequence(dim) for dim in range(1, 4)]
        self.periods =[self.getPeriod(dim) for dim in range(1, 4)]
        self.positions = [[self.getPosition(t, dim) for t in range(0, self.periods[dim - 1] + 1)] for dim in range(1, 4)]

    def getSequence(self, dim):
        base = int(pow(2, dim))
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

    def getPeriod(self, dim):
        base = int(pow(2, dim))
        p = 1
        reminder = 1
        while True:
            reminder = (reminder * base) % self.n
            if reminder == 1:
                break
            p = p + 1
        return p

    def getPosition(self, t, dim=1):
        (digits, _) = self.sequences[dim - 1]
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

    def period(self, dim=1):
        return self.periods[dim - 1]

    def path(self, dim=1):
        digits = self.sequences[dim - 1][0]
        return ''.join([str(d) for d in digits])

    def reminders(self, dim=1):
        return self.sequences[dim - 1][1]

    def position(self, t, dim=1):
        rt = 0
        px = 0.0
        py = 0.0
        pz = 0.0
        nt = int(t / self.periods[dim - 1])
        for rt in range(nt):
            x, y, z = self.positions[dim - 1][self.periods[dim - 1]]
            px += x
            py += y
            pz += z
        if t % self.periods[dim - 1] != 0:
            x, y, z = self.positions[dim - 1][t % self.periods[dim - 1]]
            px += x
            py += y
            pz += z
        if dim == 1:
            return (px, )
        elif dim == 2:
            return px, py
        return px, py, pz

    def digit(self, t, dim=1):
        digits = self.sequences[dim - 1][0]
        T = len(digits)
        return digits[t % T]


if __name__ == '__main__':
    r = Rational(85, 85)
    print r.getPeriod(2)
    print r.path(2)
    for t in range(19):
        print t, r.position(t, 2)
