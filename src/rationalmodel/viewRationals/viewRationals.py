import os
import sys
import math
from time import time, sleep
from multiprocessing import freeze_support, active_children, Process
import math
from threading import Thread, Event
from copy import deepcopy

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import numpy as np
from madcad import vec3, settings, Axis, X, Y, Z, Box, cylinder, brick, icosphere, cone

from mainWindowUi import MainWindowUI
from views import Views
from saveSpecials import SaveSpecialsWidget
from saveVideo import SaveVideoWidget
from spacetime_index import SpaceTime, Cell
from rationals import c
from utils import getDivisorsAndFactors, divisors, make_video, collect
from timing import timing
from config import config
from color import ColorLine
from histogram import Histogram
from saveImages import _saveImages

settings_file = r'settings.txt'

opengl_version = (3,3)


class VideoThread(Thread):
    def __init__(self, func, args):
        super().__init__()
        self.func = func
        self.args = args
    
    def run(self):
        self.func(self.args)

    def kill(self):
        print('------- KILL VIDEO...')


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = MainWindowUI()
        self.ui.setUpUi(self)
        self.dim = 3
        self.count = 0
        self.cell_ids = {}
        self.selected = {}
        self.views = None
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.rotate3DView)
        self.turntable_angle = 0.005
        self.first_number_set = False
        self.changed_spacetime = True
        self.need_compute = True
        self.histogram = None
        self.view_histogram = True
        self.view_objects = True
        self.view_next_number = False
        self.spacetime = None
        self.video_thread = None
        self.factors = ''
        self.num = 0
        self.numbers = {}
        self.config = config
        self.color = None
        self.files_path = self.config.get('files_path')
        self.loadConfigColors()
        self._clear_parameters()
        self.showMaximized()

    def loadConfigColors(self):
        self.color = ColorLine()
        colors = self.config.get('colors')
        if colors:
            for knot in colors:
                self.color.add(knot['alpha'], vec3(*knot['color']))
        
    def _check_accumulate(self):
        return bool(self.accumulate.checkState())

    def _clear_view(self):
        self.first_number_set = False
        if self.views:
            self.views.clear()
            if self.histogram:
                self.histogram.clear()
        else:
            self.make_view(0)
        if self.cell_ids:
            del self.cell_ids
        self.cell_ids = {}
        if self.selected:
            del self.selected
        self.selected = {}
        collect('_clear_view')
        self.timer.stop()

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
            if self.views:
                self.views.set_mode('1D')
            self.button1D.setStyleSheet(pressed)
            self.button2D.setStyleSheet(not_pressed)
            self.button3D.setStyleSheet(not_pressed)
        elif self.dim == 2:
            if self.views:
                self.views.set_mode('2D')
            self.button1D.setStyleSheet(not_pressed)
            self.button2D.setStyleSheet(pressed)
            self.button3D.setStyleSheet(not_pressed)
        elif self.dim == 3:
            if self.views:
                self.views.set_mode(self.views.get_mode_3d())
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
        dims = ['1D', '2D', '3D']
        return dims[self.dim - 1]

    def saveImage(self, subfolder=''):
        if subfolder == False: subfolder = ''
        frame = int(self.time.value())
        self.saveVideo(init_frame=frame, end_frame=frame, subfolder=subfolder, num_frames=1)

    def saveVideo(self, init_frame=0, end_frame=0, subfolder='', prefix='', suffix='', num_frames=0, turn_angle=0):
        if self.views.mode not in ['1D', '2D', '3D']:
            QtWidgets.QMessageBox.critical(self, 'ERROR', 'Split 3D view is not allowed for videos')
            return
        if end_frame > self.maxTime.value():
            QtWidgets.QMessageBox.critical(self, 'ERROR', 'End Frame cannot be greatest than Max Time')
            return
        self.deselect_all()

        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        image_path = self.config.get('image_path')
        frame_rate = self.config.get('frame_rate')
        if turn_angle > 0:
            frame_rate = 25.0
        if num_frames == 0:
            if end_frame == 0:
                num_frames = int(self.maxTime.value() * frame_rate)
            else:
                num_frames = int((end_frame - init_frame + 1) * frame_rate)
        if end_frame == 0:
            end_frame = self.maxTime.value()
        if self._check_accumulate() and turn_angle == 0 and num_frames > 1:
            init_frame = 0
            end_frame = 6
            num_frames = 6

        args = (
            deepcopy(self.views.views[self.views.mode].view.projection),
            deepcopy(self.views.views[self.views.mode].view.navigation),
            image_path,
            init_frame,
            end_frame,
            subfolder,
            prefix,
            suffix,
            num_frames,
            turn_angle,
            config,
            self.color,
            self.views.views[self.views.mode].type,
            deepcopy(self.spacetime),
            self.dim,
            self.number.value(),
            self.period.value(),
            self.get_output_factors(self.number.value()),
            self._check_accumulate(),
            self._getDimStr(),
            self.actionViewObjects.isChecked(),
            self.actionViewNextNumber.isChecked(),
            self.maxTime.value()
        )

        self.video_thread = VideoThread(_saveImages, args)
        self.video_thread.start()

        # self.video_thread = Thread(target=_saveImages, args=[args])
        # self.video_thread.start()

        app.restoreOverrideCursor()

    def cancelVideo(self):
        if self.video_thread:
            self.video_thread.kill()

    def _switch_display(self, count, state=None):
        for id in self.cell_ids[count]:
            self.views.switch_display_id(id, state=state)

    def select_cells(self, count):
        if not count:
            return
        if count not in self.selected:
            self.selected[count] = self.cell_ids[count]
            self._switch_display(count, True)
        else:
            self._switch_display(count, False)
            del self.selected[count]

    def select_all(self, nope=False):
        for count in self.cell_ids:
            if count not in self.selected:
                self.selected[count] = self.cell_ids[count]
                self._switch_display(count, True)
        self.refresh_selection()

    def deselect_all(self, nope=False):
        if not self.selected:
            return
        for count in self.selected:
            self._switch_display(count, False)
        self.selected = {}
        self.refresh_selection()

    def reselect_cells(self):
        for count in self.cell_ids:
            if count in self.selected:
                self._switch_display(count, True)
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
        if self.views:
            self.views.update()
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
        
        print(f'need_compute: {self.need_compute}, changed_spacetime: {self.changed_spacetime}')
        
        if not self.need_compute:
            self.draw_objects()
            self.period_changed = False
            return

        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        time1 = time()

        self.deselect_all()

        n = int(self.number.value())

        if self.changed_spacetime:
            if self.spacetime is not None:
                if self.histogram is not None:
                    self.histogram.set_spacetime(None)
                del self.spacetime
                self.spacetime = None

            self.setStatus('Creating incremental spacetime...')
            self.spacetime = SpaceTime(self.period.value(), n, self.maxTime.value(), dim=self.dim)
            self.changed_spacetime = False
            self.need_compute = False

        self.spacetime.clear()

        self.setStatus(f'Setting rational set for number: {n} ...')
        self.spacetime.setRationalSet(n, self.is_special)

        self.setStatus('Adding rational set...')
        self.spacetime.addRationalSet()
        self.setStatus(f'Rational set added for number {n}')
    
        self.timeWidget.setValue(self.maxTime.value() if self.period_changed else self.time.value())
        self.timeWidget.setFocus()

        if self.time.value() != self.maxTime.value():
            self.time.setValue(self.maxTime.value())
        else:
            self.draw_objects()

        collect('Compute')
        
        time2 = time()
        self.setStatus(f'Rationals set for number {n:,.0f} computed in {time2-time1:,.2f} secs')

        app.restoreOverrideCursor()

    @staticmethod
    def _get_next_number_dir(dim, cell: Cell):
        if dim == 1:
            v1 = np.array([ 1,  0,  0]) * cell.next_digits[0]
            v2 = np.array([-1,  0,  0]) * cell.next_digits[1]
            v = (v1 + v2) / 2.0
        elif dim == 2:
            v1 = np.array([ 1,  0,  1]) * cell.next_digits[0]
            v2 = np.array([-1,  0,  1]) * cell.next_digits[1]
            v3 = np.array([ 1,  0, -1]) * cell.next_digits[2]
            v4 = np.array([-1,  0, -1]) * cell.next_digits[3]
            v = (v1 + v2 + v3 + v4) / 4.0
        else:
            v1 = np.array([ 1,  1,  1]) * cell.next_digits[0]
            v2 = np.array([-1,  1,  1]) * cell.next_digits[1]
            v3 = np.array([ 1,  1, -1]) * cell.next_digits[2]
            v4 = np.array([-1,  1, -1]) * cell.next_digits[3]
            v5 = np.array([ 1, -1,  1]) * cell.next_digits[4]
            v6 = np.array([-1, -1,  1]) * cell.next_digits[5]
            v7 = np.array([ 1, -1, -1]) * cell.next_digits[6]
            v8 = np.array([-1, -1, -1]) * cell.next_digits[7]
            v = (v1 + v2 + v3 + v4 + v5 + v6 + v7 + v8) / 8.0
        return v * cell.count

    @timing
    def draw_objects(self, frame=0):
        self.make_objs(frame, make_view=True)

    @timing
    def make_objects(self, frame=0):
        return self.make_objs(frame, make_view=False)

    def make_objs(self, frame:int=0, make_view:bool=True):
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

        self.num = 0
        self.max = -1
        self.count = 0
        for cell in view_cells:
            num = cell.count
            if num > self.max:
                self.max = num
            if num > 0:
                self.count += 1
            self.num += num
        
        self.setStatus(f'Creating {self.count} cells at time: {frame}')

        if not self._check_accumulate():
            rad_factor = self.config.get('rad_factor')
            rad_pow = self.config.get('rad_pow')
        else:
            rad_factor = self.config.get('rad_factor_accum')
            rad_pow = self.config.get('rad_pow_accum')
        rad_min = self.config.get('rad_min')
        max_faces = self.config.get('max_faces')
        faces_pow = self.config.get('faces_pow')

        config.resetKey()

        if self.cell_ids:
            del self.cell_ids
        self.cell_ids = {}
        objs = {}

        if self.actionViewObjects.isChecked():
            for cell in view_cells:
                alpha = float(cell.count) / float(self.max)
                rad = math.pow(alpha / rad_factor, rad_pow)
                if rad < rad_min:
                    rad = rad_min
                id = self.config.getKey()
                color = self.color.getColor(alpha)
                if cell.count not in self.cell_ids:
                    self.cell_ids[cell.count] = []
                self.cell_ids[cell.count].append(id)

                if self.dim == 3:
                    obj = icosphere(vec3(cell.x, cell.y, cell.z), rad, resolution=('div', int(max_faces * math.pow(rad, faces_pow))))
                elif self.dim == 2:
                    obj = cylinder(vec3(cell.x, 0, cell.y), vec3(cell.x, alpha*10, cell.y), rad)
                else:
                    height = 14 * float(cell.count) / float(self.num)
                    obj = brick(vec3(cell.x - c, 0, 0), vec3(cell.x + c, 1, height))
                obj.option(color=color)
                objs[id] = obj

        if self.actionViewNextNumber.isChecked(): 
            min_dir = 1000000
            max_dir = -1000000
            for cell in view_cells:
                dir = self._get_next_number_dir(self.dim, cell)
                ndir = np.linalg.norm(dir)
                if ndir < min_dir: min_dir = ndir
                if ndir > max_dir: max_dir = ndir

            for cell in view_cells:
                dir = self._get_next_number_dir(self.dim, cell)
                mod_dir = np.linalg.norm(dir)
                if min_dir < max_dir:
                    k = np.power((mod_dir*1.5 - min_dir) / (max_dir*15 - min_dir), 0.75)
                    if k <= 1.0e-6:
                        k = 0.2
                else:
                    k = 0.2
                if mod_dir < 1.0e-6:
                    continue
                dir = dir * k / mod_dir
                mod_dir = k

                base = vec3(cell.x, cell.y, cell.z)
                dir_len = 5.0
                if self.dim == 1:
                    base = vec3(cell.x, 0.0, -1.0)
                    dir_len = 3.0
                elif self.dim == 2:
                    base = vec3(cell.x, 0, cell.y)

                color = vec3(0.6, 0.8, 1.0)

                top = base + dir * dir_len * 0.6
                rad = mod_dir * 0.4 * 0.8
                obj = cylinder(top, base, rad)
                obj.option(color=color)
                id = self.config.getKey()
                objs[id] = obj

                base = top
                top = base + dir * dir_len * 0.4
                rad = mod_dir * 0.4
                obj = cone(top, base, rad) 
                obj.option(color=color)
                id = self.config.getKey()
                objs[id] = obj

        del view_cells

        dirs = [X, Y, Z]
        for dir in dirs:
            axis = Axis(vec3(0), dir)
            id = self.config.getKey()
            objs[id] = axis

        if frame > 0 and self.dim > 1:
            if not self._check_accumulate():
                cube = Box(center=vec3(0), width=frame)
            else:
                t = self.maxTime.value()
                cube = Box(center=vec3(0), width=t if frame%2 == 0 else t+c)
            id = self.config.getKey()
            objs[id] = cube

        if make_view:
            self.make_view(frame, objs)
            return None
        else:
            return objs

    def make_view(self, frame, objs=None):
        objs = objs or {}
        if not self.views:
            print("view doesn't exists...")
            self.views = Views(self, parent=self)
            self.viewLayout.addWidget(self.views)
            
        elif not self.first_number_set:
            print('setting first number...')
            self.first_number_set = True
            self.views.initialize(objs)
            if not self.histogram: self.histogram = Histogram(parent=self)
            self.histogram.set_spacetime(self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            if self.view_histogram:
                self.histogram.set_time(frame, self._check_accumulate())
                self.histogram.show()
        else:
            print('continue setting number...')
            self.views.reset(objs)
            self.histogram.set_spacetime(self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            if self.view_histogram:
                self.histogram.set_time(frame, self._check_accumulate())
                self.histogram.show()
        
        self.setStatus(f'{self.count} cells created at time {self.timeWidget.value()} for number {int(self.number.value())}...')

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
        if not self.views:
            return
        self.views.center()

    def swap_3d_view(self):
        if not self.views:
            return
        names = ['3D', '3DSPLIT']
        if not self.views.get_mode() in names:
            return
        new_mode = names[(names.index(self.views.mode) + 1) % 2]
        self.views.set_mode(new_mode)
        frame = self.time.value()
        objs = self.make_objects(frame)
        self.views.reinit(objs)
        self.reselect_cells()
        self.views.update()
        self.views.setFocus()
        collect('swap_3d_view')

    def turntable(self):
        if self.views.mode not in ['3D', '3DSPLIT']:
            return
        if self.timer.isActive():
            self.timer.stop()
            return
        self.timer.start(40)

    def rotate3DView(self):
        if self.views.mode not in ['3D', '3DSPLIT']:
            return
        self.views.rotate3DView(self.turntable_angle)
        self.update()

    def turntableFaster(self):
        self.turntable_angle *= 1.02

    def turntableSlower(self):
        self.turntable_angle /= 1.02

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
        # self.changed_spacetime = True
        self.need_compute = True
        T = int(self.period.value())
        self.spacetime = None
        self.fillDivisors(T)
        label = self.get_factors(list(self.numbers.keys())[-1])
        self.factorsLabel.setText(label)
        self.label_num_divisors.setText(f'{len(self.divisors)}')
        self.cycles = (4 if T < 8 else (3 if T < 17 else 2))
        self.maxTime.setValue(T * self.cycles)
        self.maxTime.setSingleStep(T)
        self.setStatus('Divisors computed. Select now a number from the list and press the Compute button')

    def _to_qt_list_color(self, color_name):
        return QtGui.QColor(*[int(255 * x) for x in self.config.get(color_name)])

    def fillDivisors(self, T: int):
        not_period = self._to_qt_list_color('list_color_not_period')
        not_period_prime = self._to_qt_list_color('list_color_not_period_prime')
        period_special = self._to_qt_list_color('list_color_period_special')
        period_not_special = self._to_qt_list_color('list_color_period_not_special')

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
                    item.setForeground(not_period_prime)
                else:
                    item.setForeground(not_period)
            else:
                if x in specials:
                    item.setForeground(period_special)
                    is_special = True
                elif is_prime:
                    item.setForeground(period_not_special)
            item.setData(Qt.UserRole, is_special)
            self.divisors.addItem(item)
                
    def setNumber(self, index):
        self.need_compute = True
        item = self.divisors.item(index.row())
        self.is_special = item.data(Qt.UserRole)
        self.number.setValue(int(item.text().split(' ', 1)[0]))

    def maxTimeChanged(self):
        self.changed_spacetime = True
        self.need_compute = True

    def update_view(self):
        self.draw_objects()

    def saveSpecials(self):
        widget = SaveSpecialsWidget(self, self.period.value(), 61)
        widget.show()

    def saveSpecialNumbers(self, init_period, end_period, subfolder):
        self.accumulate.setChecked(True)
        for period in range(init_period, end_period + 1, 2):
            if 46 <= period <= 48 and self.dim == 3:
                continue
            self.period.setValue(period)
            self.changed_spacetime = True
            for row in range(len(self.divisors)):
                self.need_compute = True
                item = self.divisors.item(row)
                is_special = item.data(Qt.UserRole)
                if not is_special:
                    continue
                number = int(item.text().split(' ', 1)[0])
                if number > 1650000:
                    continue
                print(f'------ saving number {number}')
                self.is_special = is_special
                self.number.setValue(number)
                self.update()
                self.compute()
                self.saveImage(subfolder=subfolder)
                print(f'------ number {number} saved')
        self.changed_spacetime = True

    def callSaveVideo(self):
        widget = SaveVideoWidget(self, self.timeWidget.value(), self.maxTime.value(), self.views.mode, self.saveVideo)
        widget.show()

    def save(self):
        number = int(self.number.value())
        if number == 0:
            QtWidgets.QMessageBox.critical(self, 'Error', 'Please, compute a number first')
            return
        period = self.period.value()
        factors = self.get_output_factors(number)
        files_path = self.config.get('files_path')
        path  = os.path.join(files_path, self._getDimStr(), f'P{period:02d}')
        if not os.path.exists(path):
            os.makedirs(path)
        file_name = os.path.join(path, f'{self._getDimStr()}_N{number:d}_P{period:02d}_F{factors}.json')
        out_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save number json file', file_name, '*.json'
        )
        if out_name:
            self.setStatus(f'Saving file: {os.path.basename(out_name)}...')
            time1 = time()
            app.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.spacetime.save(out_name)
            self.files_path = os.path.dirname(out_name)
            app.restoreOverrideCursor()
            time2 = time()
            self.setStatus(f'File {os.path.basename(out_name)} saved in {time2 - time1:0.2f} segs')

    def load(self):
        in_file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open number json file', self.files_path, '*.json'
        )
        if in_file_name:
            time1 = time()
            self.setStatus(f'Loading file {os.path.basename(in_file_name)}...')
            app.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.files_path = os.path.dirname(in_file_name)
            if not self.spacetime:
                self.spacetime = SpaceTime(2, 2, 2, 1)
            self.spacetime.load(in_file_name)
            self.dim = self.spacetime.dim
            spacetime = self.spacetime
            self._clear_parameters()
            self.spacetime = spacetime
            self.period.setValue(self.spacetime.T)
            self.spacetime = spacetime
            self.number.setValue(spacetime.n)
            self.is_special = spacetime.is_special
            self.maxTime.setValue(spacetime.max)
            self.first_number_set = False
            self.changed_spacetime = False
            self.need_compute = False
            self.time.setValue(spacetime.max)
            self.views.setFocus()
            app.restoreOverrideCursor()
            time2 = time()
            self.setStatus(f'File {os.path.basename(in_file_name)} loaded in {time2 - time1:0.2f} segs')


if __name__=="__main__":
    freeze_support()
    QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, False)
    app = QtWidgets.QApplication(sys.argv)
    settings.load(settings_file)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
