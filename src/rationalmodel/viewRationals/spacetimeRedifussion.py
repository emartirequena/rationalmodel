from rationals import Rational, c
import random


class Cell(object):
	def __init__(self, dim, x, y=0, z=0):
		self.dim = dim
		self.x = x
		self.y = y
		self.z = z
		self.count = 0

	def add(self):
		self.count += 1

	def get(self):
		pos = (self.x, )
		if self.dim > 1:
			pos = pos + (self.y, )
		if self.dim > 2:
			pos = pos + (self.z, )
		out = {
			'pos': pos,
			'count': self.count
		}
		return out


class Space(object):
	def __init__(self, t, dim):
		self.t = t
		self.dim = dim
		self.base = 2**dim
		self.cells = []
		if self.dim == 1:
			for nx in range(t + 1):
				x = c * t - nx
				self.cells.append(Cell(dim, x))
		elif self.dim == 2:
			for ny in range(t + 1):
				y = c * t - ny
				for nx in range(t + 1):
					x = c * t - nx
					self.cells.append(Cell(dim, x, y))
		elif self.dim == 3:
			for nz in range(t + 1):
				z = c * t - nz
				for ny in range(t + 1):
					y = c * t - ny
					for nx in range(t + 1):
						x = c * t - nx
						self.cells.append(Cell(dim, x, y, z))

	def getCell(self, x, y=0.0, z=0.0):
		nx = c * self.t - x
		ny = c * self.t - y if self.dim > 1 else 0.0
		nz = c * self.t - z if self.dim > 2 else 0.0
		n = nx + (self.t + 1) * (ny + (self.t + 1) * nz)
		return self.cells[int(n)]

	def add(self, x, y=0.0, z=0.0):
		self.getCell(x, y, z).add()


class SpaceTime(object):
	def __init__(self, T, max, dim=1):
		self.T = T
		self.max = max
		self.dim = dim
		self.base = 2**dim
		self.spaces = [Space(t, dim) for t in range(max + 1)]
		self.rationalSet = []

	def add(self, t, x, y=0, z=0):
		self.spaces[t].add(x, y, z)

	def getCell(self, t, x, y=0, z=0):
		return self.spaces[t].getCell(x, y, z)

	def setRationalSet(self, n):
		self.rationalSet = []
		for m in range(n + 1):
			self.rationalSet.append(Rational(m, n, self.dim))

	def addRational(self, r, t, x=0, y=0, z=0):
		for rt in range(0, self.T + 1):
			if t + rt > self.max:
				return
			pos = r.position(rt)
			pos = list(pos)
			pos[0] += x
			if self.dim > 1:
				pos[1] += y
			if self.dim > 2:
				pos[2] += z
			self.spaces[t + rt].add(*pos)
		if t + rt < self.max:
			self.addRationalSet(t + rt, *pos)
	
	def addRationalSet(self, t=0, x=0, y=0, z=0):
		for r in self.rationalSet:
			self.addRational(r, t, x, y, z)

	def addRationalShift(self, m, n):
		r = Rational(m, n)
		reminders = r.reminders(dim=self.dim)
		for reminder in reminders:
			self.addRational(Rational(reminder, n, self.dim), 0)

	def addRationalRandom(self, n, num):
		s = range(n + 1)
		for _ in range(num):
			m = random.choice(s)
			s.remove(m)
			r = Rational(m, n, self.dim)
			self.addRational(r, 0)
