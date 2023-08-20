from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from PIL import Image, ImageDraw
from madcad import vec3
import numpy as np

from config import Config
from color import ColorLine
from utils import lerp


class Item:
    def __init__(self, x: int, height: int, color: vec3) -> None:
        self.x = x
        self.height = height
        self.color = (
            int(255 * color.x), 
            int(255 * color.y), 
            int(255 * color.z)
        )


class Scene:
    def __init__(self, width: int, height: int) -> None:
        self.width: int = width
        self.height: int = height
        self.min_x = 0.
        self.max_x = 0.
        self.max_h = 0.
        self.ox: float = width / 2
        self.scl: float = 1.
        self.items: list[Item] = []

    def clear(self):
        self.items = []
        self.max_x = 0.
        self.max_h = 0.

    def add(self, x: int, height: int, color: vec3):
        self.items.append(Item(x, height, color))
        if x > self.max_x: self.max_x = x
        if height > self.max_h: self.max_h = height

    def scale(self, x: float, step: float):
        sox = self.ox * self.scl
        factor = 1.05 if step > 0. else 1./1.05
        self.scl *= factor
        self.ox = ((sox - x) * factor + x) / self.scl

    def fit(self):
        self.min_x =  10000000000
        self.max_x = -10000000000
        for item in self.items:
            if item.x < self.min_x: self.min_x = item.x
            if item.x > self.max_x: self.max_x = item.x
        if self.max_x != self.min_x:
            self.scl = self.width / (self.max_x - self.min_x)
            self.ox = -self.min_x - 0.5
        else:
            self.scl = self.width / self.max_x
            self.ox = 0.

    def translate(self, dist: float):
        self.ox += dist / self.scl

    @staticmethod
    def _loga(a, x):
        return np.log(x) / np.log(a)
    
    def _loga_round(self, a, x):
        return int(np.power(a, int(self._loga(a, x))))
    
    def _get_y_step_max(self):
        y_base = 10
        y_step = int(self._loga(y_base, self.max_h))
        y_step = y_step if y_step > 0 else 1
        y_max = np.power(y_base, y_step)
        return y_step, y_max

    def _render_grid(self, draw):
        colors = [(100, 100, 100), (200, 100, 0), (150, 150, 150), (255, 255, 0)]

        y_step, y_max = self._get_y_step_max()
        for y in range(0, y_max, y_step):
            color = colors[0]
            if y == y_max // 2: color = colors[1]
            h = np.power(y / y_max, 0.5) * self.height 
            draw.line((0, self.height - h, self.width, self.height - h), color, 1)

        x_base = 10
        x_step = self._loga_round(x_base, x_base * 10 / self.scl)
        x_step = x_step if x_step > 0 else 1
        x_max = x_step * np.power(x_base, 3)
        for x in range(-x_max, x_max, x_step):

            color = colors[0]
            if x == 0: color = colors[3]
            elif (x - x_max) % x_base == 0: color = colors[1]
            elif (x - x_max) % x_base == 5: color = colors[2]

            px = int((x + self.ox) * self.scl)
            w = 1 if np.abs(px) > 0.1 else 3
            draw.line((px, self.height, px, 0), color, w)

    def render(self):
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        self._render_grid(draw)
        _, y_max = self._get_y_step_max()
        for item in self.items:
            x = int((item.x + self.ox) * self.scl)
            h = np.power(item.height / y_max, 0.5) * self.height
            draw.line((x, self.height - h, x, self.height), (item.color), 3)

        draw.rectangle((0, 0, self.width-1, self.height-1), None, (255, 255, 255), 1)
        return img

    @staticmethod
    def _pil2pixmap(im):
        if im.mode == "RGB":
            r, g, b = im.split()
            im = Image.merge("RGB", (b, g, r))
        elif  im.mode == "RGBA":
            r, g, b, a = im.split()
            im = Image.merge("RGBA", (b, g, r, a))
        elif im.mode == "L":
            im = im.convert("RGBA")
        im2 = im.convert("RGBA")
        data = im2.tobytes("raw", "RGBA")
        qim = QtGui.QImage(data, im.size[0], im.size[1], QtGui.QImage.Format_ARGB32)
        pixmap = QtGui.QPixmap.fromImage(qim)
        return pixmap


class Histogram(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.spacetime = None
        self.time = 0
        if not parent:
            self.config = Config()
        else:
            self.config = parent.config
        self.resx = self.config.get('histogram_resx')
        self.resy = self.config.get('histogram_resy')
        self.hist_size = (self.resx, self.resy)
        self.hist_max = self.config.get('histogram_max')
        self.color = ColorLine()
        for knot in self.config.get('colors'):
            self.color.add(knot['alpha'], vec3(*knot['color']))

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
        self.setLayout(self.layout)

        self.view = None

        self.resize(self.resx, self.resy)
        if parent:
            pos = parent.central.pos()
            self.move(pos.x() + 15, pos.y() + 15)

        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor('gray'))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.scene = Scene(self.width(), self.height())
        self.scene.clear()
        # img = self.scene.render()
        self.label = QtWidgets.QLabel(self)
        # self.label.setPixmap(self.scene._pil2pixmap(img))
        self.layout.addWidget(self.label)
        
        self.old_pos = 0.

    def set_number(self, number):
        self.hist_max = int(number)

    def set_spacetime(self, spacetime):
        if self.spacetime is not spacetime:
            self.spacetime = spacetime
            self.change_flag = True
        else:
            self.change_flag = False

    def reset(self):
        img = self.scene.render()
        self.label.setPixmap(self.scene._pil2pixmap(img))
        self.show()
        self.update()

    def set_time(self, time):
        self.time = time
        self._make_items()
        if self.change_flag:
            self.scene.fit()
            self.change_flag = False
        self.reset()

    def _make_items(self):
        space = self.spacetime.spaces[self.time]

        dict_objs = {}

        count = 0
        max = -1
        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num:
                if num > max:
                    max = num
                if num not in dict_objs:
                    dict_objs[num] = 0
                dict_objs[num] += 1
                count += 1

        print(f'hist: ------- time: {self.time}, count: {count}, max: {max}, len: {len(dict_objs)}')

        self.scene.clear()
        for num in dict_objs.keys():
            alpha = float(num) / float(max)
            pos = float(num)
            color = self.color.getColor(alpha)
            # height = float(dict_objs[num]) / float(count)
            height = float(dict_objs[num])
            self.scene.add(pos, height, color)

    def prepare_save(self, ctx=None):
        self.old_time = self.time

    def save_image(self, time):
        self.time = time
        self._make_items()
        img = self.scene.render()
        return img.convert('RGBA')

    def end_save(self):
        self.time = self.old_time
        self._make_items()

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        self.old_pos = float(a0.pos().x())
        a0.accept()

    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        pos = float(a0.pos().x())
        self.scene.translate(float(pos - self.old_pos))
        self.old_pos = pos
        self.reset()
        a0.accept()

    def wheelEvent(self, a0: QWheelEvent) -> None:
        pos = float(a0.pos().x())
        step = float(a0.angleDelta().y() / 120.)
        self.scene.scale(pos, step)
        self.reset()
        a0.accept()

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        print('hist: ------- key press event...')
        if a0.key() == QtCore.Qt.Key.Key_F:
            self.scene.fit()
            self.reset()
            a0.accept()
            return
        if not self.parent():
            if a0.key() == QtCore.Qt.Key.Key_Left and self.time > 0:
                self.set_time(self.time - 1)
                a0.accept()
                return
            elif a0.key() == QtCore.Qt.Key.Key_Right and self.time < 24:
                self.set_time(self.time + 1)
                a0.accept()
                return
            return super().keyPressEvent(a0)


if __name__ == '__main__':
    import sys
    from spacetime import SpaceTime

    spacetime = SpaceTime(T=10, max=30, dim=3)
    spacetime.setRationalSet(n=11)
    spacetime.addRationalSet()

    app = QtWidgets.QApplication(sys.argv)

    histogram = Histogram()
    histogram.set_number(11)
    histogram.set_spacetime(spacetime)
    histogram.set_time(30)
    histogram.show()

    sys.exit(app.exec())
