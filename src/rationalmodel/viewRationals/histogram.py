from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from PIL import Image, ImageDraw
from madcad import vec3
import numpy as np
import gc

from config import Config
from color import ColorLine
from utils import lerp

epsilon = 5.
colors = [(100, 100, 100), (200, 100, 0), (150, 150, 150), (255, 255, 0)]


class Item:
    def __init__(self, x: int, height: int, color: vec3, count: int) -> None:
        self.x = x
        self.height = height
        self.count = count
        self.color = (
            int(255 * color.x), 
            int(255 * color.y), 
            int(255 * color.z)
        )

    def check_position(self, x, eps):
        if self.x - eps <= x <= self.x + eps:
            return True
        return False


class Scene:
    def __init__(self, width: int, height: int, y_factor: float=1.) -> None:
        self.width: int = width
        self.height: int = height
        self.min_x = 0.
        self.max_x = 0.
        self.max_h = 0.
        self.y_factor = y_factor
        self.ox: float = width / 2
        self.scl: float = 1.
        self.items: list[Item] = []
        self.select_area = None

    def clear(self, max_h=1.):
        self.items = []
        self.max_x = 0.
        self.max_h = max_h

    def add(self, x: int, height: int, color: vec3, count: int):
        self.items.append(Item(x, height, color, count))
        if x > self.max_x: self.max_x = x

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
            self.ox = -self.min_x
        else:
            self.scl = self.width / self.max_x
            self.ox = 0.
        self.scale(self.width / 2.0, -1.0)

    def translate(self, dist: float):
        self.ox += dist / self.scl

    def screen2world(self, xscr: int) -> float:
        return xscr / self.scl - self.ox
    
    def world2screen(self, xwrld: float) -> int:
        return int((xwrld + self.ox) * self.scl)

    @staticmethod
    def _loga(a, x):
        return np.log(x) / np.log(a)
    
    def _loga_round(self, a, x):
        return int(np.power(a, int(self._loga(a, x))))
    
    def _get_y_step_max(self, y_base):
        y_step = int(self._loga_round(y_base, self.max_h))
        y_step = y_step if y_step > 0 else 1
        y_max = y_step * np.power(y_base, 2)
        return y_step, y_max
    
    def _get_x_step_max(self, x_base):
        x_step = self._loga_round(x_base, x_base * 10 / self.scl)
        x_step = x_step if x_step > 0 else 1
        x_max = x_step * np.power(x_base, 3)
        return x_step, x_max

    def _render_grid(self, draw):
        x_base = 10
        y_base = 5

        y_step, y_max = self._get_y_step_max(y_base)
        for y in range(y_step, y_max, y_step):
            color = colors[0]
            if y % ( 5 * y_step) == 0: color = colors[2]
            if y % (10 * y_step) == 0: color = colors[1]
            if self._loga(y_base, y) >= 1 and color == colors[0]:
                continue
            h = np.power(y / y_max, self.y_factor) * self.height
            draw.line((0, self.height - h, self.width, self.height - h), color, 1)

        x_step, x_max = self._get_x_step_max(x_base)
        for x in range(-x_max, x_max, x_step):

            color = colors[0]
            if x == 0: color = colors[3]
            else:
                if abs(x_max - x) % ( 5 * x_step) == 0: color = colors[2]
                if abs(x_max - x) % (10 * x_step) == 0: color = colors[1]
            px = int((x + self.ox) * self.scl)
            if px < 0 or px > self.width: continue
            w = 1 if np.abs(px) > 0.1 else 3
            draw.line((px, self.height, px, 0), color, w)

    def render(self):
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        if self.select_area:
            self.select_area.render(draw)

        self._render_grid(draw)
        _, y_max = self._get_y_step_max(10)
        for item in self.items:
            x = int((item.x + self.ox) * self.scl)
            h = np.power(item.height / y_max, self.y_factor) * self.height
            draw.line((x, self.height - h, x, self.height), (item.color), 3)

        draw.rectangle((0, 0, self.width-1, self.height-1), None, (255, 255, 255), 1)
        return img
    
    def itemat(self, x):
        x = self.screen2world(x)
        eps = epsilon / self.scl
        print(f'eps: {eps:0.2f}, x: {x:0.2f}')
        for item in self.items:
            if item.x - eps <= x <= item.x + eps:
                print(f'item.x: {item.x:0.2f}')
                return item
            # if item.check_position(x, eps):
            #     return item
        return None

    @staticmethod
    def _pil2pixmap(img):
        if img.mode == "RGB":
            r, g, b = img.split()
            img = Image.merge("RGB", (b, g, r))
        elif  img.mode == "RGBA":
            r, g, b, a = img.split()
            img = Image.merge("RGBA", (b, g, r, a))
        elif img.mode == "L":
            img = img.convert("RGBA")
        img2 = img.convert("RGBA")
        data = img2.tobytes("raw", "RGBA")
        qimg = QtGui.QImage(data, img.size[0], img.size[1], QtGui.QImage.Format_ARGB32)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        return pixmap
    
    def init_select_area(self, begin: int):
        self.select_area = SelectArea(begin, self)

    def move_select_area(self, end: int):
        if self.select_area:
            self.select_area.set_end(end)

    def end_select_area(self):
        if not self.select_area:
            return []
        selected = []
        for item in self.items:
            if self.select_area.inside(item.x):
                selected.append(item)
        self.select_area = None
        return selected


class SelectArea:
    def __init__(self, begin: int, scene: Scene):
        self.begin = begin
        self.end = begin
        self.scene = scene

    def set_end(self, end: int):
        self.end = end

    def render(self, draw: ImageDraw.Draw):
        colors = [(50, 50, 50), (50, 50, 200)]
        if self.begin == self.end:
            return
        if self.end < self.begin:
            t = self.end
            self.end = self.begin
            self.begin = t
        draw.rectangle((self.begin, 0, self.end, self.scene.height), colors[0], colors[1], 1)

    def inside(self, xwrld: float):
        x = self.scene.world2screen(xwrld)
        if self.begin <= x <= self.end:
            return True
        return False


class Histogram(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.spacetime: SpaceTime = None
        self.time = 0
        self.number = 0
        self.accumulate = False
        self.moving = False
        if not parent:
            self.config = Config()
        else:
            self.config = parent.config
        self.resx = self.config.get('histogram_resx')
        self.resy = self.config.get('histogram_resy')
        self.hist_size = (self.resx, self.resy)
        self.hist_max = self.config.get('histogram_max')
        self.hist_y_factor = self.config.get('histogram_y_factor')
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

        self.scene = Scene(self.width(), self.height(), self.hist_y_factor)
        self.scene.clear()
        self.label = QtWidgets.QLabel(self)
        self.layout.addWidget(self.label)
        
        self.old_pos = 0.0

    def clear(self):
        self.scene.clear()
        self.reset()

    def set_number(self, number):
        if self.number != number:
            self.change_flag = True
        self.number = number
        self.scene.clear(number)

    def set_spacetime(self, spacetime):
        if not spacetime:
            return
        if not self.spacetime or self.spacetime.T != spacetime.T:
            self.change_flag = True
        else:
            self.change_flag = False
        self.spacetime = spacetime

    def reset(self):
        img = self.scene.render()
        self.label.setPixmap(self.scene._pil2pixmap(img))
        if self.isVisible():
            self.show()
            self.update()

    def set_time(self, time, accumulate=False):
        self.time = time
        self.accumulate = accumulate
        self.display_all()

    def display_all(self):
        self._make_items()
        if self.change_flag:
            self.scene.fit()
            self.change_flag = False
        self.reset()

    def _make_items(self):
        space = self.spacetime.getSpace(self.time, self.accumulate)

        dict_objs = {}

        view_cells = list(filter(lambda cell: cell.count != 0, space.cells))

        max = -1
        for cell in view_cells:
            count = cell.count
            if count > max:
                max = count
            if count not in dict_objs: dict_objs[count] = 0
            dict_objs[count] += 1

        self.scene.clear()
        for count in dict_objs.keys():
            alpha = float(count) / float(max)
            pos = float(count)
            if self.parent() and self.parent().is_selected(count):
                color = vec3(255, 255, 255)
            else:
                color = self.color.getColor(alpha)
            height = float(dict_objs[count])
            self.scene.add(pos, height, color, count)

        del view_cells
        del dict_objs
        gc.collect()

    def prepare_save_image(self):
        self.old_time = self.time

    def get_save_image(self, time):
        self.time = time
        self._make_items()
        if self.accumulate:
            self.scene.fit()
        img = self.scene.render()
        return img.convert('RGBA')

    def end_save_image(self):
        self.time = self.old_time
        self._make_items()

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.modifiers() & QtCore.Qt.ShiftModifier:
            self.scene.init_select_area(a0.pos().x())
        else:
            self.old_pos = float(a0.pos().x())
            self.scene.select_area = None
            self.moving = False
        a0.accept()

    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        if a0.modifiers() & QtCore.Qt.ShiftModifier: 
            self.scene.move_select_area(a0.pos().x())
        else:
            self.moving = True
            pos = float(a0.pos().x())
            self.scene.translate(float(pos - self.old_pos))
            self.old_pos = pos
        self.reset()
        a0.accept()

    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        if a0.modifiers() & QtCore.Qt.ShiftModifier: 
            selected_items = self.scene.end_select_area()
            for item in selected_items:
                self.parent().select_cells(item.count)
            self.parent().refresh_selection()
        else:
            if not self.moving:
                item = self.scene.itemat(a0.pos().x())
                if item:
                    self.parent().select_cells(item.count)
                    self.parent().refresh_selection()
            self.moving = False
        a0.accept()

    def wheelEvent(self, a0: QWheelEvent) -> None:
        pos = float(a0.pos().x())
        step = float(a0.angleDelta().y() / 120.)
        self.scene.scale(pos, step)
        self.reset()
        a0.accept()

    # def keyPressEvent(self, a0: QKeyEvent) -> None:
    #     print('hist: ------- key press event...')
    #     if a0.key() == QtCore.Qt.Key.Key_F:
    #         self.scene.fit()
    #         self.reset()
    #         a0.accept()
    #         return
    #     if not self.parent():
    #         if a0.key() == QtCore.Qt.Key.Key_Left and self.time > 0:
    #             self.set_time(self.time - 1)
    #             a0.accept()
    #             return
    #         elif a0.key() == QtCore.Qt.Key.Key_Right and self.time < 30:
    #             self.set_time(self.time + 1)
    #             a0.accept()
    #             return
    #         return super().keyPressEvent(a0)


if __name__ == '__main__':
    import sys
    from spacetime import SpaceTime

    n = 32769
    T = 10
    max = 30
    dim = 3

    spacetime = SpaceTime(T=T, max=max, dim=dim)
    spacetime.setRationalSet(n)
    spacetime.addRationalSet()

    app = QtWidgets.QApplication(sys.argv)

    histogram = Histogram()
    histogram.set_number(n)
    histogram.set_spacetime(spacetime)
    histogram.set_time(max, max)
    histogram.show()

    sys.exit(app.exec())
