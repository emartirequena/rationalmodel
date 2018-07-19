from rationals import Rational, c


class Cell(object):
	def __init__(self, space, x, y=0, z=0):
		self.space = space
		self.x = x
		self.y = y
		self.z = z
		self.num = 0
		self.counts = [0 for _ in range(8)]

	def getNum(self):
		return self.num

	def getCount(self, digit):
		return self.counts[digit]

	def addDigit(self, digit):
		self.num += 1
		self.counts[digit] += 1


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
		ny = c * self.t - y
		nz = c * self.t - z
		n = int(nx + self.t * (ny + self.t * nz))
		print self.t, x, y, z, nx, ny, nz, n
		return self.cells[n]

	def addDigit(self, digit, x, y=0.0, z=0.0):
		self.getCell(x, y, z).addDigit(digit)

	def getCount(self, digit, x, y=0.0, z=0.0):
		return self.getCell(x, y, z).getCount(digit)


class SpaceTime(object):
	def __init__(self, T, dim=1):
		self.T = T
		self.dim = dim
		self.spaces = [Space(t, dim) for t in range(T + 1)]

	def addDigit(self, digit, t, x, y=0, z=0):
		self.spaces[t].addDigit(digit, x, y, z)

	def getCell(self, t, x, y=0, z=0):
		return self.spaces[t].getCell(x, y, z)

	def addRational(self, r):
		for t in range(self.T + 1):
			pos = r.position(t, self.dim)
			digit = r.digit(t, self.dim)
			self.spaces[t].addDigit(digit, *pos)

	def addRationalSet(self, n):
		for m in range(n + 1):
			r = Rational(m, n)
			self.addRational(r)


if __name__ == '__main__':
	r = Rational(1, 27)
	spacetime = SpaceTime(r.period(), 1)
	spacetime.addRationalSet(27)

	cell = spacetime.getCell(18, 0)
	print cell.getCount(0), cell.getCount(1)
