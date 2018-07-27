from src.racionales.utils import divisors

from rationals import Rational, c
from math import pow


class Cell(object):
	def __init__(self, space, x, y=0, z=0):
		self.space = space
		self.x = x
		self.y = y
		self.z = z
		base = int(pow(2, space.dim))
		self.input = [0 for _ in range(base)]
		self.output = [0 for _ in range(base)]

	def addInput(self, digit):
		self.input[digit] += 1

	def addOutput(self, digit):
		self.output[digit] += 1

	def getInput(self, digit):
		return self.input[digit]

	def getOutput(self, digit):
		return self.output[digit]

	def get(self):
		pos = (self.x, )
		if self.space.dim > 1:
			pos = pos + (self.y, )
		if self.space.dim > 2:
			pos = pos + (self.z, )
		out = {
			'pos': pos,
			'input': self.input,
			'output': self.output
		}
		return out


class Space(object):
	def __init__(self, t, dim):
		self.t = t
		self.dim = dim
		self.cells = []
		if self.dim == 1:
			for n in range(t + 1):
				x = c * t - n
				self.cells.append(Cell(self, x))
		elif self.dim == 2:
			for ny in range(t + 1):
				y = c * t - ny
				for nx in range(t + 1):
					x = c * t - nx
					self.cells.append(Cell(self, x, y))
		elif self.dim == 3:
			for nz in range(t + 1):
				z = c * t - nz
				for ny in range(t + 1):
					y = c * t - ny
					for nx in range(t + 1):
						x = c * t - nx
						self.cells.append(Cell(self, x, y, z))

	def getCell(self, x, y=0.0, z=0.0):
		nx = c * self.t - x
		ny = c * self.t - y if self.dim > 1 else 0
		nz = c * self.t - z if self.dim > 2 else 0
		n = int(nx + self.t * (ny + self.t * nz))
		return self.cells[n]

	def addInput(self, digit, x, y=0.0, z=0.0):
		self.getCell(x, y, z).addInput(digit)

	def addOutput(self, digit, x, y=0.0, z=0.0):
		self.getCell(x, y, z).addOutput(digit)


class SpaceTime(object):
	def __init__(self, T, dim=1):
		self.T = T
		self.dim = dim
		self.spaces = [Space(t, dim) for t in range(T + 1)]

	def addInput(self, digit, t, x, y=0, z=0):
		self.spaces[t].addInput(digit, x, y, z)

	def addOutput(self, digit, t, x, y=0, z=0):
		self.spaces[t].addOutput(digit, x, y, z)

	def getCell(self, t, x, y=0, z=0):
		return self.spaces[t].getCell(x, y, z)

	def addRational(self, r):
		digit = 0
		for t in range(self.T + 1):
			pos = r.position(t, self.dim)
			self.spaces[t].addInput(digit, *pos)
			digit = r.digit(t, self.dim)
			self.spaces[t].addOutput(digit, *pos)

	def addRationalSet(self, n):
		for m in range(n + 1):
			r = Rational(m, n)
			self.addRational(r)

	def addRationalShift(self, m, n):
		r = Rational(m, n)
		reminders = r.reminders(dim=1)
		for reminder in reminders:
			self.addRational(Rational(reminder, n))


def testRationalSet1D(T):
	n = int(pow(2, T) - 1)
	divs = divisors(n)
	for div in divs:
		print 'divisor', div, 'period', Rational(1, div).period()
		spacetime = SpaceTime(T, 1)
		spacetime.addRationalSet(div)

		dx = 1
		for t in range(T + 1):
			print t
			x = t * (c - 1)
			for _ in range(t + 1):
				cell = spacetime.getCell(t, x)
				dic = cell.get()
				flow = [(dic['output'][i] - dic['input'][i]) for i in range(2)]
				print dic['pos'], flow
				x += dx

		print ' '


def testNonRationalSet():
	spacetime = SpaceTime(6, 1)
	spacetime.addRationalShift(1, 63)
	spacetime.addRationalShift(62, 63)
	spacetime.addRationalShift(5, 63)
	spacetime.addRationalShift(58, 63)
	spacetime.addRationalShift(11, 63)
	spacetime.addRationalShift(13, 63)

	T = 6
	dx = 1
	for t in range(T + 1):
		print t
		x = t * (c - 1)
		for _ in range(t + 1):
			cell = spacetime.getCell(t, x)
			dic = cell.get()
			flow = [(dic['output'][i] - dic['input'][i]) for i in range(2)]
			print dic['pos'], flow, dic['input'], dic['output']
			x += dx

	print ' '


if __name__ == '__main__':
	testNonRationalSet()
