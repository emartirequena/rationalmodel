import svgwrite
from svgwrite import rgb
import os

root = r'C:\Users\enrique\Google Drive\Enrique\ArticuloRacionales\figuras'


class Rect(object):
	def __init__(self, x, y, width, height):
		self.x = x
		self.y = y
		self.width = width
		self.height = height

	def getViewbox(self, margin=0):
		x = self.x - margin
		y = self.y - margin
		width = self.width + 2 * margin
		height = self.height + 2 * margin
		output = '{:f} {:f} {:f} {:f}'.format(x, y, width, height)
		return output


class Drawing(object):
	def __init__(self, name, sizex, sizey, viewbox, margin=0):
		self.path = os.path.join(root, name)
		self.sizex = sizex
		self.sizey = sizey
		self.viewbox = viewbox
		self.margin = margin
		self.dwg = svgwrite.Drawing(
			self.path,
			size=('{}cm'.format(self.sizex), '{}cm'.format(self.sizey)),
			viewBox=viewbox.getViewbox(self.margin)
		)

		self.all = self.dwg.add(self.dwg.g(id='all'))
		self.groups = [self.all]

		self.all.scale(1, -1)

		dy = 0
		if self.viewbox.width > self.viewbox.height:
			dy = self.viewbox.y
		self.all.translate(0, dy)

		self.strokewidth = 0.1
		self.stroke = rgb(0, 0, 0, '%')
		self.fill = rgb(255, 255, 255, '%')
		self.dasharray = []

	def openGroup(self, name):
		group = self.groups[-1].add(self.dwg.g(id=name))
		self.groups.push(group)

	def closeGroup(self):
		if len(self.groups) > 1:
			self.groups.pop()

	def setStroke(self, r, g, b):
		self.stroke = rgb(r, g, b, '%')

	def setFill(self, r, g, b):
		self.fill = rgb(r, g, b, '%')

	def setDasharray(self, dasharray):
		self.dasharray = dasharray

	def setStrokewidth(self, width):
		self.strokewidth = width

	def drawLine(self, x1, y1, x2, y2):
		group = self.groups[-1]
		group.add(
			self.dwg.line(
				(x1, y1),
				(x2, y2),
				stroke=self.stroke,
				stroke_width=self.strokewidth,
				stroke_dasharray=self.dasharray
			)
		)

	def drawCircle(self, x, y, r):
		group = self.groups[-1]
		group.add(
			self.dwg.circle(
				center=(x, y),
				r=r,
				stroke_width=self.strokewidth,
				stroke=self.stroke,
				fill=self.fill
			)
		)

	def drawRect(self, x, y, width, height):
		group = self.groups[-1]
		group.add(
			self.dwg.rect(
				insert=(x, y),
				size=(width, height),
				stroke_width=self.strokewidth,
				stroke=self.stroke,
				fill=self.fill
			)
		)

	def save(self):
		self.dwg.save()


if __name__ == '__main__':
	drawing = Drawing(
		'test.svg',
		10, 10,
		Rect(-10, -3, 20, 10),
		margin=2
	)

	drawing.setStroke(0, 0, 255)
	drawing.drawRect(-10, -3, 20, 10)

	drawing.setStroke(255, 0, 0)
	drawing.drawRect(0, 0, 20, 20)
	drawing.drawCircle(0, 0, 1)

	drawing.save()
