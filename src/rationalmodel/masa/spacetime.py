import os
from multiprocessing import Pool, cpu_count, Pipe
import json
import gc

from rationals import Rational, c
from utils import timing


spacetime = None


class Cell(object):
	def __init__(self, dim, x, y=0, z=0):
		self.dim = dim
		self.x = x
		self.y = y
		self.z = z
		self.count = 0
		self.time = 0.0
		self.next_digits = dict(zip([x for x in range(2**self.dim)], [0 for _ in range(2**self.dim)]))

	def add(self, time, next_digit):
		self.count += 1
		self.time += time
		self.next_digits[next_digit] += 1

	def clear(self):
		self.count = 0
		self.time = 0.0

	def get(self):
		pos = (self.x, )
		if self.dim > 1:
			pos = pos + (self.y, )
		if self.dim > 2:
			pos = pos + (self.z, )
		out = {
			'pos': pos,
			'count': self.count,
			'time': self.time / float(self.count),
			'next_digits': self.next_digits
		}
		return out
	
	def set(self, count, time):
		self.count = count
		self.time = time


class Space(object):
	def __init__(self, t, dim, name='normal'):
		self.t = t
		self.dim = dim
		self.name = name
		self.base = 2**dim
		self.cells: list[Cell] = []
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

	def __del__(self):
		del self.cells

	def getCell(self, x, y=0.0, z=0.0):
		nx = c * self.t - x
		ny = (c * self.t - y) if self.dim > 1 else 0.0
		nz = (c * self.t - z) if self.dim > 2 else 0.0
		n = int(nx + (self.t + 1) * (ny + (self.t + 1) * nz))
		if n >= len(self.cells):
			return None
		return self.cells[int(n)]
	
	def getCells(self):
		return list(filter(lambda x: x.count > 0, self.cells))

	def add(self, time, next_digit, x, y=0.0, z=0.0):
		cell = self.getCell(x, y, z)
		if not cell:
			return
		cell.add(time, next_digit)

	def clear(self):
		for cell in self.cells:
			cell.clear()

	def save(self):
		objs = []

		view_cells = list(filter(lambda x: x.count != 0, self.cells))
		for cell in view_cells:
			objs.append(cell.get())

		del view_cells
		gc.collect()

		return objs
	
	def load(self, input: list[dict]):
		for in_cell in input:
			cell = self.getCell(*in_cell['pos'])
			cell.set(in_cell['count'], in_cell['time'])


class Spaces:
	def __init__(self, T, max, dim=1) -> None:
		self.T = T
		self.max = max
		self.dim = dim
		self.spaces = [Space(t, dim) for t in range(max + 1)]
		if 9 <= T <= 15:
			self.accumulates_even = Space(max if T%2 == 0 else max-1, dim, name='even')
			self.accumulates_odd = Space(max if T%2 == 1 else max-1, dim, name='odd')
		else:
			self.accumulates_even = Space(max if T%2 == 0 else max, dim, name='even')
			self.accumulates_odd = Space(max+1 if T%2 == 1 else max-1, dim, name='odd')

	def __del__(self):
		del self.spaces

	def add(self, is_special, t, next_digit, cycle, time, x, y=0, z=0):
		self.spaces[t].add(time, next_digit, x, y, z)
		if t < self.max - cycle and is_special:
			return
		if self.dim == 1:
			if (x == t * c or x == -t * c) and is_special:
				return
		elif self.dim == 2:
			if (x == y == t * c or x == y == -t * c) and is_special:
				return
		else:
			if (x == y == z == t * c or x == y == z == -t * c) and is_special:
				return
		if t%2 == 0:
			self.accumulates_even.add(time, next_digit, x, y, z)
		else:
			self.accumulates_odd.add(time, next_digit, x, y, z)

	def clear(self):
		for space in self.spaces:
			space.clear()
		self.accumulates_even.clear()
		self.accumulates_odd.clear()

	def getCell(self, t, x, y=0, z=0, accumulate=False):
		if not accumulate:
			return self.spaces[t].getCell(x, y, z)
		else:
			if t%2 == 0:
				return self.accumulates_even.getCell(x, y, z)
			else:
				return self.accumulates_odd.getCell(x, y, z)
			
	def getCells(self, t, accumulate=False):
		if not accumulate:
			return self.spaces[t].getCells()
		else:
			if t%2 == 0:
				return self.accumulates_even.getCells()
			else:
				return self.accumulates_odd.getCells()

	def getSpace(self, t, accumulate=False):
		if not accumulate:
			return self.spaces[t]
		else:
			if t%2 == 0:
				return self.accumulates_even
			else:
				return self.accumulates_odd

	def save(self):
		output = {}
		for t in range(self.max + 1):
			space = self.getSpace(t, accumulate=False)
			out_cells = space.save()
			output[str(t)] = out_cells
		output['accumulates_even'] = self.accumulates_even.save()
		output['accumulates_odd'] = self.accumulates_odd.save()
		return output
	
	def load(self, input: dict):
		for t in range(self.max + 1):
			space = self.getSpace(t)
			space.load(input[str(t)])
		self.accumulates_even.load(input['accumulates_even'])
		self.accumulates_odd.load(input['accumulates_odd'])


def create_rational(args):
	m, n, dim = args
	return Rational(m, n, dim)


class SpaceTime(object):
	def __init__(self, T, max, dim=1):
		self.T = T
		self.max = max
		self.dim = dim
		self.n = 0
		self.is_special = False
		self.spaces = Spaces(T, max, dim)
		self.rationalSet = []

	def __del__(self):
		del self.spaces
		del self.rationalSet
		gc.collect()

	def len(self):
		return self.max

	def add(self, is_special, t, next_digit, time, x, y=0, z=0):
		self.spaces.add(is_special, t, next_digit, T, time, x, y , z)

	def clear(self):
		self.n = 0
		self.is_special = False
		self.spaces.clear()

	def getCell(self, t, x, y=0, z=0, accumulate=False):
		return self.spaces.getCell(t, x, y, z, accumulate)

	def getCells(self, t, accumulate=False):
		return self.spaces.getCells(t, accumulate)
	
	def getSpace(self, t, accumulate=False):
		return self.spaces.getSpace(t, accumulate)
	
	@timing
	def setRationalSet(self, n: int, is_special: bool = False):
		self.n = n
		self.is_special = is_special
		p = Pool(cpu_count())
		params = []
		for m in range(n + 1):
			params.append((m, n, self.dim))

		unordered_set = p.imap(func=create_rational, iterable=params, chunksize=1000)
		p.close()
		p.join()

		self.rationalSet = list(sorted(unordered_set, key=lambda x: x.m))
		del unordered_set
		gc.collect()

	def add_rational(self, r, t, x, y, z, is_special):
		for rt in range(self.max + 1):
			pos = list(r.position(rt))
			pos[0] += x
			if self.dim > 1:
				pos[1] += y
			if self.dim > 2:
				pos[2] += z
			time = r.time(t+rt)
			next_digit = r.digit(t+rt+1)
			self.spaces.add(is_special, t+rt, next_digit, self.T, time, *pos)

	@timing
	def addRationalSet(self, is_special=False, t=0, x=0, y=0, z=0):
		for r in self.rationalSet:
			self.add_rational(r, t, x, y, z, is_special)

	@timing
	def save(self, fname):
		spaces = self.spaces.save()
		output = {
			'dim': self.dim,
			'num': self.n,
			'special': self.is_special,
			'T': self.T,
			'max': self.max,
			'spaces': spaces
		}

		with open(fname, 'wt') as fp:
			json.dump(output, fp, indent=4)

	@timing
	def load(self, fname):
		with open(fname, 'rt') as fp:
			content = json.load(fp)

		self.__init__(content['T'], content['max'], content['dim'])
		self.n = content['num']
		self.is_special = content['special']
		self.spaces.load(content['spaces'])


if __name__ == '__main__':
	dim = 1
	T = 20
	n = (2**dim)**int(T) - 1
	# n = 205
	print('Creating spacetime...')
	spacetime = SpaceTime(T, T, dim=dim)
	print(f'Set rational set for n={n}...')
	spacetime.setRationalSet(n, is_special=False)
	print('Add rational set...')
	spacetime.addRationalSet()
	print(f'Save test_1D_N{n}.json...')
	spacetime.save(f'test_1D_N{n}.json')
	print(f'Load test_1D_N{n}.json...')
	spacetime.load(f'test_1D_N{n}.json')
	print(len(list(filter(lambda x: x.count != 0, spacetime.spaces.getCells(T, accumulate=False)))))
