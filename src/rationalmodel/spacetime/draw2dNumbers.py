import os
from spacetime import SpaceTime
from rationals import c
from utils import divisors
from svg.drawing import Drawing, Viewbox

basePath = r'C:\Users\emart\OneDrive\Documentos\Enrique\Proyectos\spacetime'


def draw2dNumber(T, n, fname):
	spacetime = SpaceTime(T, T, dim=2)
	spacetime.setRationalSet(n)
	spacetime.addRationalSet()
	space = spacetime.spaces[T]

	max = -1
	for i in range(len(space.cells)):
		cell = space.cells[i].get()
		num = cell['count']
		if num > max:
			max = num

	drawing = Drawing(
		fname,
		1000, 1000,
		Viewbox(-c*T, -c*T, T, T),
		margin=2
	)
	drawing.setFill(0, 0, 0)
	drawing.setStrokewidth(0.0)

	for i in range(len(space.cells)):
		cell = space.cells[i].get()
		num = cell['count']
		if num == 0:
			continue
		x, y = cell['pos']
		rad = 0.5*num/float(max)
		if rad < 0.01:
			rad = 0.01
		drawing.drawCircle(x, y, rad)

	drawing.saveImage(fname)


def draw2dSpace(T, nt, n, fname):
    print ('Computing spacetime...')
    spacetime = SpaceTime(T, nt, dim=2)
    spacetime.setRationalSet(n)
    spacetime.addRationalSet()

    for t in range(0, nt+1):
        print (t)
        space = spacetime.spaces[t]

        max = -1
        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num > max:
                max = num

        drawing = Drawing(
            fname,
            1000, 1000,
            Viewbox(-c*t, -c*t, t, t),	
            margin=2
        )
        drawing.setFill(0, 0, 0)
        drawing.setStrokewidth(0.0)

        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num == 0:
                continue
            x, y = cell['pos']
            rad = 0.5*num/float(max)
            if rad < 0.01:
                rad = 0.01
            drawing.drawCircle(x, y, rad)

        drawing.saveImage(os.path.join(fname, '{0}.{1:04d}.png'.format(n, t)))

def save2dNumber(T, n, fname):
	spacetime = SpaceTime(T, dim=2)
	spacetime.addRationalSet(n)
	space = spacetime.spaces[T]

	with open(fname, 'wt') as fp:
		for i in range(len(space.cells)):
			cell = space.cells[i].get()
			num = cell['count']
			if num == 0:
				continue
			x, y = cell['pos']
			fp.write('{0:5.2f} {1:5.2f} {2:6.0f}\n'.format(x, y, num))


def drawPeriod(T):
	T = 11
	path = os.path.join(basePath, 'T{0:02d}'.format(T))
	if not os.path.exists(path):
		os.mkdir(path)
	nums = divisors(4**T-1)
	for num in nums[1:]:
		print (num)
		draw2dNumber(T, num, os.path.join(path, '{0}_{1}.jpg'.format(T, num)))


def drawNumber(num, T, nt):
	path = os.path.join(basePath, 'NN{0:02d}'.format(num))
	if not os.path.exists(path):
		os.mkdir(path)
	draw2dSpace(T, nt, num, path)


if __name__ == '__main__':
	# T = 11
	# path = os.path.join(basePath, 'T{0:02d}'.format(T))
	# if not os.path.exists(path):
	# 	os.mkdir(path)
	# nums = divisors(4**T-1)
	# for num in nums[1:]:
	# 	print num
	# 	draw2dNumber(T, num, os.path.join(path, '{0}_{1}.jpg'.format(T, num)))
	# num = 4194303
	# T = 11
	# path = os.path.join(basePath, 'T{0:02d}'.format(T))
	# draw2dNumber(T, num, os.path.join(path, '{0}_{1}.jpg'.format(T, num)))
	# save2dNumber(12, 197379, r'C:\Users\emart\OneDrive\Documentos\Enrique\Proyectos\Cuadros\data\C009\pedroNieto\12_197379.txt')
	# num = 127
	# path = os.path.join(basePath, 'NN{0:02d}'.format(num))
	# if not os.path.exists(path):
	# 	os.mkdir(path)
	# draw2dSpace(7, 28, num, path)
	drawNumber(87, 14, 42)
