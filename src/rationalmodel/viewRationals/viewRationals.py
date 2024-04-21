import os
import sys
from time import time, sleep
from multiprocessing import freeze_support, Manager
from threading import Thread
from copy import deepcopy
from multiprocessing import managers

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import numpy as np
from madcad import vec3, settings
from mainWindowUi import MainWindowUI
from views import Views
from saveSpecials import SaveSpecialsWidget
from saveVideo import SaveVideoWidget
from saveImages import make_objects
from spacetime_index import SpaceTime
from rationals import c
from utils import getDivisorsAndFactors, divisors, make_video, collect
from timing import timing, get_duration
from config import config
from color import ColorLine
from histogram import Histogram
from saveImages import _saveImages, _create_video


settings_file = r'settings.txt'
opengl_version = (3,3)

class MyManager(managers.BaseManager):
	...

MyManager.register('SpaceTime', SpaceTime)


class VideoThread(Thread):
    def __init__(self, parent, func_process, args_process, func_video, single_image):
        super().__init__()
        self.parent = parent
        self.func_process = func_process
        self.args_process = args_process
        self.func_video = func_video
        self.processes = None
        self.killed = False
        self.single_image = single_image
    
    def run(self):
        self.parent.setStatus(f'Creating video sequence, please wait...')
        self.processes = self.func_process(self.args_process)
        self.processes[0].close()
        self.processes[0].join()
        if self.processes[1] and not self.killed and not self.single_image:
            self.func_video(self.processes[1])
            self.parent.setStatus(f'Video saved for number {int(self.parent.number.value()):d} in {get_duration():.2f} secs')
        elif not self.killed:
            self.parent.setStatus(f'Image saved for number {int(self.parent.number.value()):d} in {get_duration():.2f} secs')
        else:
            self.killed = False
        self.parent.shr_num_video_frames.value = -1
        del self.args_process
        del self.processes
        collect()

    def kill(self):
        if self.processes:
            self.parent.setStatus('VIDEO CREATION CANCELLED...')
            self.killed = True
            self.processes[0].terminate()
            self.processes[0].close()
            self.processes[0].join()
            self.parent.cancelVideo()
            del self.processes
            collect()
            

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
        self.timer_video = QtCore.QTimer(self)
        self.timer_video.timeout.connect(self.message_video)
        self.turntable_angle = 0.005
        self.first_number_set = False
        self.changed_spacetime = True
        self.need_compute = True
        self.histogram = None
        self.view_histogram = True
        self.view_objects = True
        self.view_time = False
        self.view_next_number = False
        self.manager = MyManager()
        self.manager.start()
        self.spacetime: SpaceTime = self.manager.SpaceTime(2, 2, 2, 1)
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

    def moveNextCycle(self):
        frame = self.timeWidget.value()
        T = self.period.value()
        cycle = frame // T
        frame = (cycle + 1) * T
        if frame < self.maxTime.value():
            self.timeWidget.setValue(frame)
        else:
            self.timeWidget.setValue(self.maxTime.value())

    def movePrevCycle(self):
        frame = self.timeWidget.value()
        T = self.period.value()
        cycle = frame // T
        if frame % T == 0:
            frame = (cycle - 1) * T
        else:
            frame = cycle * T
        if frame > 0:
            self.timeWidget.setValue(frame)
        else:
            self.timeWidget.setValue(0)

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
        single_image = False
        if num_frames == 1:
            single_image = True
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

        manager = Manager()
        projection = self.views.views[self.views.mode].view.projection
        navigation = self.views.views[self.views.mode].view.navigation
        shr_projection = manager.Value(type(projection), projection)
        shr_navigation = manager.Value(type(navigation), navigation)
        self.num_video_frames = 0
        self.max_video_frames = deepcopy(num_frames)
        self.shr_num_video_frames = manager.Value(int, self.num_video_frames)

        args = (
            shr_projection,
            shr_navigation,
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
            self.spacetime,
            self.dim,
            self.number.value(),
            self.period.value(),
            self.get_output_factors(self.number.value()),
            self._check_accumulate(),
            self._getDimStr(),
            self.actionViewObjects.isChecked(),
            self.actionViewTime.isChecked(),
            self.actionViewNextNumber.isChecked(),
            self.maxTime.value(),
            self.shr_num_video_frames
        )

        self.timer_video.start(1000)
        self.video_thread = VideoThread(self, _saveImages, args, _create_video, single_image)
        self.video_thread.start()

        app.restoreOverrideCursor()

    def cancelVideo(self):
        self.timer_video.stop()
        if self.video_thread:
            self.video_thread.kill()

    def message_video(self):
        if self.shr_num_video_frames.value < 0:
            self.timer_video.stop()
        elif self.shr_num_video_frames.value == 0:
            self.setStatus('Initializing video creation. Please wait...')
        else:
            self.setStatus(f'Creating video, num frames: {self.shr_num_video_frames.value} / {self.max_video_frames}')

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
        max = self.number.value() or 1
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
            self.setStatus('Creating incremental spacetime...')
            self.spacetime.reset(self.period.value(), n, self.maxTime.value(), dim=self.dim)
            self.changed_spacetime = False
            self.need_compute = False

        self.spacetime.clear()

        self.setStatus(f'Setting rational set for number: {n} ...')
        self.spacetime.setRationalSet(n, self.is_special)

        self.setStatus(f'Adding rational set for number: {n}...')
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

    @timing
    def draw_objects(self, frame=0):
        frame = self.timeWidget.value()
        objs, count_cells, self.cell_ids = make_objects(
            self.spacetime,
            self.number.value(),
            self.dim,
            self._check_accumulate(),
            self.config,
            self.color,
            self.view_objects,
            self.view_time,
            self.view_next_number, 
            self.maxTime.value(),
            frame
        )
        self.make_view(objs=objs, count_cells=count_cells)
        del objs
        collect()

    @timing
    def make_objects(self, frame):
        objs, _, _ = make_objects(
            self.spacetime,
            self.number.value(),
            self.dim,
            self._check_accumulate(),
            self.config,
            self.color,
            self.view_objects,
            self.view_time,
            self.view_next_number, 
            self.maxTime.value(),
            frame
        )
        return objs

    def make_view(self, objs=None, count_cells=0):
        objs = objs or {}
        if not self.views:
            print("view doesn't exists...")
            self.views = Views(self, parent=self)
            self.viewLayout.addWidget(self.views)
            
        elif not self.first_number_set:
            print('setting first number...')
            self.first_number_set = True
            self.views.initialize(objs)
            if not self.histogram: 
                self.histogram = Histogram(self, self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            if self.view_histogram:
                self.histogram.set_time(self._check_accumulate())
                self.histogram.show()
        else:
            print('continue setting number...')
            self.views.reset(objs)
            self.histogram.set_number(int(self.number.value()))
            if self.view_histogram:
                self.histogram.set_time(self._check_accumulate())
                self.histogram.show()
        
        self.setStatus(f'{count_cells} cells created at time {self.timeWidget.value()} for number {int(self.number.value())}...')

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
        self.need_compute = True
        T = int(self.period.value())
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

    def update_view_objects(self):
        if self.view_objects:
            self.view_objects = False
        else:
            self.view_objects = True
        self.view_time = False
        self.actionViewObjects.setChecked(self.view_objects)
        self.actionViewTime.setChecked(self.view_time)
        self.draw_objects()

    def update_view_time(self):
        if self.view_time:
            self.view_time = False
        else:
            self.view_time = True
        self.view_objects = False
        self.actionViewObjects.setChecked(self.view_objects)
        self.actionViewTime.setChecked(self.view_time)
        self.draw_objects()

    def update_view_next_number(self):
        self.view_next_number = not self.view_next_number
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
            self.spacetime.load(in_file_name)
            T, n, max, dim, is_special = self.spacetime.getParams()
            self.dim = dim
            spacetime = self.spacetime
            self._clear_parameters()
            self.spacetime = spacetime
            self.period.setValue(T)
            self.spacetime = spacetime
            self.number.setValue(n)
            self.is_special = is_special
            self.maxTime.setValue(max)
            self.first_number_set = False
            self.changed_spacetime = False
            self.need_compute = False
            self.time.setValue(max)
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
