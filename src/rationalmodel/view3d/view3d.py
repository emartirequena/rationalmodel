import os
import sys
import time
import math
import shutil
from copy import deepcopy
import gc
from multiprocessing import freeze_support

from madcad import vec3, rendering, settings, uvsphere, Axis, X, Y, Z, Box
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from spacetime import SpaceTime
from rationals import c
from utils import getDivisorsAndFactors, divisors, make_video
from config import Config
from color import ColorLine
from renderView import RenderView
from histogram import Histogram

settings_file = r'settings.txt'

opengl_version = (3,3)


class MainView(rendering.View):
    def __init__(self, mainWindow: QtWidgets.QMainWindow, scene: rendering.Scene, parent: QtWidgets.QWidget=None):
        self.mainWindow = mainWindow
        super().__init__(scene, parent=parent)

    def mouseClick(self, evt):
        obj = self.itemat(QtCore.QPoint(evt.x(), evt.y()))
        if obj:
            center = self.scene.item(obj).box.center
            t = self.mainWindow.timeWidget.value()
            spacetime = self.mainWindow.spacetime
            cell = spacetime.getCell(t, center.x, center.y, center.z, accumulate=self.mainWindow._check_accumulate())
            max = self.mainWindow.num or 1
            count = cell.count
            percent = 100.0 * float(count) / float(max)
            text = f'position ({center.x:.1f}, {center.y:.1f}, {center.z:.1f}), num paths: {count} / {max}, percent: {percent:.2f}%'
            self.mainWindow.setStatus(text)
            return True
        return False

    def control(self, key, evt):
        if evt.type() == 3:
            return self.mouseClick(evt)
        return super().control(key, evt)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setUpUi()
        self.count = 0
        self.objs = {}
        self.view = None
        self.period_changed = False
        self.histogram = None
        self.view_histogram = True
        self.spacetime = None
        self.factors = ''
        self.num = 0
        self.numbers = {}
        self.config = Config()
        self.color = None
        self.loadConfigColors()
        self.make_view(0)
        self.showMaximized()

    def loadConfigColors(self):
        self.color = ColorLine()
        colors = self.config.get('colors')
        if colors:
            for knot in colors:
                self.color.add(knot['alpha'], vec3(*knot['color']))
        
    def setUpUi(self):
        self.resize(1920, 1080)

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

        self.accumulate = QtWidgets.QCheckBox('Accumulate', self)
        self.accumulate.setCheckState(Qt.Unchecked)
        self.rightLayout.addWidget(self.accumulate)

        self.computeButton = QtWidgets.QPushButton('Compute', self)
        self.rightLayout.addWidget(self.computeButton)
        self.computeButton.clicked.connect(self.compute)

        self.central = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central)
        self.central.setLayout(self.mainLayout)

        self.menu = self.menuBar()
        self.mainMenu = QtWidgets.QMenu('Main')
        self.actionExit = QtWidgets.QAction('Exit', self)
        self.actionExit.setShortcut('Esc')
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

        self.menuUtils.addSeparator()

        self.actionFitHistogram = QtWidgets.QAction('Fit Histogram', self)
        self.actionFitHistogram.setShortcut('F')
        self.actionFitHistogram.triggered.connect(self.fit_histogram)
        self.menuUtils.addAction(self.actionFitHistogram)

        self.actionViewHistogram = QtWidgets.QAction('View Histogram', self)
        self.actionViewHistogram.setShortcut('H')
        self.actionViewHistogram.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionViewHistogram.triggered.connect(self.set_view_histogram)
        self.menuUtils.addAction(self.actionViewHistogram)

        self.actionCenterView = QtWidgets.QAction('Center View', self)
        self.actionCenterView.setShortcut('C')
        self.actionCenterView.triggered.connect(self.center_view)
        self.menuUtils.addAction(self.actionCenterView)
        
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

        self.actionInit = QtWidgets.QAction('Set init time', self.centralWidget())
        self.actionInit.setShortcut('Home')
        self.actionInit.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionInit.triggered.connect(self.setTimeInit)
        self.menuTime.addAction(self.actionInit)

        self.actionEnd = QtWidgets.QAction('Set end time', self.centralWidget())
        self.actionEnd.setShortcut('End')
        self.actionEnd.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionEnd.triggered.connect(self.setTimeEnd)
        self.menuTime.addAction(self.actionEnd)

        self.menu.addMenu(self.menuTime)

        self.statusBar = QtWidgets.QStatusBar(self)
        self.statusLabel = QtWidgets.QLabel()
        self.statusBar.addWidget(self.statusLabel)
        self.setStatusBar(self.statusBar)

    def _check_accumulate(self):
        return bool(self.accumulate.checkState())

    def setTimeInit(self):
        print('------- set init time')
        self.timeWidget.setValue(0)

    def setTimeEnd(self):
        print('------- set max time')
        self.timeWidget.setValue(self.maxTime.value())

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
        print(f'status: {txt}')
        self.statusLabel.setText(str(txt))
        self.statusBar.show()
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def _makePath(self, period, number):
        if self._check_accumulate():
            path = os.path.join(self.config.get('image_path'), f'P{period:02d}', 'Accumulate')
        else:
            factors = self.get_output_factors(number)
            path  = os.path.join(self.config.get('image_path'), f'P{period:02d}', f'N{number:d}_F{factors}')
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def _saveImages(self, init_time, end_time):
        self.setStatus('Saving images...')
        
        projection = deepcopy(self.view.projection)
        navigation = deepcopy(self.view.navigation)
        
        number = int(self.number.value())
        period = self.period.value()
        factors = self.get_output_factors(number)
        
        path = self._makePath(period, number)
        image_resx = self.config.get('image_resx')
        image_resy = self.config.get('image_resy')
        histogram_resx = self.config.get('histogram_resx')
        histogram_resy = self.config.get('histogram_resy')
        frame_rate = self.config.get('frame_rate')
        ffmpeg_path = self.config.get('ffmpeg_path')
        video_path = self.config.get('video_path')
        video_format = self.config.get('video_format')
        video_codec = self.config.get('video_codec')
        bit_rate = self.config.get('bit_rate')

        scene = rendering.Scene(options=None)
        view = RenderView(scene, projection=projection, navigation=navigation)
        view.resize((image_resx, image_resy))

        self.histogram.prepare_save(ctx=scene.ctx)

        for time in range(init_time, end_time + 1):
            scene.displays.clear()
            objs = self.make_objects(time=time, make_view=False)
            scene.add(objs)
            img = view.render()
            
            file_name = f'P{period:02d}_N{number}_F{factors}.{time:04d}.png'
            if self.view_histogram:
                hist_name = 'Hist_' + file_name
                hist_img = self.histogram.save_image(time)
                img.alpha_composite(hist_img)
                if self._check_accumulate():
                    hist_name = 'Accum_' + hist_name
                hist_img.save(os.path.join(path, hist_name))

            if self._check_accumulate():
                file_name = 'Accum_' + file_name
            img.save(os.path.join(path, file_name))
            
            scene.displays.clear()
            del objs
            gc.collect()
        
        del projection
        del navigation
        del scene
        del view
        
        self.histogram.end_save()

        gc.collect()
        self.setStatus('Images saved...')

        # if there are more tha one image, save video
        if init_time != end_time:

            if not self._check_accumulate():
                in_sequence_path = os.path.join(path, f'P{period:02d}_N{number}_F{factors}.%04d.png')
                out_video_path = os.path.join(path, f'P{period:02d}_N{number:d}_F{factors}.{video_format}')
                self.setStatus('Making main sequence video...')
                result = make_video(
                    ffmpeg_path, 
                    in_sequence_path, out_video_path, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    image_resx, image_resy
                )
                if not result:
                    self.setStatus('ffmepg not found... (check config.json file specification)')
                    return

                in_sequence_path = os.path.join(path, f'Hist_P{period:02d}_N{number}_F{factors}.%04d.png')
                out_video_path = os.path.join(path, f'Hist_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                self.setStatus('Making histogram video...')
                make_video(
                    ffmpeg_path, 
                    in_sequence_path, out_video_path, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    histogram_resx, histogram_resy
                )

                self.setStatus('Copying video...')
                if not os.path.exists(video_path):
                    os.makedirs(video_path)
                dest_video_path = os.path.join(video_path, f'P{period:02d}_N{number:d}_F{factors}.{video_format}')
                shutil.copyfile(out_video_path, dest_video_path)

            else:
                in_sequence_path = os.path.join(path, f'Accum_P{period:02d}_N{number}_F{factors}.%04d.png')
                out_video_path = os.path.join(path, f'Accum_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                self.setStatus('Making main sequence video...')
                result = make_video(
                    ffmpeg_path, 
                    in_sequence_path, out_video_path, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    image_resx, image_resy
                )
                if not result:
                    self.setStatus('ffmepg not found... (check config.json file specification)')
                    return

                self.setStatus('Copying video...')
                if not os.path.exists(video_path):
                    os.makedirs(video_path)
                dest_video_path = os.path.join(video_path, f'Accum_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                shutil.copyfile(out_video_path, dest_video_path)

            self.setStatus('Videos saved...')

    def saveImage(self):
        self._saveImages(self.time.value(), self.time.value())

    def saveVideo(self):
        if not self._check_accumulate():
            self._saveImages(0, self.maxTime.value())
        else:
            self._saveImages(0, 1)

    def compute(self):
        init = time.time()

        if self.spacetime is not None:
            print('------- del spacetime...')
            if self.histogram is not None:
                self.histogram.set_spacetime(None)
            del self.spacetime
            self.spacetime = None
            gc.collect(2)

        self.setStatus('Creating incremental spacetime...')
        self.spacetime = SpaceTime(self.period.value(), self.maxTime.value(), dim=3)

        self.setStatus(f'Setting rational set for number: {int(self.number.value())} ...')
        self.spacetime.setRationalSet(int(self.number.value()))

        self.setStatus('Adding rational set...')
        self.spacetime.addRationalSet(self.is_special, self._check_accumulate())
        self.setStatus(f'Rational set added for number {int(self.number.value())}')
    
        self.timeWidget.setValue(self.maxTime.value() if self.period_changed else self.time.value())
        self.timeWidget.setFocus()

        self.make_objects()
        self.period_changed = False

        end = time.time()
        print(f'------- compute time = {int(end-init)}')
        
    def make_objects(self, time:int=0, make_view:bool=True):
        if not self.spacetime:
            return
        if self.number.value() == 0:
            return
        if make_view:
            time = self.timeWidget.value()
        if time > self.spacetime.len():
            return
        
        space = self.spacetime.getSpace(time, accumulate=self._check_accumulate())
        view_cells = list(filter(lambda cell: cell.count != 0, space.cells))
        list_objs = []

        self.setStatus(f'Drawing time: {time} ...')

        self.num = 0
        max = -1
        self.count = 0
        for cell in view_cells:
            num = cell.count
            if num > max:
                max = num
            if num > 0:
                self.count += 1
            self.num += num
        self.setStatus(f'Creating {self.count} spheres at time: {time}')

        if not self._check_accumulate():
            rad_factor = self.config.get('rad_factor')
            rad_pow = self.config.get('rad_pow')
        else:
            rad_factor = self.config.get('rad_factor_accum')
            rad_pow = self.config.get('rad_pow_accum')
        rad_min = self.config.get('rad_min')
        max_faces = self.config.get('max_faces')
        faces_pow = self.config.get('faces_pow')

        for cell in view_cells:
            alpha = float(cell.count) / float(max)
            rad = math.pow(alpha / rad_factor, rad_pow)
            if rad < rad_min:
                rad = rad_min
            sphere = uvsphere(vec3(cell.x, cell.y, cell.z), rad, resolution=('div', int(max_faces * math.pow(rad, faces_pow))))
            sphere.option(color=self.color.getColor(alpha))
            list_objs.append(sphere)
        
        del view_cells

        axisX = Axis(vec3(0), X)
        axisY = Axis(vec3(0), Y)
        axisZ = Axis(vec3(0), Z)
        list_objs.append(axisX)
        list_objs.append(axisY)
        list_objs.append(axisZ)

        if time > 0:
            if not self._check_accumulate():
                cube = Box(center=vec3(0), width=time)
            else:
                t = self.maxTime.value()
                t = t if t%2 == 0 else t-1
                cube = Box(center=vec3(0), width=t)
            list_objs.append(cube)

        self.objs = {}
        for i in range(len(list_objs)):
            self.objs[self.config.getKey()] = list_objs[i]

        del list_objs
        gc.collect(2)

        if make_view:
            self.make_view(time)
        else:
            return self.objs

    def make_view(self, time):
        if not self.view:
            print("view doesn't exists...")
            scene = rendering.Scene(self.objs, options=None)
            self.view = MainView(self, scene)
            self.viewLayout.addWidget(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust()
            
        elif not len(self.view.scene.displays) and self.view.navigation.distance == 1.0:
            print('first number set...')
            self.view.scene.add(self.objs)
            self.view.scene.render(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust()
            if not self.histogram: self.histogram = Histogram(parent=self)
            self.histogram.set_spacetime(self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            self.histogram.set_time(time, self.maxTime.value(), self._check_accumulate())
            if self.view_histogram:
                self.histogram.show()

        else:
            print('continue setting number...')
            self.view.scene.displays.clear()
            self.view.scene.add(self.objs)
            self.view.scene.render(self.view)
            self.view.show()
            self.view.update()
            self.histogram.set_spacetime(self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            self.histogram.set_time(time, self.maxTime.value(), self._check_accumulate())
            if self.view_histogram:
                self.histogram.show()

        del self.objs
        self.objs = {}
        gc.collect()
        self.setStatus(f'{self.count} objects created at time {self.timeWidget.value()} for number {int(self.number.value())}...')
        
    def fit_histogram(self):
        if not self.histogram or not self.view_histogram:
            return
        self.histogram.scene.fit()
        self.histogram.reset()
        self.histogram.update()

    def set_view_histogram(self):
        self.view_histogram = not self.view_histogram
        if not self.histogram:
            return
        if not self.view_histogram:
            self.histogram.hide()
        else:
            self.histogram.show()
            self.histogram.update()

    def center_view(self):
        if not self.view:
            return
        self.view.center()
        self.view.adjust()
        self.view.update()

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

    def get_period_factors(self):
        self.setStatus('Computing divisors...')
        self.period_changed = True
        T = int(self.period.value())
        self.spacetime = None
        self.fillDivisors(T)
        label = self.get_factors(list(self.numbers.keys())[-1])
        self.factorsLabel.setText(label)
        self.label_num_divisors.setText(f'{len(self.divisors)}')
        self.cycles = (4 if T < 8 else (3 if T < 17 else 2))
        self.maxTime.setValue(T * self.cycles)
        self.maxTime.setSingleStep(T)

    def fillDivisors(self, T: int):
        a = int(8)
        b = int(T)
        c = int(2)
        self.numbers = getDivisorsAndFactors(a**b - 1, a)
        self.divisors.clear()
        is_even: bool = True if T % 2 == 0 else False
        specials = []
        if is_even:
            d = int(T // 2)
            specials = divisors(a**d + 1)
        else:
            specials = [c**b - 1]
        for record in self.numbers.values():
            x: int = record['number']
            factors: dict = record['factors']
            period: int = record['period']
            item = QtWidgets.QListWidgetItem(f'{x} ({period}) = {self.get_factors(x)}')
            is_prime: bool = True if x in factors.keys() and factors[x] == 1 else False
            is_special: bool = False
            if period != T:
                if is_prime:
                    item.setForeground(QtGui.QBrush(Qt.red))
                else:
                    item.setForeground(QtGui.QBrush(Qt.darkRed))
            else:
                if x in specials:
                    item.setForeground(QtGui.QBrush(Qt.darkGreen))
                    is_special = True
                elif is_prime:
                    item.setForeground(QtGui.QBrush(Qt.blue))
            item.setData(Qt.UserRole, is_special)
            self.divisors.addItem(item)
                
    def setNumber(self, index):
        item = self.divisors.item(index.row())
        self.is_special = item.data(Qt.UserRole)
        self.number.setValue(int(item.text().split(' ', 1)[0]))


if __name__=="__main__":
    QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QtWidgets.QApplication(sys.argv)
    freeze_support()
    settings.load(settings_file)
    wi = MainWindow()
    wi.show()
    sys.exit(app.exec())
