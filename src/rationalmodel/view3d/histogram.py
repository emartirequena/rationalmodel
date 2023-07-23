from copy import deepcopy
import gc

from PyQt5 import QtWidgets, QtCore, QtGui
import moderngl as mgl, glm
from madcad import brick, vec3, Axis, X, settings, fvec3
from madcad.rendering import View, Scene, Orthographic, Turntable

from config import Config
from color import ColorLine
from renderView import RenderView


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
        self.layout.setContentsMargins(QtCore.QMargins(1, 1, 1, 1))
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
        self.change_flag = True
        self.save_projection = None
        self.save_navigation = None
        self.save_scene = None
        self.save_view = None

    def set_number(self, number):
        self.hist_max = int(number)

    def set_spacetime(self, spacetime):
        if self.spacetime is not spacetime:
            self.spacetime = spacetime
            self.change_flag = True
        else:
            self.change_flag = False

    def set_time(self, time):
        self.time = time
        
        if not self.view:
            if not self.parent():
                scene = Scene(ctx=mgl.create_context(standalone=True, share=False))
            else:
                scene = Scene(ctx=self.parent().view.scene.ctx)
            self.view = View(
                scene, 
                projection=Orthographic(), 
                navigation=Turntable()
            )
            self.layout.addWidget(self.view)
            self.view.preload()
        
        self.bar_height = float(self.hist_max * self.resy) / float(self.resx)
        self.bar_width = 0.5
        self.view.scene.displays.clear()
        objs = self._make_objs()
        self.view.scene.add(objs)
        self.view.scene.render(self.view)

        if self.change_flag:
            print(f'hist: ------- number: {self.hist_max}, resx: {self.resx}, resy: {self.resy}, height: {self.bar_height}')
            self.view.center(center=fvec3(self.hist_max * 0.5, 1, self.bar_height))
            self.view.look(fvec3(self.hist_max * 0.5, 0, self.bar_height))
            self.view.navigation.distance = self.bar_height * 2.5

        del objs
        gc.collect()
        self.view.show()
        self.view.update()

    def _make_objs(self):
        space = self.spacetime.spaces[self.time]

        dict_objs = {}
        dict_keys = {}

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
                dict_objs[num] += num
                count += 1

        print(f'hist: ------- time: {self.time}, count: {count}, max: {max}, len: {len(dict_objs)}')

        for num in dict_objs.keys():
            alpha = float(num) / float(max)
            pos = float(num)
            obj = brick(
                center=vec3(pos + self.bar_width * 0.5, self.bar_width * 0.5, self.bar_height), 
                width=vec3(self.bar_width, self.bar_width, self.bar_height * 2)
            )
            obj.option(color=self.color.getColor(alpha))
            dict_keys[self.config.getKey()] = obj

        print(f"hist: ------- key: {self.config.values['objects_key']}")

        return dict_keys
    
    def prepare_save(self, ctx=None):
        self.save_projection = deepcopy(self.view.projection)
        self.save_navigation = deepcopy(self.view.navigation)
        self.save_scene = Scene(options=None)
        self.save_view = RenderView(
            self.save_scene,
            projection=self.save_projection, 
            navigation=self.save_navigation,
            ctx=ctx
        )
        self.save_view.resize((self.resx, self.resy))

    def save_image(self, time):
        self.old_time = self.time
        self.time = time
        self.save_scene.displays.clear()
        objs = self._make_objs()
        self.save_scene.add(objs)
        img = self.save_view.render()
        self.save_scene.displays.clear()
        self.time = self.old_time
        del objs
        return img
    
    def end_save(self):
        del self.save_projection
        del self.save_navigation
        del self.save_scene
        del self.save_view
        self.save_projection = None
        self.save_navigation = None
        self.save_scene = None
        self.save_view = None

if __name__ == '__main__':
    import sys
    from spacetime import SpaceTime

    opengl_version = (3,3)

    settings_file = r'settings.txt'

    spacetime = SpaceTime(T=8, max=24, dim=3)
    spacetime.setRationalSet(n=99)
    spacetime.addRationalSet()

    settings.load(settings_file)
    
    app = QtWidgets.QApplication(sys.argv)

    histogram = Histogram()
    histogram.set_number(99)
    histogram.set_spacetime(spacetime)
    histogram.set_time(24)
    histogram.view.update()
    print('set_time...')
    histogram.show()
    print('show...')

    err = app.exec()
    print('exec...')
    print(f'Qt error = {err}')

    sys.exit(err)
