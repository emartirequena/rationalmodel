import os
from multiprocessing import Pool, cpu_count, Pipe
import json
import gc

from rationals import Rational, c
from config import Config
from utils import timing


spacetime = None


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

	def __del__(self):
		del self.cells

	def getCell(self, x, y=0.0, z=0.0):
		nx = c * self.t - x
		ny = (c * self.t - y) if self.dim > 1 else 0.0
		nz = (c * self.t - z) if self.dim > 2 else 0.0
		n = nx + (self.t + 1) * (ny + (self.t + 1) * nz)
		return self.cells[int(n)]
	
	def getCells(self):
		return list(filter(lambda x: x.count != 0, self.cells))

	def add(self, x, y=0.0, z=0.0):
		self.getCell(x, y, z).add()

	def save_stats(self, fname):
		objs = {}
		view_cells = list(filter(lambda x: x.count != 0, self.cells))
		for cell in view_cells:
			key = cell.count
			if key not in objs: objs[key] = {
				'count': 0,
				'percent': 0.0
			}
			objs[key]['count'] += 1
		total = 0.0
		for key in objs.keys():
			obj = objs[key]
			total += float(obj['count'] * key)
		for key in objs.keys():
			obj = objs[key]
			obj['percent'] = 100. * float(key * obj['count']) / float(total)

		objs = dict(sorted(zip(objs.keys(), objs.values()), key=lambda x: int(x[0])))

		with open(fname, 'wt') as fp:
			json.dump(objs, fp, indent=4)

		del view_cells
		del objs
		gc.collect()

class Spaces:
	def __init__(self, T, max, dim=1) -> None:
		self.T = T
		self.max = max
		self.dim = dim
		self.spaces = [Space(t, dim) for t in range(max + 1)]
		self.accumulates_even = Space(max if T%2 == 0 else max-1, dim)
		self.accumulates_odd = Space(max if T%2 == 1 else max-1, dim)

	def __del__(self):
		del self.spaces

	def add(self, is_special, t, x, y=0, z=0):
		self.spaces[t].add(x, y, z)
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
			self.accumulates_even.add(x, y, z)
		else:
			self.accumulates_odd.add(x, y, z)

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

	def save_stats(self, t, fname, accumulate=False):
		space = self.getSpace(t, accumulate=accumulate)
		space.save_stats(fname)

def create_rational(args):
	m, n, dim = args
	return Rational(m, n, dim)


# def add_rational(args):
# 	conn, max, dim, r, t, x, y, z = args
# 	r = args[3]
# 	for rt in range(0, max + 1):
# 		pos = list(r.position(rt))
# 		pos[0] += x
# 		if dim > 1:
# 			pos[1] += y
# 		if dim > 2:
# 			pos[2] += z
# 		conn.send((t+rt, *pos))
# 	conn.send(None)


class SpaceTime(object):
	def __init__(self, T, max, dim=1):
		self.T = T
		self.max = max
		self.dim = dim
		self.spaces = Spaces(T, max, dim)
		self.rationalSet = []

	def __del__(self):
		del self.spaces
		del self.rationalSet
		gc.collect()

	def len(self):
		return self.max

	def add(self, is_special, t, x, y=0, z=0):
		self.spaces.add(t, is_special, x, y , z)

	def getCell(self, t, x, y=0, z=0, accumulate=False):
		return self.spaces.getCell(t, x, y, z, accumulate)

	@timing	
	def getCells(self, t, accumulate=False):
		return self.spaces.getCells(t, accumulate)
	
	def getSpace(self, t, accumulate=False):
		return self.spaces.getSpace(t, accumulate)

	def setRationalSet(self, n: int):
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

	def add_rational(self, r, t, x, y, z, accumulate, is_special):
		if accumulate and is_special:
			cycle = self.max // self.T
			begin = self.T * (cycle - 1)
			end = self.T * cycle + 1
		else:
			begin = 0
			end = self.max + 1
		for rt in range(begin, end):
			pos = list(r.position(rt))
			pos[0] += x
			if self.dim > 1:
				pos[1] += y
			if self.dim > 2:
				pos[2] += z
			self.spaces.add(is_special, t+rt, *pos)

	def addRationalSet(self, is_special=False, accumulate=False, t=0, x=0, y=0, z=0):
		# p = Pool(cpu_count())
		# params = []
		# connections = []
		# for r in self.rationalSet:
		# 	conn1, conn2 = Pipe()
		# 	connections.append((conn1, conn2))
		# 	params.append((conn1, self.max, self.dim, r, t, x, y, z))
		# p.imap(func=add_rational, iterable=params, chunksize=1000)
		# print('------ connections created...')

		# count = 0
		# while True:
		# 	for connection in connections:
		# 		conn1, conn2 = connection
		# 		obj = conn2.recv()
		# 		if obj is None:
		# 			count += 1
		# 		else:
		# 			t, x, y, z = obj
		# 			self.add(t, x, y, z)
		# 	if count == len(params):
		# 		break

		# p.close()
		# p.join()

		for r in self.rationalSet:
			self.add_rational(r, t, x, y, z, accumulate, is_special)

	def save_stats(self, t, fname, accumulate=False):
		self.spaces.save_stats(t, fname, accumulate=accumulate)


if __name__ == '__main__':
	print('Creating spacetime...')
	spacetime = SpaceTime(20, 40, dim=3)
	print('Setting rational set of 25...')
	spacetime.setRationalSet(25)
	print('Adding rational set...')
	spacetime.addRationalSet(is_special=True, accumulate=True)
	config = Config()
	spacetime.save_stats(40, os.path.join(config.get('image_path'), 'test.json'), accumulate=True)
