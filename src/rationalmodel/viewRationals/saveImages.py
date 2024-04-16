import os
import shutil
import math
import time
from multiprocessing import Pool, cpu_count
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from madcad import vec3, settings, Axis, X, Y, Z, Box, cylinder, brick, icosphere, cone

from views import ViewRender
from makeObjects import make_objects
from utils import make_video, collect
from timing import timing

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


def _get_number_img(number, period, ptime):
    img = Image.new('RGBA', (500, 40), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    string = f'number: {number:,.0f} period: {period:02d} time: {ptime}'.replace(',', '.')
    width = int(draw.textlength(string) + 10)
    img.resize((width, 40))
    font = ImageFont.FreeTypeFont('NotoMono-Regular.ttf', size=24)
    draw.text((0, 0), string, font=font, fill=(0, 0, 0))
    return img


def _create_image(args):
    view_type, projection, navigation, frame, factor, init_time, prefix, suffix, \
    config, ccolor, spacetime, dim, number, period, factors, accumulate, dim_str, \
    view_objects, view_time, view_next_number, max_time, \
    image_resx, image_resy, path, rotate, dx = args

    settings.load(settings_file)

    view = ViewRender(view_type)
    view.set_projection(projection)
    view.set_navigation(navigation)
    if rotate:
        view.rotateTo3DVideo(dx)

    ptime = init_time + frame // factor
    objs, _, _ = make_objects(spacetime, number, dim, accumulate, config, ccolor, view_objects, view_time, view_next_number, max_time, ptime)
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

    file_name = f'{accum_str}{prefix}{dim_str}_N{int(number)}_P{int(period):02d}_F{factors}{suffix}.{frame:04d}.png'

    number_img = _get_number_img(number, period, ptime)
    img.alpha_composite(number_img, (10, image_resy - 40))
    del number_img

    fname = os.path.join(path, file_name)
    print(f'------- save: {file_name}, time: {ptime}')
    img.save(fname)

    del args
    del objs
    del view
    del img
    collect()

    return


def _create_video(args):
    print('------- CREATING VIDEO')

    path, image_resx, image_resy, init_time, end_time, \
    prefix, suffix, num_frames, turn_angle, config, \
    number, period, factors, accumulate, dim_str = args

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
        print('------- ERROR: Error creating video')
        return

    out_video_path = os.path.join(video_path, f'{dim_str}')
    if not os.path.exists(out_video_path):
        os.makedirs(out_video_path)
    dest_video_name = os.path.join(out_video_path, f'{accum_str}{prefix}{dim_str}_N{number:d}_P{period:02d}_F{factors}{suffix}.{video_format}')
    print(f'------- copying {main_video_name} \n-------      to {dest_video_name}')
    shutil.copyfile(main_video_name, dest_video_name)

    del args
    collect('save video')


@timing
def _saveImages(args):

    projection, navigation, image_path, init_time, end_time, \
    subfolder, prefix, suffix, num_frames, turn_angle, config, \
    ccolor, view_type, spacetime, dim, number, period, factors, \
    accumulate, dim_str, view_objects, view_time, view_next_number, \
    max_time = args
    
    number = int(number)
    period = int(period)

    if prefix and prefix[-1] != '_':
        prefix = prefix + '_'

    if suffix and suffix[0] != '_':
        suffix = '_' + suffix

    single_image = True if num_frames == 1 else False
    try:
        path = _makePath(accumulate, factors, image_path, dim_str, period, number, single_image, subfolder)
    except Exception as e:
        print(f'ERROR: {str(e)}')

    image_resx = config.get('image_resx')
    image_resy = config.get('image_resy')

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
    for frame in range(range_frames):
        rotate = False
        dx = navigation.yaw / math.pi
        if turn_angle > 0:
            k = 0.005 * 400. / 360.
            dx += frame * k * float(turn_angle) / float(num_frames)
            rotate = True
        params.append((
            view_type, projection, navigation, frame, factor, init_time, prefix, suffix,
            config, ccolor, spacetime, dim, number, period, factors, accumulate, dim_str,
            view_objects, view_time, view_next_number, max_time,
            image_resx, image_resy, path, rotate, dx            
        ))

    num_cpus = int(cpu_count() * 0.8)
    chunksize = (range_frames // num_cpus) or 1
    print(f'------- range_frames: {range_frames}, num_cpus: {num_cpus}, chunksize: {chunksize}')
    
    pool = Pool(num_cpus)
    pool.imap(func=_create_image, iterable=params, chunksize=chunksize)
    args_video = (
        path, image_resx, image_resy, init_time, end_time,
        prefix, suffix, num_frames, turn_angle, config,
        number, period, factors, accumulate, dim_str
    ) if not single_image else ()
    return (pool, args_video)
