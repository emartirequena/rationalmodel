import os
import sys
import math
import shutil
from copy import deepcopy
import gc
from multiprocessing import freeze_support
from PyQt5.QtWidgets import QWidget

from madcad import vec3, rendering, settings, uvsphere, Axis, X, Y, Z, Box, cylinder, brick, fvec3, text
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

from mainWindowUi import MainWindowUI
from mainView import MainView
from renderView import RenderView
from saveSpecials import SaveSpecialsWidget
from spacetime import SpaceTime
from rationals import c
from utils import getDivisorsAndFactors, divisors, make_video, timing
from config import Config
from color import ColorLine
from histogram import Histogram

settings_file = r'settings.txt'

opengl_version = (3,3)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = MainWindowUI()
        self.ui.setUpUi(self)
        self.dim = 3
        self.count = 0
        self.objs = {}
        self.cell_ids = {}
        self.selected = {}
        self.view = None
        self.first_number_set = False
        self.changed_spacetime = True
        self.need_compute = True
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
        dims = ['1D', '2D', '3D']
        return dims[self.dim - 1]

    def _makePath(self, period, number, single_image=False, subfolder=''):
        factors = self.get_output_factors(number)
        image_path = self.config.get('image_path')
        if self._check_accumulate():
            if not single_image:
                path = os.path.join(image_path, f'P{period:02d}', self._getDimStr(), 'Accumulate', f'N{number:d}_F{factors}')
            else:
                path = os.path.join(image_path, 'Snapshots', self._getDimStr(), 'Accumulate', subfolder)
        else:
            if not single_image:
                path  = os.path.join(image_path, f'P{period:02d}', self._getDimStr(), f'N{number:d}_F{factors}')
            else:
                path = os.path.join(image_path, 'Snapshots', self._getDimStr(), 'Not Accumulate', subfolder)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def _get_number_img(self):
        img = Image.new('RGBA', (500, 40), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        string = f'number: {self.number.value():,.0f} period: {self.period.value():02d}'.replace(',', '.')
        width = draw.textlength(string) + 10
        img.resize((width, 40))
        font = ImageFont.FreeTypeFont('NotoMono-Regular.ttf', size=24)
        draw.text((0, 0), string, font=font, fill=(255, 255, 255, 255))
        return img

    def _saveImages(self, init_time, end_time, subfolder=''):
        self.setStatus('Saving images...')
        
        projection = deepcopy(self.view.projection)
        navigation = deepcopy(self.view.navigation)
        
        number = int(self.number.value())
        period = self.period.value()
        factors = self.get_output_factors(number)

        single_image = True if init_time == end_time else False
        path = self._makePath(period, number, single_image=single_image, subfolder=subfolder)
        image_resx = self.config.get('image_resx')
        image_resy = self.config.get('image_resy')
        histogram_resx = self.config.get('histogram_resx')
        histogram_resy = self.config.get('histogram_resy')
        if self._check_accumulate():
            frame_rate = self.config.get('frame_rate_accum')
        else:
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
            
            file_name = f'{self._getDimStr()}_N{number}_P{period:02d}_F{factors}.{time:04d}.png'
            if self.view_histogram:
                hist_name = 'Hist_' + file_name
                hist_img = self.histogram.get_save_image(time)
                img.alpha_composite(hist_img)
                if self._check_accumulate():
                    hist_name = 'Accum_' + hist_name
                hist_img.save(os.path.join(path, hist_name))

            if init_time == end_time:
                number_img = self._get_number_img()
                img.alpha_composite(number_img, (10, image_resy - 40))

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
                in_sequence_name = os.path.join(path, f'{self._getDimStr()}_N{number}_P{period:02d}_F{factors}.%04d.png')
                main_video_name = os.path.join(path, f'{self._getDimStr()}_N{number:d}_P{period:02d}_F{factors}.{video_format}')
                self.setStatus('Making main sequence video...')
                result = make_video(
                    ffmpeg_path, 
                    in_sequence_name, main_video_name, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    image_resx, image_resy
                )
                if not result:
                    self.setStatus('ffmepg not found... (check config.json file specification)')
                    return

                in_sequence_name = os.path.join(path, f'Hist_{self._getDimStr()}_N{number}_P{period:02d}_F{factors}.%04d.png')
                hist_video_name = os.path.join(path, f'Hist_{self._getDimStr()}_N{number:d}_P{period:02d}_F{factors}.{video_format}')
                self.setStatus('Making histogram video...')
                make_video(
                    ffmpeg_path, 
                    in_sequence_name, hist_video_name, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    histogram_resx, histogram_resy
                )

                self.setStatus('Copying video...')
                out_video_path = os.path.join(video_path, f'{self._getDimStr()}')
                if not os.path.exists(out_video_path):
                    os.makedirs(out_video_path)
                dest_video_name = os.path.join(out_video_path, f'{self._getDimStr()}_N{number:d}_P{period:02d}_F{factors}.{video_format}')
                shutil.copyfile(main_video_name, dest_video_name)

            else:
                in_sequence_name = os.path.join(path, f'Accum_{self._getDimStr()}_N{number}_P{period:02d}_F{factors}.%04d.png')
                main_video_name = os.path.join(path, f'Accum_{self._getDimStr()}_N{number:d}_P{period:02d}_F{factors}.{video_format}')
                self.setStatus('Making main sequence video...')
                result = make_video(
                    ffmpeg_path, 
                    in_sequence_name, main_video_name, 
                    video_codec, video_format, 
                    frame_rate, bit_rate, 
                    image_resx, image_resy
                )
                if not result:
                    self.setStatus('ffmepg not found... (check config.json file specification)')
                    return

                self.setStatus('Copying video...')
                out_video_path = os.path.join(video_path, f'{self._getDimStr()}')
                if not os.path.exists(out_video_path):
                    os.makedirs(out_video_path)
                dest_video_name = os.path.join(out_video_path, f'Accum_{self._getDimStr()}_N{number:d}_P{period:02d}_F{factors}.{video_format}')
                shutil.copyfile(main_video_name, dest_video_name)

            self.setStatus('Videos saved...')

    def saveImage(self, subfolder=''):
        if subfolder == False: subfolder = ''
        self.deselect_all()
        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        self._saveImages(self.time.value(), self.time.value(), subfolder)
        self.make_objects()
        app.restoreOverrideCursor()

    def saveVideo(self):
        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        if self._check_accumulate():
            self._saveImages(0, 6)
        else:
            self._saveImages(0, self.maxTime.value())
        self.make_objects()
        app.restoreOverrideCursor()

    def _switch_display(self, count, state=None):
        for id in self.cell_ids[count]:
            if len(self.view.scene.item([0])) == 1:
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
        
        print(f'need_compute: {self.need_compute}, changed_spacetime: {self.changed_spacetime}')
        
        if not self.need_compute:
            self.make_objects()
            self.period_changed = False
            return
        self.need_compute = False

        app.setOverrideCursor(QtCore.Qt.WaitCursor)

        self.deselect_all()

        if self.changed_spacetime:
            if self.spacetime is not None:
                if self.histogram is not None:
                    self.histogram.set_spacetime(None)
                del self.spacetime
                self.spacetime = None
                gc.collect(2)

            self.setStatus('Creating incremental spacetime...')
            self.spacetime = SpaceTime(self.period.value(), self.maxTime.value(), dim=self.dim)
        else:
            self.spacetime.clear()
        self.changed_spacetime = False

        self.setStatus(f'Setting rational set for number: {int(self.number.value())} ...')
        self.spacetime.setRationalSet(int(self.number.value()))

        self.setStatus('Adding rational set...')
        self.spacetime.addRationalSet(self.is_special)
        self.setStatus(f'Rational set added for number {int(self.number.value())}')
    
        self.timeWidget.setValue(self.maxTime.value() if self.period_changed else self.time.value())
        self.timeWidget.setFocus()

        if self.time.value() != self.maxTime.value():
            self.time.setValue(self.maxTime.value())
        else:
            self.make_objects()

        app.restoreOverrideCursor()

    @timing
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
                cube = Box(center=vec3(0), width=t if frame%2 == 0 else t+c)
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
        self.changed_spacetime = True
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
        self.setStatus('Divisors computed. Select now a number on the list and press \bCompute\b button')

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
        self.need_compute = True
        item = self.divisors.item(index.row())
        self.is_special = item.data(Qt.UserRole)
        self.number.setValue(int(item.text().split(' ', 1)[0]))

    def maxTimeChanged(self):
        self.changed_spacetime = True
        self.need_compute = True

    def saveSpecials(self):
        widget = SaveSpecialsWidget(self, self.period.value(), 61)
        widget.show()

    def saveSpecialsNumbers(self, init_period, end_period, subfolder):
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


if __name__=="__main__":
    QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QtWidgets.QApplication(sys.argv)
    freeze_support()
    settings.load(settings_file)
    wi = MainWindow()
    wi.show()
    sys.exit(app.exec())
