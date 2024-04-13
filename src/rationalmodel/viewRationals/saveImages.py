import os
import shutil
import math
import gc
from multiprocessing import Pool, cpu_count
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from madcad import vec3, settings, Axis, X, Y, Z, Box, cylinder, brick, icosphere, cone

from config import Config
from utils import make_video
from views import ViewRender
from spacetime import c
from spacetime import Cell

settings_file = r'settings.txt'


def _del_folder(folder):
    if not os.path.exists(folder):
        return
    names = os.listdir(folder)
    for name in names:
        path = os.path.join(folder, name)
        if os.path.isdir(path):
            _del_folder(path)
        else:
            os.remove(path)
    os.rmdir(folder)


def _makePath(accumulate, factors, image_path, dim_str, period, number, single_image=False, subfolder=''):
    if accumulate:
        if not single_image:
            path = os.path.join(image_path, f'P{period:02d}', dim_str, 'Accumulate', f'N{number:d}_F{factors}', subfolder)
        else:
            path = os.path.join(image_path, 'Snapshots', dim_str, 'Accumulate', subfolder)
    else:
        if not single_image:
            path  = os.path.join(image_path, f'P{period:02d}', dim_str, f'N{number:d}_F{factors}', subfolder)
        else:
            path = os.path.join(image_path, 'Snapshots', dim_str, 'Not Accumulate', subfolder)
    if os.path.exists(path):
        if not single_image:
            _del_folder(path)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def _get_number_img(number, period, frame):
    img = Image.new('RGBA', (500, 40), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    string = f'number: {number:,.0f} period: {period:02d} frame: {frame}'.replace(',', '.')
    width = int(draw.textlength(string) + 10)
    img.resize((width, 40))
    font = ImageFont.FreeTypeFont('NotoMono-Regular.ttf', size=24)
    draw.text((0, 0), string, font=font, fill=(0, 0, 0))
    return img


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


def make_objects(spacetime, number, dim, accumulate, config, ccolor, view_objects, view_next_number, max_time, frame):
    if not spacetime:
        return
    if number == 0:
        return
    if frame > spacetime.len():
        return

    view_cells = spacetime.getCells(frame, accumulate=accumulate)

    num = 0
    max = -1
    count = 0
    for cell in view_cells:
        num = cell.count
        if num > max:
            max = num
        if num > 0:
            count += 1
        num += num
    
    if not accumulate:
        rad_factor = config.get('rad_factor')
        rad_pow = config.get('rad_pow')
    else:
        rad_factor = config.get('rad_factor_accum')
        rad_pow = config.get('rad_pow_accum')
    rad_min = config.get('rad_min')
    max_faces = config.get('max_faces')
    faces_pow = config.get('faces_pow')

    num_id = 0

    objs = {}

    if view_objects:
        for cell in view_cells:
            alpha = float(cell.count) / float(max)
            rad = math.pow(alpha / rad_factor, rad_pow)
            if rad < rad_min:
                rad = rad_min
            color = ccolor.getColor(alpha)

            if dim == 3:
                obj = icosphere(vec3(cell.x, cell.y, cell.z), rad, resolution=('div', int(max_faces * math.pow(rad, faces_pow))))
            elif dim == 2:
                obj = cylinder(vec3(cell.x, 0, cell.y), vec3(cell.x, alpha*10, cell.y), rad)
            else:
                height = 5 * float(cell.count) / float(num)
                obj = brick(vec3(cell.x - c, 0, 0), vec3(cell.x + c, 1, height))
            obj.option(color=color)
            objs[num_id] = obj
            num_id += 1

    if view_next_number: 
        min_dir = 1000000
        max_dir = -1000000
        for cell in view_cells:
            dir = _get_next_number_dir(dim, cell)
            ndir = np.linalg.norm(dir)
            if ndir < min_dir: min_dir = ndir
            if ndir > max_dir: max_dir = ndir

        for cell in view_cells:
            dir = _get_next_number_dir(dim, cell)
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
            if dim == 1:
                base = vec3(cell.x, 0.0, -1.0)
                dir_len = 3.0
            elif dim == 2:
                base = vec3(cell.x, 0, cell.y)

            color = vec3(0.6, 0.8, 1.0)

            top = base + dir * dir_len * 0.6
            rad = mod_dir * 0.4 * 0.8
            obj = cylinder(top, base, rad)
            obj.option(color=color)
            objs[num_id] = obj
            num_id += 1

            base = top
            top = base + dir * dir_len * 0.4
            rad = mod_dir * 0.4
            obj = cone(top, base, rad) 
            obj.option(color=color)
            objs[num_id] = obj
            num_id += 1

    del view_cells

    dirs = [X, Y, Z]
    for dir in dirs:
        axis = Axis(vec3(0), dir)
        objs[num_id] = axis
        num_id += 1

    if frame > 0 and dim > 1:
        if not accumulate:
            cube = Box(center=vec3(0), width=frame)
        else:
            t = max_time
            cube = Box(center=vec3(0), width=t if frame%2 == 0 else t+c)
        objs[num_id] = cube
        num_id += 1

    return objs


def _create_image(args):
    view_type, projection, navigation, \
    time, factor, init_time, prefix, suffix, config, ccolor, spacetime, dim, number, \
    period, factors, accumulate, dim_str, view_objects, view_next_number, max_time, \
    image_resx, image_resy, path, rotate, dx = args

    settings.load(settings_file)

    view = ViewRender(view_type)
    view.set_projection(projection)
    view.set_navigation(navigation)
    if rotate:
        view.render_view.navigation.yaw = dx*math.pi

    frame = init_time + time // factor
    objs = make_objects(spacetime, number, dim, accumulate, config, ccolor, view_objects, view_next_number, max_time, frame)
    if not objs:
        print('------ NOT OBJS')
        return

    img = view.render(image_resx, image_resy, objs)
    if not img:
        print('------- NOT IMG')
        return
    
    accum_str = ''
    if accumulate:
        accum_str = 'Accum_'

    file_name = f'{accum_str}{prefix}{dim_str}_N{int(number)}_P{int(period):02d}_F{factors}{suffix}.{time:04d}.png'

    number_img = _get_number_img(number, period, frame)
    img.alpha_composite(number_img, (10, image_resy - 40))
    del number_img

    fname = os.path.join(path, file_name)
    print(f'------- save: {file_name}')
    img.save(fname)

    del objs
    del view
    del img
    gc.collect()

    return


def _saveImages(args):
    projection, navigation, image_path, init_time, end_time, \
    subfolder, prefix, suffix, num_frames, turn_angle, config, \
    ccolor, view_type, spacetime, dim, number, period, factors, \
    accumulate, dim_str, view_objects, view_next_number, max_time = args
    
    number = int(number)
    period = int(period)

    if prefix and prefix[-1] != '_':
        prefix = prefix + '_'

    if suffix and suffix[0] != '_':
        suffix = '_' + suffix

    single_image = True if num_frames == 1 else False
    path = _makePath(accumulate, factors, image_path, dim_str, period, number, single_image, subfolder)

    image_resx = config.get('image_resx')
    image_resy = config.get('image_resy')
    if accumulate and turn_angle == 0.:
        frame_rate = config.get('frame_rate_accum')
    else:
        frame_rate = config.get('frame_rate')
        if turn_angle == 0.0 and num_frames > 1 and end_time > init_time:
            frame_rate = float(end_time - init_time) / float(num_frames)
            num_frames = end_time - init_time
    ffmpeg_path = config.get('ffmpeg_path')
    video_path = config.get('video_path')
    video_format = config.get('video_format')
    video_codec = config.get('video_codec')
    bit_rate = config.get('bit_rate')

    if num_frames == 0:
        num_frames = end_time - init_time + 1

    factor = 1
    if init_time < end_time:
        factor = 1 + num_frames // (end_time - init_time + 1)
    else:
        factor = num_frames

    if num_frames == 1 and init_time == end_time:
        range_frames = 1
    else:
        range_frames = num_frames + 1

    params = []
    for time in range(range_frames):
        rotate = False
        dx = navigation.yaw / math.pi
        if turn_angle > 0:
            k = 0.005 * 400. / 360.
            dx += time * k * float(turn_angle) / float(num_frames)
            rotate = True
        params.append((
            view_type, projection, navigation, 
            time, factor, init_time, prefix, suffix, config, ccolor, spacetime, dim, number, 
            period, factors, accumulate, dim_str, view_objects, view_next_number, max_time, 
            image_resx, image_resy, path, rotate, dx
        ))

    num_cpus = min(cpu_count()-4, range_frames)
    pool = Pool(num_cpus)
    pool.imap(func=_create_image, iterable=params)
    pool.close()
    pool.join()

    del params

    # if there are more than one images, save video
    if not single_image:

        accum_str = ''
        if accumulate:
            accum_str = 'Accum_'

        in_sequence_name = os.path.join(path, f'{accum_str}{prefix}{dim_str}_N{number}_P{period:02d}_F{factors}{suffix}.%04d.png')
        main_video_name = os.path.join(path, f'{accum_str}{prefix}{dim_str}_N{number:d}_P{period:02d}_F{factors}{suffix}.{video_format}')
        result = make_video(
            ffmpeg_path, 
            in_sequence_name, main_video_name, 
            video_codec, video_format, 
            frame_rate, bit_rate, 
            image_resx, image_resy
        )
        if not result:
            return

        out_video_path = os.path.join(video_path, f'{dim_str}')
        if not os.path.exists(out_video_path):
            os.makedirs(out_video_path)
        dest_video_name = os.path.join(out_video_path, f'{accum_str}{prefix}{dim_str}_N{number:d}_P{period:02d}_F{factors}{suffix}.{video_format}')
        print(f'------- copying {main_video_name} \n-------      to {dest_video_name}')
        shutil.copyfile(main_video_name, dest_video_name)

