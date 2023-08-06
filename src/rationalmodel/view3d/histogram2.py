from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from PIL import Image, ImageDraw
from madcad import vec3
import numpy as np

from config import Config
from color import ColorLine


def lerp(t, ta, a, tb, b):
    return a + (b-a)*(t-ta)/(tb-ta)


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
        self.ox: float = width / 2
        self.scl: float = 1
        self.items: list[Item] = []

    def clear(self):
        self.items = []

    def add(self, x: int, height: int, color: vec3):
        self.items.append(Item(x, height, color))

    def scale(self, x: float, step: float):
        factor = 1.05 if step > 0. else 1./1.05
        self.scl *= factor
        self.ox -= (x - (self.max - self.min) * self.scl) / self.width

    def fit(self):
        self.min =  1000000
        self.max = -1000000
        for item in self.items:
            if item.x < self.min:
                self.min = item.x
            if item.x > self.max:
                self.max = item.x
        self.scl = self.width / (self.max - self.min)
        self.ox = -self.min * self.scl

    def translate(self, dist: float):
        self.ox += dist

    def render(self):
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, self.width-1, self.height-1), None, (255, 255, 255), 1)
        for item in self.items:
            x = int(item.x * self.scl + self.ox)
            height = np.power(item.height, 0.5) * self.height 
            draw.line((x, self.height - height, x, self.height), (item.color), 3)
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
        img = self.scene.render()
        self.label = QtWidgets.QLabel(self)
        self.label.setPixmap(self.scene._pil2pixmap(img))
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
            height = float(dict_objs[num]) / float(count)
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

    spacetime = SpaceTime(T=8, max=24, dim=3)
    spacetime.setRationalSet(n=241)
    spacetime.addRationalSet()

    app = QtWidgets.QApplication(sys.argv)

    histogram = Histogram()
    histogram.set_number(241)
    histogram.set_spacetime(spacetime)
    histogram.set_time(24)
    histogram.show()

    sys.exit(app.exec())
