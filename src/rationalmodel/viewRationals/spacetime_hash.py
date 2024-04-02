from multiprocessing import Pool, cpu_count, Pipe
import json
import gc
import numpy as np

from rationals import Rational, c
from timing import timing
from config import Config


spacetime = None


def eq_digits(q: str, r: str):
	l = len(q)
	for i in range(l):
		if q == r[i:] + r[:i-l]:
			return True
	return False


class HashRationalsItem:
	def __init__(self, min, max):
		self.min = min
		self.max = max
		self.rationals = []
		self.indexes = {}

	def __del__(self):
		del self.rationals
		del self.indexes

	def add(self, m, reminders, digits, time):
		if not self.min <= m <= self.max:
			return False
		
		if m not in self.indexes:
			self.rationals.append({
				'm': [m],
				'digits': digits,
				'count': 1,
				'time': time
			})
			i = len(self.rationals) - 1
			for r in reminders:
				self.indexes[r] = i
		elif m not in self.rationals[self.indexes[m]]['m']:
			self.rationals[self.indexes[m]]['m'].append(m)
			self.rationals[self.indexes[m]]['count'] += 1

		return True


class HashRationals:
	def __init__(self, num, size=100000):
		self.hash: list[HashRationalsItem] = []
		for i in range(0, num, size):
			self.hash.append(HashRationalsItem(i, i+size-1))

	def __del__(self):
		del self.hash

	def add(self, m, reminders, digits, time):
		for item in self.hash:
			if item.add(m, reminders, digits, time):
				return True
	
	def get_rationals(self):
		rationals = []
		for item in self.hash:
			rationals += item.rationals
		return rationals


class Cell(object):
	def __init__(self, dim, T, n, x, y=0, z=0):
		self.dim = dim
		self.T = T
		self.n = n
		self.x = x
		self.y = y
		self.z = z
		self.count = 0
		self.time = 0.0
		self.next_digits = dict(zip([x for x in range(2**self.dim)], [0 for _ in range(2**self.dim)]))
		self.rationals = HashRationals(self.n)

	def __del__(self):
		del self.next_digits
		del self.rationals

	def add(self, time: int, reminders: list[int], digits: str, m: int, next_digit: int):
		self.count += 1
		self.time += time
		self.next_digits[next_digit] += 1
		self.rationals.add(m, reminders, digits, time)

	def clear(self):
		self.count = 0
		self.time = 0.0
		self.next_digits = dict(zip([x for x in range(2**self.dim)], [0 for _ in range(2**self.dim)]))
		self.rationals = HashRationals(self.n)

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
			'next_digits': self.next_digits,
			'rationals': self.rationals.get_rationals()
		}
		return out
	
	def set(self, count, time, next_digits, rationals):
		self.count = count
		self.time = time
		self.next_digits = dict(zip([x for x in range(2**self.dim)], [0 for _ in range(2**self.dim)]))
		for x in [x for x in range(2**self.dim)]:
			self.next_digits[x] = next_digits[str(x)]
		self.rationals = HashRationals(self.n)
		for rational in rationals:
			for m in rational['m']:
				self.rationals.add(m, rational['m'], rational['digits'], rational['time'])


class Bbox:
	def __init__(self, bmin: np.array, bmax: np.array):
		self.min = bmin
		self.max = bmax

	def get_subbox(self, index: str):
		centre = (self.min + self.max) * 0.5
		dist =   (self.max - self.min) * 0.5
		delta = np.array([0., 0., 0.])
		for i in range(3):
			if index[i] == '1':
				delta[i] = -dist[i]
		bmin = centre   + delta
		bmax = self.max + delta
		return Bbox(bmin, bmax)

	def inside(self, point: np.array):
		if self.min[0] <= point[0] <= self.max[0] and\
		   self.min[1] <= point[1] <= self.max[1] and\
		   self.min[2] <= point[2] <= self.max[2]:
			return True
		return False
	
	def __str__(self) -> str:
		return f'({self.min}, {self.max})'

	def __repr__(self) -> str:
		return f'bbox({self.min}, {self.max})'


class OctTreeItem:
	def __init__(self, dim: int, t: int, level: int, max_level: int, bbox: Bbox):
		self.dim = dim
		self.cells_indexes: list[int] = []
		self.bbox: Bbox = bbox
		self.children: list[OctTreeItem] = []
		self.level = level
		if level == max_level or level == t:
			return
		if self.dim == 1:
			z = 0
			y = 0
			for x in range(2):
				bbox = self.bbox.get_subbox(f'{x}{y}{z}')
				self.children.append(OctTreeItem(dim, t, level+1, max_level, bbox))
		elif self.dim == 2:
			z = 0
			for y in range(2):
				for x in range(2):
					bbox = self.bbox.get_subbox(f'{x}{y}{z}')
					self.children.append(OctTreeItem(dim, t, level+1, max_level, bbox))
		elif self.dim == 3:
			for z in range(2):
				for y in range(2):
					for x in range(2):
						bbox = self.bbox.get_subbox(f'{x}{y}{z}')
						self.children.append(OctTreeItem(dim, t, level+1, max_level, bbox))

	def __del__(self):
		del self.cells_indexes
		del self.bbox
		del self.children

	def get_cell(self, cells: list[Cell], dim, T, n, t, x, y=0, z=0) -> Cell | None:
		if not self.bbox.inside(np.array([x, y, z])):
			return None

		if not self.children:
			found_cell = None
			for index in self.cells_indexes:
				cell = cells[index]
				d = np.array([cell.x, cell.y, cell.z]) - np.array([x, y, z])
				if np.linalg.norm(d) < 0.1:
					found_cell = cell
					break
			if found_cell:
				return found_cell
			cell = Cell(dim, T, n, x, y, z)
			cells.append(cell)
			self.cells_indexes.append(len(cells) - 1)
			return cell

		else:
			for child in self.children:
				cell = child.get_cell(cells, dim, T, n, t, x, y, z)
				if cell:
					return cell

		return None
	
	def clear(self):
		self.cells_indexes = []
		for child in self.children:
			child.clear()


class OctTree:
	def __init__(self, dim: int, t: int, max_levels: int, bbox: Bbox) -> None:
		self.bbox = bbox
		self.root = OctTreeItem(dim, t, 0, max_levels, self.bbox)

	def __del__(self):
		del self.root
	
	def get_cell(self, cells: list[Cell], dim, T, n, t, x, y=0, z=0) -> Cell:
		return self.root.get_cell(cells, dim, T, n, t, x, y, z)
	
	def clear(self):
		self.root.clear()


class Space(object):
	def __init__(self, t, dim, T, n, max, name='normal'):
		self.t = t
		self.T = T
		self.n = n
		self.dim = dim
		self.name = name
		self.base = 2**dim
		self.cells: list[Cell] = []
		d = max * 0.5
		if dim == 1: bbox = Bbox(np.array([-d,  0,  0]), np.array([d, 0, 0]))
		if dim == 2: bbox = Bbox(np.array([-d, -d,  0]), np.array([d, d, 0]))
		if dim == 3: bbox = Bbox(np.array([-d, -d, -d]), np.array([d, d, d]))
		config = Config()
		max_octtree_levels = config.get('max_octtree_levels')	
		self.hash_tree = OctTree(dim, t, max_octtree_levels, bbox)

	def __del__(self):
		del self.cells
		del self.hash_tree

	def getCell(self, x, y=0.0, z=0.0) -> Cell:
		return self.hash_tree.get_cell(self.cells, self.dim, self.T, self.n, self.t, x, y, z)

	def countCells(self):
		l = 0
		for cell in self.cells:
			if cell.count > 0:
				l += 1
		return l

	def getCells(self) -> list[Cell]:
		return self.cells

	def add(self, time, reminders, digits, m, next_digit, x, y, z):
		cell = self.getCell(x, y, z)
		if not cell:
			return
		cell.add(time, reminders, digits, m, next_digit)

	def clear(self):
		self.cells = []
		self.hash_tree.clear()

	def save(self):
		objs = []
		for cell in self.cells:
			objs.append(cell.get())
		return objs
	
	def load(self, input: list[dict]):
		self.clear()
		for in_cell in input:
			cell = self.getCell(*in_cell['pos'])
			cell.set(in_cell['count'], in_cell['time'], in_cell['next_digits'], in_cell['rationals'])


class Spaces:
	def __init__(self, T, n, max, dim=1) -> None:
		self.T = T
		self.n = n
		self.max = max
		self.dim = dim
		self.spaces = [Space(t, dim, T, n, max) for t in range(max + 1)]
		self.accumulates_even = Space(max if T%2 == 0 else max-1, dim, T, n, max, name='even')
		self.accumulates_odd  = Space(max if T%2 == 1 else max-1, dim, T, n, max, name='odd' )

	def __del__(self):
		del self.spaces
		del self.accumulates_even
		del self.accumulates_odd

	def add(self, is_special, t, reminders, digits, m, next_digit, time, cycle, x, y, z):
		self.spaces[t].add(time, reminders, digits, m, next_digit, x, y, z)
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
			self.accumulates_even.add(time, reminders, digits, m, next_digit, x, y, z)
		else:
			self.accumulates_odd.add(time, reminders, digits, m, next_digit, x, y, z)

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


def add_rational(args):
	conn, max, r, t, x, y, z = args
	r: Rational = args[2]
	for rt in range(0, max + 1):
		px, py, pz = r.position(rt)
		px += x
		py += y
		pz += z
		reminders = r.reminders
		digits = r.path()
		m = r.m
		next_digit = r.digit(t+rt+1)
		time = r.time(t+rt)
		obj = (t+rt, reminders, digits, m, next_digit, time, px, py, pz)
		conn.send(obj)
	conn.send(None)


class SpaceTime(object):
	def __init__(self, T, n, max, dim=1):
		self.T = T
		self.max = max
		self.dim = dim
		self.n = n
		self.is_special = False
		self.spaces = Spaces(T, n, max, dim)
		self.rationalSet = []

	def __del__(self):
		del self.spaces
		del self.rationalSet
		gc.collect()

	def len(self):
		return self.max

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
	
	def add(self, r: Rational, t, x, y, z):
		for rt in range(0, self.max + 1):
			px, py, pz = r.position(rt)
			px += x
			py += y
			pz += z
			reminders = r.reminders
			digits = r.path()
			m = r.reminder(t+rt)
			next_digit = r.digit(t+rt+1)
			time = r.time(t+rt)
			self.spaces.add(self.is_special, t+rt, reminders, digits, m, next_digit, time, self.T, px, py, pz)
	
	@timing
	def setRationalSet(self, n: int, is_special: bool = False):
		self.n = n
		self.is_special = is_special
		p = Pool(cpu_count())
		params = []
		for m in range(n + 1):
			params.append((m, n, self.dim))

		unordered_set = p.imap(func=create_rational, iterable=params, chunksize=10000)
		p.close()
		p.join()

		self.rationalSet = list(sorted(unordered_set, key=lambda x: x.m))
		del unordered_set
		gc.collect()

	@timing
	def addRationalSet(self, t=0, x=0, y=0, z=0, count_rationals=True):
		# conn1, conn2 = Pipe()
		# p = Pool(cpu_count())
		# params = []
		# for r in self.rationalSet:
		# 	params.append((conn1, self.max, r, t, x, y, z))
		# p.imap(func=add_rational, iterable=params, chunksize=100000)

		# count = 0
		# while True:
		# 	obj = conn2.recv()
		# 	if obj is None:
		# 		count += 1
		# 	else:
		# 		t, reminders, path, m, next_digit, time, px, py, pz = obj
		# 		self.spaces.add(self.is_special, t, reminders, path, m, next_digit, time, self.T, px, py, pz)
		# 	if count == len(params):
		# 		break

		# p.close()
		# p.join()

		for r in self.rationalSet:
			self.add(r, t, x, y, z)

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

		self.__init__(content['T'], content['num'], content['max'], content['dim'])
		self.is_special = content['special']
		self.spaces.load(content['spaces'])


if __name__ == '__main__':
	dim = 1
	T = 6
	# n = (2**dim)**int(T // 2) + 1
	n = 63
	print('Creating spacetime...')
	spacetime = SpaceTime(T, n, T, dim=dim)
	print(f'Set rational set for n={n}...')
	spacetime.setRationalSet(n, is_special=True)
	print('Add rational set...')
	spacetime.addRationalSet()
	print(f'Save test_1D_N{n}.json...')
	spacetime.save(f'test_1D_N{n}.json')
	print(f'Load test_1D_N{n}.json...')
	spacetime.load(f'test_1D_N{n}.json')
