import os
import sys
import math
import shutil
import time
from copy import deepcopy
import gc
from multiprocessing import freeze_support

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from madcad import vec3, settings, Axis, X, Y, Z, Box, cylinder, brick, icosphere, cone

from mainWindowUi import MainWindowUI
from views import Views
from saveSpecials import SaveSpecialsWidget
from spacetime import SpaceTime, Cell
from rationals import c
from utils import getDivisorsAndFactors, divisors, make_video
from timing import timing
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
        self.factors = ''
        self.num = 0
        self.numbers = {}
        self.config = Config()
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
        self.objs = {}
        self.cell_ids = {}
        self.selected = {}
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

    def _makePath(self, image_path, period, number, single_image=False, subfolder=''):
        factors = self.get_output_factors(number)
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
        if os.path.exists(path) and not single_image:
            for name in os.listdir(path):
                os.remove(os.path.join(path, name))
            os.rmdir(path)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def _get_number_img(self):
        img = Image.new('RGBA', (500, 40), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        string = f'number: {self.number.value():,.0f} period: {self.period.value():02d}'.replace(',', '.')
        width = int(draw.textlength(string) + 10)
        img.resize((width, 40))
        font = ImageFont.FreeTypeFont('NotoMono-Regular.ttf', size=24)
        draw.text((0, 0), string, font=font, fill=(255, 255, 255, 255))
        return img

    def _saveImages(self, image_path, init_time, end_time, subfolder=''):
        self.setStatus('Saving images...')
        
        number = int(self.number.value())
        period = self.period.value()
        factors = self.get_output_factors(number)

        single_image = True if init_time == end_time else False
        path = self._makePath(image_path, period, number, single_image=single_image, subfolder=subfolder)
        image_resx = self.config.get('image_resx')
        image_resy = self.config.get('image_resy')
        histogram_resx = self.config.get('histogram_resx')
        histogram_resy = self.config.get('histogram_resy')
        frame_rate = 1.0
        if self._check_accumulate():
            frame_rate = self.config.get('frame_rate_accum')
        else:
            frame_rate = self.config.get('frame_rate')
        ffmpeg_path = self.config.get('ffmpeg_path')
        video_path = self.config.get('video_path')
        video_format = self.config.get('video_format')
        video_codec = self.config.get('video_codec')
        bit_rate = self.config.get('bit_rate')

        self.histogram.prepare_save_image()

        rotate = False
        dx = 0.0
        if (
            self.views.mode in ['3D', '3DSPLIT'] and 
            init_time != end_time and 
            self.action3DTurntable.isChecked()
        ):
            dx = 2.0 / float(end_time - init_time + 1)
            frame_rate = 12.0
            if self._check_accumulate():
                objs = self.make_objects(frame=self.time.value() % 2, make_view=False)
            rotate = True
        else:
            objs = self.make_objects(frame=self.time.value(), make_view=False)

        for time in range(init_time, end_time + 1):
            factor = 1
            if (
                self.views.mode in ['3D', '3DSPLIT'] and 
                init_time != end_time and 
                self.action3DTurntable.isChecked()
            ):
                factor = 6
            if (
                self.views.mode in ['3D', '3DSPLIT'] and 
                init_time != end_time and 
                self.action3DTurntable.isChecked() and 
                self._check_accumulate()
            ):
                frame = self.time.value() % 2
            else:
                frame = time
                if frame % factor == 0 and not self._check_accumulate():
                    objs = self.make_objects(frame=frame // factor, make_view=False)
                    # gc.collect()
            img = self.views.render(image_resx, image_resy, objs)
            
            file_name = f'{self._getDimStr()}_N{number}_P{period:02d}_F{factors}.{time:04d}.png'
            if self.view_histogram:
                hist_name = 'Hist_' + file_name
                hist_img = self.histogram.get_save_image(frame // factor)
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

            if rotate:
                self.views.rotate3DVideo(dx)
                self.setStatus(f'Saving frame {time} / {end_time - init_time}')
            
        self.histogram.end_save_image()

        # gc.collect()
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

                if self.view_histogram:
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
        frame = self.time.value()
        image_path = self.config.get('image_path')
        self._saveImages(image_path, frame, frame, subfolder)
        self.make_objects()
        app.restoreOverrideCursor()

    def saveVideo(self):
        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        image_path = self.config.get('image_path')
        if self._check_accumulate():
            if self.views.mode in ['3D', '3DSPLIT'] and self.action3DTurntable.isChecked():
                self._saveImages(image_path, 0, 50)
            else:
                self._saveImages(image_path, 0, 6)
        else:
            factor = 1
            if self.views.mode in ['3D', '3DSPLIT'] and self.action3DTurntable.isChecked():
                factor = 6
            self._saveImages(image_path, 0, self.maxTime.value() * factor)
        self.make_objects()
        app.restoreOverrideCursor()

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
        # gc.collect()       
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
            self.make_objects()
            self.period_changed = False
            return
        self.need_compute = False

        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        time1 = time.time()

        self.deselect_all()

        n = int(self.number.value())

        if self.spacetime is not None:
            if self.histogram is not None:
                self.histogram.set_spacetime(None)
            del self.spacetime
            self.spacetime = None
            gc.collect(2)

        self.setStatus('Creating incremental spacetime...')
        self.spacetime = SpaceTime(self.period.value(), n, self.maxTime.value(), dim=self.dim)
        self.changed_spacetime = False

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
            self.make_objects()

        gc.collect()
        
        time2 = time.time()
        self.setStatus(f'Rationals set for number {n:,.0f} computed in {time2-time1:,.2f} secs')

        app.restoreOverrideCursor()

    def _get_next_number_dir(self, cell: Cell):
        if self.dim == 1:
            v1 = np.array([ 1,  0,  0]) * cell.next_digits[0]
            v2 = np.array([-1,  0,  0]) * cell.next_digits[1]
            v = (v1 + v2) / 2.0
        elif self.dim == 2:
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

        self.cell_ids = {}
        self.objs = {}
        # self.config.resetKey()

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
                    obj = brick(vec3(cell.x - c, 0, 0), vec3(cell.x + c, 1, alpha*10))
                obj.option(color=color)
                self.objs[id] = obj

        if self.actionViewNextNumber.isChecked(): 
            min_dir = 1000000
            max_dir = -1000000
            for cell in view_cells:
                dir = self._get_next_number_dir(cell)
                ndir = np.linalg.norm(dir)
                if ndir < min_dir: min_dir = ndir
                if ndir > max_dir: max_dir = ndir

            if min_dir < max_dir:
                for cell in view_cells:
                    dir = self._get_next_number_dir(cell)
                    mod_dir = np.linalg.norm(dir)
                    k = np.power((mod_dir*1.5 - min_dir) / (max_dir*15 - min_dir), 0.75)
                    if k <= 1.0e-6:
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
                    self.objs[id] = obj

                    base = top
                    top = base + dir * dir_len * 0.4
                    rad = mod_dir * 0.4
                    obj = cone(top, base, rad) 
                    obj.option(color=color)
                    id = self.config.getKey()
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

    @timing
    def make_view(self, frame):
        if not self.views:
            print("view doesn't exists...")
            self.views = Views(self, parent=self)
            self.viewLayout.addWidget(self.views)
            
        elif not self.first_number_set:
            print('setting first number...')
            self.first_number_set = True
            self.views.initialize(self.objs)
            if not self.histogram: self.histogram = Histogram(parent=self)
            self.histogram.set_spacetime(self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            if self.view_histogram:
                self.histogram.set_time(frame, self._check_accumulate())
                self.histogram.show()
        else:
            print('continue setting number...')
            self.views.reset(self.objs)
            self.histogram.set_spacetime(self.spacetime)
            self.histogram.set_number(int(self.number.value()))
            if self.view_histogram:
                self.histogram.set_time(frame, self._check_accumulate())
                self.histogram.show()
        
        # gc.collect()
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
        self.views.reinit(self.objs)
        self.reselect_cells()
        self.views.update()
        self.views.setFocus()

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
        self.setStatus('Divisors computed. Select now a number from the list and press the Compute button')

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

    def update_view(self):
        self.make_objects()

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
            time1 = time.time()
            app.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.spacetime.save(out_name)
            self.files_path = os.path.dirname(out_name)
            app.restoreOverrideCursor()
            time2 = time.time()
            self.setStatus(f'File {os.path.basename(out_name)} saved in {time2 - time1:0.2f} segs')

    def load(self):
        in_file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open number json file', self.files_path, '*.json'
        )
        if in_file_name:
            time1 = time.time()
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
            del self.objs
            self.objs = None
            # gc.collect()
            self.first_number_set = False
            self.changed_spacetime = False
            self.need_compute = False
            self.time.setValue(spacetime.max)
            self.views.setFocus()
            app.restoreOverrideCursor()
            time2 = time.time()
            self.setStatus(f'File {os.path.basename(in_file_name)} loaded in {time2 - time1:0.2f} segs')


if __name__=="__main__":
    QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, False)
    app = QtWidgets.QApplication(sys.argv)
    freeze_support()
    settings.load(settings_file)
    wi = MainWindow()
    wi.show()
    sys.exit(app.exec())
