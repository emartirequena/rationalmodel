from decimal import Context
import os
import json
import math
import shutil
import subprocess
import sys
from copy import deepcopy
import numpy as np

import moderngl as mgl
from madcad import mathutils, vec3, uvec2, fmat4, rendering, settings, uvsphere, Axis, X, Y, Z, Box, render
from moderngl import create_standalone_context
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from spacetimeRedifussion import SpaceTime as SpaceTimeRedifussion
from utils import getDivisorsAndFactors, divisors

from spacetime import SpaceTime

settings_file = r'settings.txt'
config_file = r'config.json'
validations = 0

opengl_version = (3,3)


class ColorKnot:
    def __init__(self, alpha: float, value: vec3) -> None:
        self.alpha = alpha
        self.value = value


class ColorLine:
    def __init__(self) -> None:
        self.knots: list[ColorKnot] = []
        self.normalized = False
    
    def add(self, alpha: float, value: vec3):
        self.knots.append(ColorKnot(alpha, value))
        self.knots.sort(key=lambda x: x.alpha)
        self.normalized = False

    @staticmethod
    def _blend(a: vec3, b: vec3, alpha: float) -> vec3:
        r = mathutils.lerp(a.x, b.x, alpha)
        g = mathutils.lerp(a.y, b.y, alpha)
        b = mathutils.lerp(a.z, b.z, alpha)
        return vec3(r, g, b)

    def normalize(self):
        if not self.normalized:
            self.normalized = True
            for knot in self.knots:
                knot.alpha = knot.alpha / self.knots[-1].alpha

    def getColor(self, alpha: float) -> vec3:
        self.normalize()
        if alpha <= 0.0:
            return self.knots[0].value
        if alpha >= 1.0:
            return self.knots[-1].value
        for index in range(len(self.knots)):
            if alpha <= self.knots[index].alpha:
                alpha1 = self.knots[index - 1].alpha
                alpha2 = self.knots[index].alpha
                beta = (alpha - alpha1) / (alpha2 - alpha1)
                color = self._blend(
                    self.knots[index - 1].value,
                    self.knots[index].value,
                    beta
                )
                return color
        return vec3(1)


class Config:
    def __init__(self):
        self.values = {
            'image_path': '',
            'video_path': '',
            'image_resx': 1920,
            'image_resy': 1080,
            'ffmpeg_path': '',
            'video_codec': 'prores',
            'video_format': 'mov',
            'colors': [
                {'alpha': 0.0, 'color': [0.2, 0.2, 1.0]},
                {'alpha': 0.5, 'color': [0.3, 0.6, 0.5]},
                {'alpha': 1.0, 'color': [1.0, 0.5, 0.2]}
            ],
            'rad_factor': 2.3,
            'rad_pow': 0.8,
            'max_faces': 20,
            'faces_pow': 0.2
        }
        if os.path.exists(config_file):
            with open(config_file, 'rt') as fp:
                values = json.load(fp)
                for key in list(values.keys()):
                    if key in self.values:
                        self.values[key] = values[key]

    def get(self, key: str):
        if key in self.values:
            return self.values[key]
        return ''
            

class MainView(rendering.View):
    def __init__(self, mainWindow: QtWidgets.QMainWindow, scene, parent=None):
        self.mainWindow = mainWindow
        super().__init__(scene, parent=parent)

    def mouseClick(self, evt):
        obj = self.itemat(QtCore.QPoint(evt.x(), evt.y()))
        if obj:
            center = self.scene.item(obj).box.center
            t = self.mainWindow.timeWidget.value()
            spacetime = self.mainWindow.spacetime
            cell = spacetime.getCell(t, center.x, center.y, center.z)
            max = self.mainWindow.num or 1
            percent = 100.0 * float(cell.count) / float(max)
            text = f'position ({center.x:.1f}, {center.y:.1f}, {center.z:.1f}), num paths: {cell.count} / {max}, percent: {percent:.2f}%'
            self.mainWindow.setStatus(text)
            return True
        return False

    def control(self, key, evt):
        if evt.type() == 3:
            return self.mouseClick(evt)
        if self.mainWindow.rendering:
            return False
        return super().control(key, evt)


class RenderView(rendering.Offscreen):
    def __init__(self, scene, size=uvec2(1920, 1080), navigation=None, projection=None):
        self.scene = scene
        self.projection = projection
        self.navigation = navigation

        self.uniforms = {'proj':fmat4(1), 'view':fmat4(1), 'projview':fmat4(1)}	# last frame rendering constants
        self.targets = []
        self.steps = []
        self.step = 0
        self.stepi = 0

        # dump targets
        self.map_depth = None
        self.map_idents = None
        self.fresh = set()	# set of refreshed internal variables since the last render

        self.scene.ctx = mgl.create_standalone_context(share=True)

        self.init(size)
        self.preload()

    def init(self, size):
        w, h = size

        ctx = self.scene.ctx
        assert ctx, 'context is not initialized'

        # self.fb_frame is already created and sized by Qt
        self.fb_screen = ctx.simple_framebuffer(size)
        self.fb_ident = ctx.simple_framebuffer(size, components=3, dtype='f1')
        self.targets = [ ('screen', self.fb_screen, self.setup_screen),
                            ('ident', self.fb_ident, self.setup_ident)]
        self.map_ident = np.empty((h,w), dtype='u2')
        self.map_depth = np.empty((h,w), dtype='f4')

    def resize(self, size):
        if size != self.fb_screen.size:
            self.init(size)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setUpUi()
        self.count = 0
        self.objs = dict()
        self.list_objs = list()
        self.view = None
        self.rendering = False
        settings.load(settings_file)
        self.make_view()
        self.showMaximized()
        self.spacetime = None
        self.factors = ''
        self.num = 0
        self.numbers = {}
        self.config = Config()
        self.color = ColorLine()
        colors = self.config.get('colors')
        if colors:
            for color in colors:
                self.color.add(color['alpha'], vec3(*color['color']))
        
    def setUpUi(self):
        self.resize(1000, 700)

        self.setWindowTitle('View 3D Spacetime Rational Sets')

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.leftLayout = QtWidgets.QVBoxLayout()
        self.rightLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addLayout(self.leftLayout, 10)
        self.mainLayout.addLayout(self.rightLayout, 1)
        
        self.viewLayout = QtWidgets.QVBoxLayout()
        self.timeLayout = QtWidgets.QHBoxLayout()
        
        self.leftLayout.addLayout(self.viewLayout, 10)
        self.leftLayout.addLayout(self.timeLayout, 1)
        
        self.timeWidget = QtWidgets.QSlider(Qt.Horizontal)
        self.timeWidget.setMinimum(0)
        self.timeWidget.setMaximum(100)
        self.timeWidget.setTickInterval(1)
        self.timeWidget.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.timeWidget.valueChanged.connect(self.make_objects)
        self.timeLayout.addWidget(self.timeWidget)

        self.time = QtWidgets.QSpinBox(self)
        self.time.setMinimumWidth(40)
        self.time.setMinimum(0)
        self.time.setMaximum(10000)
        self.time.valueChanged.connect(self.timeWidget.setValue)
        self.timeWidget.valueChanged.connect(self.time.setValue)
        self.timeLayout.addWidget(self.time)
        self.time.setValue(0)

        self.gridLayout = QtWidgets.QGridLayout()
        
        self.label1 = QtWidgets.QLabel('Period')
        self.gridLayout.addWidget(self.label1, 0, 0)
        self.period = QtWidgets.QSpinBox(self)
        self.period.setMinimum(1)
        self.period.setMaximum(100)
        self.period.valueChanged.connect(self.get_period_factors)
        self.gridLayout.addWidget(self.period, 0, 1)

        self.label2 = QtWidgets.QLabel('Max Time')
        self.gridLayout.addWidget(self.label2, 1, 0)
        self.maxTime = QtWidgets.QSpinBox(self)
        self.maxTime.valueChanged.connect(self.timeWidget.setMaximum)
        self.maxTime.valueChanged.connect(self.timeWidget.setValue)
        self.maxTime.setMinimum(0)
        self.maxTime.setMaximum(10000)
        self.gridLayout.addWidget(self.maxTime, 1, 1)

        self.label3 = QtWidgets.QLabel('Number')
        self.gridLayout.addWidget(self.label3, 2, 0)
        self.number = QtWidgets.QDoubleSpinBox(self)
        self.number.setMinimum(0)
        self.number.setDecimals(0)
        self.number.setMaximum(18446744073709551615)
        self.number.setEnabled(False)
        self.gridLayout.addWidget(self.number, 2, 1)

        self.label4 = QtWidgets.QLabel('Factors')
        self.gridLayout.addWidget(self.label4, 3, 0)
        self.factorsLabel = QtWidgets.QLabel()
        self.factorsLabel.setWordWrap(True)
        self.gridLayout.addWidget(self.factorsLabel, 3, 1)

        self.factorsLayout = QtWidgets.QVBoxLayout()
        self.gridLayout.addLayout(self.factorsLayout, 4, 0)

        self.label4 = QtWidgets.QLabel('Divisors')
        self.gridLayout.addWidget(self.label4, 5, 0)
        self.label_num_divisors = QtWidgets.QLabel('')
        self.gridLayout.addWidget(self.label_num_divisors, 5, 1)

        self.rightLayout.addLayout(self.gridLayout)

        self.divisors = QtWidgets.QListWidget(self)
        self.divisors.clicked.connect(self.setNumber)
        self.rightLayout.addWidget(self.divisors)

        self.redifussion = QtWidgets.QCheckBox('Redifussion', self)
        self.redifussion.setCheckState(Qt.Unchecked)
        self.rightLayout.addWidget(self.redifussion)

        self.computeButton = QtWidgets.QPushButton('Compute', self)
        self.rightLayout.addWidget(self.computeButton)
        self.computeButton.clicked.connect(self.compute)

        self.central = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central)
        self.central.setLayout(self.mainLayout)

        self.menu = self.menuBar()
        self.mainMenu = QtWidgets.QMenu('Main')
        self.actionExit = QtWidgets.QAction('Exit', self)
        self.actionExit.triggered.connect(self.close)
        self.mainMenu.addAction(self.actionExit)
        self.menu.addMenu(self.mainMenu)

        self.menuUtils = QtWidgets.QMenu('Utils')
        self.actionSaveImage = QtWidgets.QAction('Save Image', self)
        self.actionSaveImage.setShortcut('I')
        self.actionSaveImage.triggered.connect(self.saveImage)
        self.menuUtils.addAction(self.actionSaveImage)
        self.actionSaveVideo = QtWidgets.QAction('Save Video', self)
        self.actionSaveVideo.setShortcut('V')
        self.actionSaveVideo.triggered.connect(self.saveVideo)
        self.menuUtils.addAction(self.actionSaveVideo)
        self.menu.addMenu(self.menuUtils)

        self.menuTime = QtWidgets.QMenu('Time')

        self.actionLeft = QtWidgets.QAction('Increment time', self.centralWidget())
        self.actionLeft.setShortcut('Left')
        self.actionLeft.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionLeft.triggered.connect(self.decrementTime)
        self.menuTime.addAction(self.actionLeft)

        self.actionRight = QtWidgets.QAction('Decrement time', self.centralWidget())
        self.actionRight.setShortcut('Right')
        self.actionRight.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionRight.triggered.connect(self.incrementTime)
        self.menuTime.addAction(self.actionRight)

        self.menu.addMenu(self.menuTime)

        self.statusBar = QtWidgets.QStatusBar(self)
        self.statusLabel = QtWidgets.QLabel()
        self.statusBar.addWidget(self.statusLabel)
        self.setStatusBar(self.statusBar)

    def decrementTime(self):
        print('------- decrement time...')
        t = self.timeWidget.value()
        if t > 0:
            self.timeWidget.setValue(t - 1)

    def incrementTime(self):
        print('------- increment time...')
        t = self.timeWidget.value()
        if t < self.maxTime.value():
            self.timeWidget.setValue(t + 1)

    def setStatus(self, txt: str):
        print(txt)
        self.statusLabel.setText(str(txt))
        self.statusBar.show()
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def makePath(self, period, number):
        factors = self.get_output_factors(number)
        base_path  = os.path.join(self.config.get('image_path'), f'P{period:02d}')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        path = os.path.join(base_path, f'N{number:d}_F{factors}')
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def _saveImages(self, init_time, end_time):
        self.setStatus('Saving sequence...')
        self.rendering = True
        
        projection = deepcopy(self.view.projection)
        navigation = deepcopy(self.view.navigation)
        
        number = int(self.number.value())
        period = self.period.value()
        factors = self.get_output_factors(number)
        
        path = self.makePath(period, number)
        image_resx = self.config.get('image_resx')
        image_resy = self.config.get('image_resy')
        ffmpeg_path = self.config.get('ffmpeg_path')
        video_path = self.config.get('video_path')
        video_format = self.config.get('video_format')
        video_codec = self.config.get('video_codec')

        scene = rendering.Scene()
        screen = RenderView(scene, projection=projection, navigation=navigation)
        screen.resize((image_resx, image_resy))

        for time in range(init_time, end_time + 1):
            objs = deepcopy(self.make_objects(time=time, make_view=False))
            scene.displays.clear()
            scene.add(objs)
            img = screen.render()
            img.save(os.path.join(path, f'P{period:02d}_N{number}_F{factors}.{time:04d}.png'))
            del objs
        del projection
        del navigation
        del scene
        del screen

        # if there are more tha one image, save video
        if init_time != end_time:
            in_sequence = os.path.join(path, f'P{period:02d}_N{number}_F{factors}.%04d.png')
            out_factors = self.get_output_factors(number)
            video_file_name = f'P{period:02d}_N{number:d}_F{out_factors}.{video_format}'
            out_video = os.path.join(path, video_file_name)
            options = [
                ffmpeg_path,
                '-y',
                '-r', '1',
                '-i', in_sequence,
                '-c', video_codec,
                '-f', video_format,
                '-s', f'{image_resx}x{image_resy}',
                out_video,
            ]
            self.setStatus('Making video...')
            subprocess.run(options)

            self.setStatus('Copying video...')
            if not os.path.exists(video_path):
                os.makedirs(video_path)
            dest_video = os.path.join(video_path, video_file_name)
            shutil.copyfile(out_video, dest_video)
        
        # self.view.scene.displays.clear()
        self.rendering = False
        self.setStatus('Sequence saved...')

    def saveImage(self):
        self._saveImages(self.time.value(), self.time.value())

    def saveVideo(self):
        self._saveImages(0, self.maxTime.value())

    def compute(self):

        if self.number.value() == 0:
            return
        
        self.setStatus('Creating incremental spacetime...')
        self.rendering = True

        if self.redifussion.isChecked():
            self.spacetime = SpaceTimeRedifussion(self.period.value(), self.maxTime.value(), dim=3)
        else:
            self.spacetime = SpaceTime(self.period.value(), self.maxTime.value(), dim=3)

        self.setStatus(f'Setting rational set for number: {int(self.number.value())} ...')
        self.spacetime.setRationalSet(int(self.number.value()))

        self.setStatus('Adding rational set...')
        self.spacetime.addRationalSet()
        self.timeWidget.setValue(self.maxTime.value())
        self.timeWidget.setFocus()

        self.make_objects(time=self.maxTime.value())
        
    def make_objects(self, time:int=0, make_view:bool=True):
        self.rendering = True

        if self.list_objs:
            for obj in self.list_objs:
                del obj

        if not self.spacetime:
            return
        if make_view:
            time = self.timeWidget.value()
        if time >= len(self.spacetime.spaces):
            return
        space = self.spacetime.spaces[time]

        self.list_objs = []

        self.setStatus(f'Drawing frame: {time} ...')

        self.num = 0
        max = -1
        self.count = 0
        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num > max:
                max = num
            if cell['count']:
                self.count += 1
                self.num += cell['count']
        self.setStatus(f'Num spheres: {self.count}, time: {time}')

        rad_factor = self.config.get('rad_factor')
        rad_pow = self.config.get('rad_pow')
        max_faces = self.config.get('max_faces')
        faces_pow = self.config.get('faces_pow')

        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num == 0:
                continue
            x, y, z = cell['pos']
            alpha = float(num) / float(max)
            rad = math.pow(alpha / rad_factor, rad_pow)
            if rad < 0.02:
                rad = 0.02
            sphere = uvsphere(vec3(x, y, z), rad, resolution=('div', int(max_faces * math.pow(rad, faces_pow))))
            sphere.option(color=self.color.getColor(alpha))
            self.list_objs.append(sphere)

        axisX = Axis(vec3(0), X)
        axisY = Axis(vec3(0), Y)
        axisZ = Axis(vec3(0), Z)
        self.list_objs.append([axisX, axisY, axisZ])

        if time > 0:
            cube = Box(center=vec3(0), width=time)
            self.list_objs.append(cube)

        if isinstance(self.list_objs, list):
            self.objs = dict(enumerate([self.list_objs]))

        if make_view:
            self.make_view()
        else:
            return self.objs

    def make_view(self):

        if not self.view:
            print("view doesn't exists...")
            scene = rendering.Scene(self.objs, options=None)
            self.view = MainView(self, scene)
            self.viewLayout.addWidget(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust(self.view.scene.box())
            
        elif not len(self.view.scene.displays) and self.view.navigation.distance == 1.0:
            print('first number setted...')
            self.view.scene.add(self.objs)
            self.view.scene.render(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust(self.view.scene.box())

        elif not len(self.view.scene.displays):
            print('came from save image...')
            self.view.removeEventFilter(self)
            projection = deepcopy(self.view.projection)
            navigation = deepcopy(self.view.navigation)
            scene = rendering.Scene(self.objs, options=None)
            self.viewLayout.takeAt(0)
            self.view = MainView(self, scene)
            self.view.projection = projection
            self.view.navigation = navigation
            self.viewLayout.addWidget(self.view)
            self.view.show()
            self.view.update()

        else:
            print('continue setting number...')
            self.view.scene.displays.clear()
            self.view.scene.update(self.objs)
            self.view.scene.render(self.view)
            self.view.show()
            self.view.update()

        del self.objs
        self.objs = {}
        self.rendering = False
        self.setStatus(f'{self.count} objects created at frame {self.timeWidget.value()}...')
        
    def get_factors(self, number):
        factors = self.numbers[number]['factors']
        labels = []
        for factor in factors.keys():
            if factors[factor] == 0:
                continue
            elif factors[factor] == 1:
                labels.append(str(factor))
            else:
                labels.append(str(factor) + '^' + str(factors[factor]))

        if not labels:
            labels = ['1']

        label = ', '.join(labels)
        return label

    def get_output_factors(self, number):
        factors = self.numbers[number]['factors']
        labels = []
        for factor in factors.keys():
            if factors[factor] == 0:
                continue
            elif factors[factor] == 1:
                labels.append(str(factor))
            else:
                labels.append(str(factor) + '^' + str(factors[factor]))
        label = '_'.join(labels)
        return label

    def get_period_factors(self, T):
        self.setStatus('Computing divisors...')
        self.fillDivisors(T)
        label = self.get_factors(list(self.numbers.keys())[-1])
        self.factorsLabel.setText(label)
        self.label_num_divisors.setText(f'{len(self.divisors)}')
        self.maxTime.setValue(T * (4 if T < 8 else (3 if T < 17 else 2)))

    def fillDivisors(self, T):
        a = int(8)
        b = int(T)
        c = int(2)
        self.numbers = getDivisorsAndFactors(a**b - 1, a)
        self.divisors.clear()
        is_even: bool = True if T % 2 == 0 else False
        specials = []
        if is_even:
            specials = divisors(a**(T//2) + 1)
        else:
            specials = [c**b - 1]
        for record in self.numbers.values():
            x: int = record['number']
            factors: dict = record['factors']
            period: int = record['period']
            txt = f'{x} ({period}) = {self.get_factors(x)}'
            item = QtWidgets.QListWidgetItem(txt)
            is_prime: bool = True if x in factors.keys() and factors[x] == 1 else False
            if period != T:
                if is_prime:
                    item.setForeground(QtGui.QBrush(Qt.red))
                else:
                    item.setForeground(QtGui.QBrush(Qt.darkRed))
            else:
                if x in specials:
                    item.setForeground(QtGui.QBrush(Qt.darkGreen))
                elif is_prime:
                    item.setForeground(QtGui.QBrush(Qt.blue))
            self.divisors.addItem(item)
                
    def setNumber(self, index):
        item = self.divisors.item(index.row())
        self.number.setValue(int(item.text().split(' ', 1)[0]))


if __name__=="__main__":
    QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QtWidgets.QApplication(sys.argv)
    wi = MainWindow()
    wi.show()
    sys.exit(app.exec())
