import subprocess
import sys
import shutil
import json

import math
from tokenize import Double
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from copy import deepcopy

import moderngl as mgl
from moderngl.context import create_standalone_context
from madcad import *

from spacetime import SpaceTime
from spacetimeRedifussion import SpaceTime as SpaceTimeRedifussion
from utils import divisors, factorGenerator


image_path = ''
video_path = ''
ffmpeg_path = ''
video_resx = 1920
video_resy = 1080
video_codec = 'prores'
video_format = 'mov'
settings_file = r'settings.txt'
config_file = r'config.json'

opengl_version = (3,3)


def colorBlend(a, b, alpha):
    r = mathutils.lerp(a.x, b.x, alpha)
    g = mathutils.lerp(a.y, b.y, alpha)
    b = mathutils.lerp(a.z, b.z, alpha)
    return vec3(r, g, b)


def get_next_frame() -> int:
    elem = list(filter(lambda x: 'image' in x, sorted(os.listdir(image_path))))
    if elem:
        return int(elem[-1].split('.')[-2]) + 1
    else:
        return 1


class ColorKnot:
    def __init__(self, alpha: Double, value: vec3) -> None:
        self.alpha = alpha
        self.value = value


class ColorLine:
    def __init__(self) -> None:
        self.knots: list[ColorKnot] = []
        self.normalized = False
    
    def add(self, alpha: Double, value: vec3):
        self.knots.append(ColorKnot(alpha, value))
        self.knots.sort(key=lambda x: x.alpha)

    def normalize(self):
        if not self.normalized:
            self.normalized = True
            for knot in self.knots:
                knot.alpha = knot.alpha / self.knots[-1].alpha

    def getColor(self, alpha) -> vec3:
        self.normalize()
        if alpha == 0.0:
            return self.knots[0].value
        for index in range(len(self.knots)):
            if alpha <= self.knots[index].alpha:
                beta = mathutils.lerp(self.knots[index - 1].alpha, self.knots[index].alpha, alpha)
                color = colorBlend(
                    self.knots[index - 1].value,
                    self.knots[index].value,
                    beta
                )
                return color
        return vec3(1)


class MainView(rendering.View):
    def __init__(self, mainWindow, scene, parent=None):
        self.mainWindow = mainWindow
        super().__init__(scene, parent=parent)

    def inputEvent(self, event):
        if event.type() == 3:
            obj = self.itemat(QtCore.QPoint(event.x(), event.y()))
            if obj:
                center = self.scene.item(obj).box.center
                t = self.mainWindow.timeWidget.value()
                spacetime = self.mainWindow.spacetime
                cell = spacetime.getCell(t, center.x, center.y, center.z)
                max = self.mainWindow.num or 1
                percent = 100.0 * float(cell.count)/float(max)
                text = f'position ({center.x:.1f}, {center.y:.1f}, {center.z:.1f}), num paths: {cell.count} / {max}, percent: {percent:.2f}%'
                self.mainWindow.setStatus(text)
        else:
            super().inputEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setUpUi()
        self.objs = []
        self.view = None
        self.getConfig()
        self.make_view()
        self.showMaximized()
        self.spacetime = None
        self.factors = ''
        self.num = 0
        self.rendering = False
        self.color = ColorLine()
        self.color.add(0.0,  vec3(0.2, 0.2, 1.0))
        self.color.add(0.05, vec3(0.7, 0.3, 0.4))
        self.color.add(0.4,  vec3(0.5, 0.7, 0.5))
        self.color.add(0.7,  vec3(0.7, 0.5, 0.3))
        self.color.add(1.0,  vec3(1.0, 0.5, 0.2))

    def getConfig(self):
        global image_path, video_path, ffmpeg_path, video_resx, video_resy, video_codec, video_format
        settings.load(settings_file)
        with open(config_file, 'rt') as fp:
            config = json.load(fp)
            image_path = config.get('image_path')
            video_path = config.get('video_path')
            ffmpeg_path = config.get('ffmpeg_path')
            video_resx = config.get('video_resx', 1920)
            video_resy = config.get('video_resy', 1080)
            video_codec = config.get('video_codec', 'prores')
            video_format = config.get('video_format', 'mov')

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
        self.timeWidget.setMaximum(1000)
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
        self.period.valueChanged.connect(self.fillDivisors)
        self.gridLayout.addWidget(self.period, 0, 1)

        self.label2 = QtWidgets.QLabel('Max Time')
        self.gridLayout.addWidget(self.label2, 1, 0)
        self.maxTime = QtWidgets.QSpinBox(self)
        self.maxTime.valueChanged.connect(self.timeWidget.setMaximum)
        self.maxTime.setMinimum(0)
        self.maxTime.setMaximum(10000)
        self.period.valueChanged.connect(self.maxTime.setValue)
        self.period.valueChanged.connect(self.time.setValue)
        self.gridLayout.addWidget(self.maxTime, 1, 1)

        self.label3 = QtWidgets.QLabel('Number')
        self.gridLayout.addWidget(self.label3, 2, 0)
        self.number = QtWidgets.QSpinBox(self)
        self.number.setMinimum(0)
        self.number.setMaximum(2147483647)
        self.gridLayout.addWidget(self.number, 2, 1)

        self.label4 = QtWidgets.QLabel('Factors')
        self.gridLayout.addWidget(self.label4, 3, 0)
        self.factorsLabel = QtWidgets.QLabel()
        self.factorsLabel.setWordWrap(True)
        self.gridLayout.addWidget(self.factorsLabel, 3, 1)

        self.rightLayout.addLayout(self.gridLayout)

        self.factorsLayout = QtWidgets.QVBoxLayout()
        self.rightLayout.addLayout(self.factorsLayout)

        self.label4 = QtWidgets.QLabel('Divisors')
        self.rightLayout.addWidget(self.label4)

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
        if self.rendering:
            return
        t = self.timeWidget.value()
        if t > 0:
            self.timeWidget.setValue(t - 1)

    def incrementTime(self):
        if self.rendering:
            return
        t = self.timeWidget.value()
        if t < self.maxTime.value():
            self.timeWidget.setValue(t + 1)

    def setStatus(self, txt: str):
        print(txt)
        self.statusLabel.setText(str(txt))
        self.statusBar.show()
        global app
        app.processEvents()
    
    def saveImage(self):
        self.setStatus('Saving image...')
        self.rendering = True
        projection = deepcopy(self.view.projection)
        navigation = deepcopy(self.view.navigation)
        objs = deepcopy(self.objs)
        scene = rendering.Scene(objs)
        scene.ctx = create_standalone_context()
        scene.ctx.multisample = False
        scene.ctx.enable_only(mgl.DEPTH_TEST)
        scene.ctx.blend_func = mgl.ONE, mgl.ZERO
        scene.ctx.blend_equation = mgl.FUNC_ADD
        screen = rendering.Offscreen(scene, size=(self.view.width(), self.view.height()), projection=projection, navigation=navigation)
        img = screen.render()
        number = self.number.value()
        period = self.period.value()
        time = self.time.value()
        base_path  = os.path.join(image_path, f'P{period}')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        path = os.path.join(base_path, f'N{number}')
        if not os.path.exists(path):
            os.makdirs(path)
        img.save(os.path.join(path, f'P{period:02d}_N{number}.{time:04d}.png'))
        del objs
        del projection
        del navigation
        del scene
        del screen

        self.rendering = False
        self.setStatus('Image saved...')

    def saveVideo(self):
        self.setStatus('Saving sequence...')
        self.rendering = True
        
        projection = deepcopy(self.view.projection)
        navigation = deepcopy(self.view.navigation)
        
        number = self.number.value()
        period = self.period.value()
        
        base_path  = os.path.join(image_path, f'P{period}')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        path = os.path.join(base_path, f'N{number}')
        if not os.path.exists(path):
            os.makedirs(path)
        
        scene = rendering.Scene()
        scene.ctx = create_standalone_context()
        scene.ctx.multisample = False
        scene.ctx.enable_only(mgl.DEPTH_TEST)
        scene.ctx.blend_func = mgl.ONE, mgl.ZERO
        scene.ctx.blend_equation = mgl.FUNC_ADD
        screen = rendering.Offscreen(scene, size=(self.view.width(), self.view.height()), projection=projection, navigation=navigation)
        for time in range(self.maxTime.value() + 1):
            objs = self.make_objects(time=time, make_view=False)
            scene.displays.clear()
            scene.add(objs)
            img = screen.render()
            img.save(os.path.join(path, f'P{period:02d}_N{number}.{time:04d}.png'))
            del objs
        del projection
        del navigation
        del scene
        del screen
        
        in_sequence = os.path.join(path, f'P{period:02d}_N{number}.%04d.png')
        out_factors = self.get_output_factors(number)
        video_file_name = f'P{period:02d}_N{number}_F{out_factors}.{video_format}'
        out_video = os.path.join(path, video_file_name)
        options = [
            ffmpeg_path,
            '-y',
            '-r', '1',
            '-i', in_sequence,
            '-c', video_codec,
            '-f', video_format,
            '-s', f'{video_resx}x{video_resy}',
            out_video,
        ]
        self.setStatus('Making video...')
        subprocess.run(options)

        self.setStatus('Copying video...')
        if not os.path.exists(video_path):
            os.makedirs(video_path)
        dest_video = os.path.join(video_path, video_file_name)
        shutil.copyfile(out_video, dest_video)
        
        self.rendering = False
        self.setStatus('Sequence saved...')

    def compute(self):
        
        self.setStatus('Creating ..')
        self.rendering = True

        if self.redifussion.isChecked():
            self.spacetime = SpaceTimeRedifussion(self.period.value(), self.maxTime.value(), dim=3)
        else:
            self.spacetime = SpaceTime(self.period.value(), self.maxTime.value(), dim=3)

        self.setStatus(f'Setting rational set for number: {self.number.value()} ...')
        self.spacetime.setRationalSet(self.number.value())

        self.setStatus('Adding rational set...')
        self.spacetime.addRationalSet()
        self.timeWidget.setValue(self.maxTime.value())
        self.timeWidget.setFocus()

        self.make_objects(time=self.maxTime.value())
        
    def make_objects(self, time:int=0, make_view:bool=True):
        self.rendering = True

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
        count = 0
        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num > max:
                max = num
            if cell['count']:
                count += 1
                self.num += cell['count']
        self.setStatus(f'Num spheres: {count}, time: {time}')

        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num == 0:
                continue
            x, y, z = cell['pos']
            alpha = float(num)/float(max)
            rad = alpha * 0.5
            if rad < 0.07:
                rad = 0.07
            sphere = uvsphere(vec3(x, y, z), rad, resolution=('div', int(20 * math.pow(rad, 0.2))))
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
        if self.view and len(self.view.scene.displays):
            self.view.scene.displays.clear()
            self.view.scene.update(self.objs)
            self.view.scene.render(self.view)
            self.view.update()
        else:
            scene = rendering.Scene(self.objs, options=None)
            self.viewLayout.takeAt(0)
            self.view = MainView(self, scene, parent=self.central)
            self.viewLayout.addWidget(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust(scene.box())
        del self.objs
        self.setStatus('Objects list created...')
        self.rendering = False
        
    def get_factors(self, n):
        factors = factorGenerator(n)
        labels = []
        for factor in factors:
            if factors[factor] == 1:
                labels.append(str(factor))
            else:
                labels.append(str(factor) + '^' + str(factors[factor]))

        label = ', '.join(labels)
        return label

    def get_output_factors(self, n):
        factors = factorGenerator(n)
        labels = []
        for factor in factors:
            if factors[factor] == 1:
                labels.append(str(factor))
            else:
                labels.append(str(factor) + '^' + str(factors[factor]))

        label = '_'.join(labels)
        return label

    def get_period_factors(self, T):
        label = self.get_factors(pow(8, T) - 1)
        self.factorsLabel.setText(label)

    def fillDivisors(self, T):
        numbers = divisors(pow(8, T) - 1)
        self.divisors.clear()
        self.divisors.addItems([str(x) + ' = ' + self.get_factors(x) for x in numbers])

    def setNumber(self, index):
        item = self.divisors.item(index.row())
        self.number.setValue(int(item.text().split(' ', 1)[0]))


if __name__=="__main__":
    app = QtWidgets.QApplication(sys.argv)
    wi = MainWindow()
    wi.show()
    sys.exit(app.exec())
