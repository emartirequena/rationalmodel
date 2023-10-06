import os
import sys
import time
import math
import shutil
from copy import deepcopy
import gc
from multiprocessing import freeze_support

from madcad import vec3, rendering, settings, uvsphere, Axis, X, Y, Z, Box, cylinder, brick, fvec3
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from spacetime import SpaceTime
from rationals import c
from utils import getDivisorsAndFactors, divisors, make_video, timing
from config import Config
from color import ColorLine
from renderView import RenderView
from histogram import Histogram

settings_file = r'settings.txt'

opengl_version = (3,3)


class MainView(rendering.View):
    def __init__(self, mainWindow: QtWidgets.QMainWindow, scene: rendering.Scene, projection: rendering.Perspective | rendering.Orthographic, parent: QtWidgets.QWidget=None):
        self.mainWindow = mainWindow
        super().__init__(scene, projection=projection, parent=parent)

    def mouseClick(self, evt):
        obj = self.itemat(QtCore.QPoint(evt.x(), evt.y()))
        if obj:
            center = self.scene.item(obj).box.center
            t = self.mainWindow.timeWidget.value()
            spacetime = self.mainWindow.spacetime
            if spacetime:
                if self.mainWindow.dim == 2:
                    x = center.x
                    y = center.z
                    z = 0.0
                else:
                    x = center.x
                    y = center.y
                    z = center.z
                cell = spacetime.getCell(t, x, y, z, accumulate=self.mainWindow._check_accumulate())
                if not cell:
                    return False
                count = cell.count
                self.mainWindow.select_cells(count)
                self.mainWindow.refresh_selection()
            return True
        return False

    def control(self, _, evt):
        if evt.type() == 3:
            return self.mouseClick(evt)
        return False


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setUpUi()
        self.dim = 3
        self.count = 0
        self.objs = {}
        self.cell_ids = {}
        self.selected = {}
        self.view = None
        self.first_number_set = False
        self.period_changed = False
        self.number_changed = False
        self.histogram = None
        self.view_histogram = True
        self.spacetime = None
        self.factors = ''
        self.num = 0
        self.numbers = {}
        self.config = Config()
        self.color = None
        self.loadConfigColors()
        self._clear_parameters()
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
        self.time.setValue(0)
        self.timeLayout.addWidget(self.time)

        self.gridLayout = QtWidgets.QGridLayout()

        self.dimLabel = QtWidgets.QLabel('Dimension')
        self.gridLayout.addWidget(self.dimLabel, 0, 0)
        self.dimLayout = QtWidgets.QHBoxLayout()
        self.button1D = QtWidgets.QPushButton('1D', self)
        self.button1D.setMaximumWidth(50)
        self.button1D.setMinimumHeight(20)
        self.button1D.clicked.connect(self.set1D)
        self.dimLayout.addWidget(self.button1D)
        self.button2D = QtWidgets.QPushButton('2D', self)
        self.button2D.setMaximumWidth(50)
        self.button2D.setMinimumHeight(20)
        self.button2D.clicked.connect(self.set2D)
        self.dimLayout.addWidget(self.button2D)
        self.button3D = QtWidgets.QPushButton('3D', self)
        self.button3D.setMaximumWidth(50)
        self.button3D.setMinimumHeight(20)
        self.button3D.clicked.connect(self.set3D)
        self.dimLayout.addWidget(self.button3D)
        self.gridLayout.addLayout(self.dimLayout, 0, 1)

        self.label1 = QtWidgets.QLabel('Period')
        self.gridLayout.addWidget(self.label1, 1, 0)
        self.period = QtWidgets.QSpinBox(self)
        self.period.setMinimum(1)
        self.period.setMaximum(100)
        self.period.valueChanged.connect(self.get_period_factors)
        self.gridLayout.addWidget(self.period, 1, 1)

        self.label2 = QtWidgets.QLabel('Max Time')
        self.gridLayout.addWidget(self.label2, 2, 0)
        self.maxTime = QtWidgets.QSpinBox(self)
        self.maxTime.valueChanged.connect(self.timeWidget.setMaximum)
        self.maxTime.valueChanged.connect(self.timeWidget.setValue)
        self.maxTime.valueChanged.connect(self.maxTimeChanged)
        self.maxTime.setMinimum(0)
        self.maxTime.setMaximum(10000)
        self.gridLayout.addWidget(self.maxTime, 2, 1)

        self.label3 = QtWidgets.QLabel('Number')
        self.gridLayout.addWidget(self.label3, 3, 0)
        self.number = QtWidgets.QDoubleSpinBox(self)
        self.number.setMinimum(0)
        self.number.setDecimals(0)
        self.number.setMaximum(18446744073709551615)
        self.number.setEnabled(False)
        self.gridLayout.addWidget(self.number, 3, 1)

        self.label4 = QtWidgets.QLabel('Factors')
        self.gridLayout.addWidget(self.label4, 4, 0)
        self.factorsLabel = QtWidgets.QLabel()
        self.factorsLabel.setWordWrap(True)
        self.gridLayout.addWidget(self.factorsLabel, 4, 1)

        self.factorsLayout = QtWidgets.QVBoxLayout()
        self.gridLayout.addLayout(self.factorsLayout, 5, 0)

        self.label4 = QtWidgets.QLabel('Divisors')
        self.gridLayout.addWidget(self.label4, 6, 0)
        self.label_num_divisors = QtWidgets.QLabel('')
        self.gridLayout.addWidget(self.label_num_divisors, 6, 1)

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

        self.menuSelection = QtWidgets.QMenu('Selection')

        self.actionSelectAll = QtWidgets.QAction('Select All', self)
        self.actionSelectAll.setShortcut('A')
        self.actionSelectAll.triggered.connect(self.select_all)
        self.menuSelection.addAction(self.actionSelectAll)
        
        self.actionDeselectAll = QtWidgets.QAction('Deselect All', self)
        self.actionDeselectAll.setShortcut('D')
        self.actionDeselectAll.triggered.connect(self.deselect_all)
        self.menuSelection.addAction(self.actionDeselectAll)
        
        self.actionInvertSelection = QtWidgets.QAction('Invert Selection', self)
        self.actionInvertSelection.setShortcut('Shift+A')
        self.actionInvertSelection.triggered.connect(self.invert_selection)
        self.menuSelection.addAction(self.actionInvertSelection)

        self.menu.addMenu(self.menuSelection)

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

        self.actionInit = QtWidgets.QAction('Go to init', self.centralWidget())
        self.actionInit.setShortcut('Home')
        self.actionInit.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionInit.triggered.connect(self.setTimeInit)
        self.menuTime.addAction(self.actionInit)

        self.actionEnd = QtWidgets.QAction('Go to end', self.centralWidget())
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

    def _clear_view(self):
        self.first_number_set = False
        if self.view:
            if self.dim < 3:
                self.view.projection = rendering.Orthographic()
            else:
                self.view.projection = rendering.Perspective()
            self.view.navigation = rendering.Turntable(yaw=0, pitch=0)
            self.view.scene.displays.clear()
            self.view.scene.add({})
            self.view.center()
            self.view.adjust()
            self.view.update()
            if self.histogram:
                self.histogram.clear()
        else:
            self.make_view(0)
        self.objs = {}
        self.cell_ids = {}
        self.selected = {}

    def _clear_parameters(self):
        self.period.setValue(1)
        self.period_changed = False
        self.maxTime.setValue(0)
        self.number.setValue(0)
        self.divisors.clear()
        self.factorsLabel.setText('')
        self.label_num_divisors.setText('')
        if self.histogram: 
            self.histogram.set_spacetime(None)
        pressed     = 'QPushButton {background-color: bisque;      color: red;    border-width: 1px; border-radius: 4px; border-style: outset; border-color: gray;}'
        not_pressed = 'QPushButton {background-color: floralwhite; color: black;  border-width: 1px; border-radius: 4px; border-style: outset; border-color: gray;}' \
                      'QPushButton:hover {background-color: lightgray; border-color: blue;}'
        if self.dim == 1:
            self.button1D.setStyleSheet(pressed)
            self.button2D.setStyleSheet(not_pressed)
            self.button3D.setStyleSheet(not_pressed)
        elif self.dim == 2:
            self.button1D.setStyleSheet(not_pressed)
            self.button2D.setStyleSheet(pressed)
            self.button3D.setStyleSheet(not_pressed)
        elif self.dim == 3:
            self.button1D.setStyleSheet(not_pressed)
            self.button2D.setStyleSheet(not_pressed)
            self.button3D.setStyleSheet(pressed)
        self._clear_view()

    def set1D(self):
        self.dim = 1
        self._clear_parameters()

    def set2D(self):
        self.dim = 2
        self._clear_parameters()

    def set3D(self):
        self.dim = 3
        self._clear_parameters()

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

    def _getDimStr(self):
        if self.dim == 1: return '1D'
        elif self.dim == 2: return '2D'
        else: return '3D'

    def _makePath(self, period, number):
        if self._check_accumulate():
            path = os.path.join(self.config.get('image_path'), f'P{period:02d}', self._getDimStr(), 'Accumulate')
        else:
            factors = self.get_output_factors(number)
            path  = os.path.join(self.config.get('image_path'), f'P{period:02d}', self._getDimStr(), f'N{number:d}_F{factors}')
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

        self.histogram.prepare_save_image()

        for time in range(init_time, end_time + 1):
            scene.displays.clear()
            objs = self.make_objects(frame=time, make_view=False)
            scene.add(objs)
            img = view.render()
            
            file_name = f'{self._getDimStr()}_P{period:02d}_N{number}_F{factors}.{time:04d}.png'
            if self.view_histogram:
                hist_name = 'Hist_' + file_name
                hist_img = self.histogram.get_save_image(time)
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
        
        self.histogram.end_save_image()

        gc.collect()
        self.setStatus('Images saved...')

        # if there are more tha one image, save video
        if init_time != end_time:

            if not self._check_accumulate():
                in_sequence_path = os.path.join(path, f'{self._getDimStr()}_P{period:02d}_N{number}_F{factors}.%04d.png')
                main_video_path = os.path.join(path, f'{self._getDimStr()}_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                self.setStatus('Making main sequence video...')
                result = make_video(
                    ffmpeg_path, 
                    in_sequence_path, main_video_path, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    image_resx, image_resy
                )
                if not result:
                    self.setStatus('ffmepg not found... (check config.json file specification)')
                    return

                in_sequence_path = os.path.join(path, f'Hist_{self._getDimStr()}_P{period:02d}_N{number}_F{factors}.%04d.png')
                hist_video_path = os.path.join(path, f'Hist_{self._getDimStr()}_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                self.setStatus('Making histogram video...')
                make_video(
                    ffmpeg_path, 
                    in_sequence_path, hist_video_path, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    histogram_resx, histogram_resy
                )

                self.setStatus('Copying video...')
                if not os.path.exists(video_path):
                    os.makedirs(video_path)
                dest_video_path = os.path.join(video_path, f'{self._getDimStr()}_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                shutil.copyfile(main_video_path, dest_video_path)

            else:
                in_sequence_path = os.path.join(path, f'Accum_{self._getDimStr()}_P{period:02d}_N{number}_F{factors}.%04d.png')
                main_video_path = os.path.join(path, f'Accum_{self._getDimStr()}_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                self.setStatus('Making main sequence video...')
                result = make_video(
                    ffmpeg_path, 
                    in_sequence_path, main_video_path, 
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
                dest_video_path = os.path.join(video_path, f'Accum_{self._getDimStr()}_P{period:02d}_N{number:d}_F{factors}.{video_format}')
                shutil.copyfile(main_video_path, dest_video_path)

            self.setStatus('Videos saved...')

    def saveImage(self):
        self._saveImages(self.time.value(), self.time.value())

    def saveVideo(self):
        if not self._check_accumulate():
            self._saveImages(0, self.maxTime.value())
        else:
            self._saveImages(0, 1)

    def _switch_display(self, count, state=None):
        for id in self.cell_ids[count]:
            if len(list(self.view.scene.item([0]))) == 1:
                disp = self.view.scene.item([0])[0].displays[id]
            else:
                disp = self.view.scene.item([0])[id]
            if type(disp).__name__ in ('SolidDisplay', 'WebDisplay'):
                if self.dim == 2:
                    disp.vertices.selectsub(1)
                else:
                    disp.vertices.selectsub(0)
                disp.selected = state if state is not None else not any(disp.vertices.flags & 0x1)
            else:
                disp.selected = state if state is not None else not disp.selected

    def select_cells(self, count):
        if not count:
            return
        if count not in self.selected:
            self.selected[count] = self.cell_ids[count]
            self._switch_display(count, True)
        else:
            self._switch_display(count, False)
            del self.selected[count]

    @timing
    def select_all(self, nope=False):
        for count in self.cell_ids:
            if count not in self.selected:
                self.selected[count] = self.cell_ids[count]
                self._switch_display(count, True)
        self.refresh_selection()

    @timing
    def deselect_all(self, nope=False):
        if not self.selected:
            return
        for count in self.selected:
            self._switch_display(count, False)
        self.selected = {}
        gc.collect()       
        self.refresh_selection()

    def invert_selection(self):
        not_selected = {}
        for count in self.cell_ids:
            if count in self.selected:
                self._switch_display(count, False)
            else:
                not_selected[count] = self.cell_ids[count]
                self._switch_display(count, True)
        self.selected = not_selected    
        self.refresh_selection()

    def refresh_selection(self):
        self.print_selection()
        if self.view:
            self.view.update()
        if self.histogram:
            self.histogram.display_all()
            self.histogram.update()

    def print_selection(self):
        selected_cells, selected_paths = self.get_selected_paths()
        max = self.num or 1
        if selected_cells == 0:
            self.setStatus('Selected cells: 0')
            return
        percent = 100.0 * float(selected_paths) / float(max)
        text = f'Selected cells: {selected_cells}, num paths: {selected_paths} / {max}, percent: {percent:.2f}%'
        self.setStatus(text)
    
    def is_selected(self, count):
        if count in self.selected:
            return True
        return False
    
    def get_selected_paths(self):
        num_cells = 0
        total_paths = 0
        for count in self.selected:
            num_cells += len(self.selected[count])
            total_paths += count * len(self.selected[count])
        return num_cells, total_paths

    @timing
    def compute(self, nada=False):
        if not int(self.number.value()):
            return
        
        if not self.number_changed and self._check_accumulate():
            self.make_objects()
            self.period_changed = False
            return
        self.number_changed = False

        app.setOverrideCursor(QtCore.Qt.WaitCursor)

        if self.spacetime is not None:
            if self.histogram is not None:
                self.histogram.set_spacetime(None)
            del self.spacetime
            self.spacetime = None
            gc.collect(2)

        self.deselect_all()

        self.setStatus('Creating incremental spacetime...')
        self.spacetime = SpaceTime(self.period.value(), self.maxTime.value(), dim=self.dim)

        self.setStatus(f'Setting rational set for number: {int(self.number.value())} ...')
        self.spacetime.setRationalSet(int(self.number.value()))

        self.setStatus('Adding rational set...')
        self.spacetime.addRationalSet(self.is_special, self._check_accumulate())
        self.setStatus(f'Rational set added for number {int(self.number.value())}')
    
        self.timeWidget.setValue(self.maxTime.value() if self.period_changed else self.time.value())
        self.timeWidget.setFocus()

        self.make_objects()
        self.period_changed = False

        app.restoreOverrideCursor()

    def make_objects(self, frame:int=0, make_view:bool=True):
        if not self.spacetime:
            return
        if self.number.value() == 0:
            return
        if frame > self.spacetime.len():
            return

        if make_view:
            frame = self.timeWidget.value()
            self.deselect_all()
        
        view_cells = self.spacetime.getCells(frame, accumulate=self._check_accumulate())
        self.setStatus(f'Drawing time: {frame} ...')

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
        
        self.setStatus(f'Creating {self.count} objects at time: {frame}')

        if not self._check_accumulate():
            rad_factor = self.config.get('rad_factor')
            rad_pow = self.config.get('rad_pow')
        else:
            rad_factor = self.config.get('rad_factor_accum')
            rad_pow = self.config.get('rad_pow_accum')
        rad_min = self.config.get('rad_min')
        max_faces = self.config.get('max_faces')
        faces_pow = self.config.get('faces_pow')

        self.cell_ids = {}
        self.objs = {}

        for cell in view_cells:
            alpha = float(cell.count) / float(max)
            rad = math.pow(alpha / rad_factor, rad_pow)
            if rad < rad_min:
                rad = rad_min
            id = self.config.getKey()
            color = self.color.getColor(alpha)
            if cell.count not in self.cell_ids:
                self.cell_ids[cell.count] = []
            self.cell_ids[cell.count].append(id)

            if self.dim == 3:
                obj = uvsphere(vec3(cell.x, cell.y, cell.z), rad, resolution=('div', int(max_faces * math.pow(rad, faces_pow))))
            elif self.dim == 2:
                obj = cylinder(vec3(cell.x, 0, cell.y), vec3(cell.x, alpha*10, cell.y), rad)
            else:
                obj = brick(vec3(cell.x - c, 0, 0), vec3(cell.x + c, 1, alpha*10))

            obj.option(color=color)
            self.objs[id] = obj

        del view_cells

        dirs = [X, Y, Z]
        for dir in dirs:
            axis = Axis(vec3(0), dir)
            id = self.config.getKey()
            self.objs[id] = axis

        if frame > 0 and self.dim > 1:
            if not self._check_accumulate():
                cube = Box(center=vec3(0), width=frame)
            else:
                t = self.maxTime.value()
                cube = Box(center=vec3(0), width=t if frame%2 == 0 else t-1)
            id = self.config.getKey()
            self.objs[id] = cube

        if make_view:
            self.make_view(frame)
        else:
            return self.objs

    def make_view(self, frame):
        if not self.view:
            print("view doesn't exists...")
            if self.dim < 3:
                projection = rendering.Orthographic()
            else:
                projection = rendering.Perspective()
            scene = rendering.Scene(self.objs, options=None)
            self.view = MainView(self, scene, projection=projection)
            self.viewLayout.addWidget(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust()
            self.view.update()
            
        elif not self.first_number_set:
            print('first number set...')
            self.first_number_set = True
            self.view.scene.update(self.objs)
            self.view.scene.render(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust()
            if not self.histogram: self.histogram = Histogram(parent=self)
            self.histogram.set_spacetime(self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            self.histogram.set_time(frame, self._check_accumulate())
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
            self.histogram.set_time(frame, self._check_accumulate())
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
        self.view.navigation = rendering.Turntable(yaw=0, pitch=0)
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
        a = int(2 ** self.dim)
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
        self.number_changed = True
        item = self.divisors.item(index.row())
        self.is_special = item.data(Qt.UserRole)
        self.number.setValue(int(item.text().split(' ', 1)[0]))

    def maxTimeChanged(self):
        self.number_changed = True


if __name__=="__main__":
    QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QtWidgets.QApplication(sys.argv)
    freeze_support()
    settings.load(settings_file)
    wi = MainWindow()
    wi.show()
    sys.exit(app.exec())
