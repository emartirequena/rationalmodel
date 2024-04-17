import numpy as np
import math
from madcad import icosphere, icosahedron, brick, vec3, cylinder, cone, Box, Axis, X, Y, Z
from spacetime import Cell, c


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


def make_objects(spacetime, number, dim, accumulate, config, ccolor, view_objects, view_time, view_next_number, max_time, ptime):
    if not spacetime:
        return {}, 0, {}
    if number == 0:
        return {}, 0, {}
    if ptime > spacetime.len():
        return {}, 0, {}

    view_cells = spacetime.getCells(ptime, accumulate=accumulate)
    count = len(view_cells)

    if not accumulate:
        rad_factor = config.get('rad_factor')
        rad_pow = config.get('rad_pow')
    else:
        rad_factor = config.get('rad_factor_accum')
        rad_pow = config.get('rad_pow_accum')
    rad_min = config.get('rad_min')
    max_faces = config.get('max_faces')
    faces_pow = config.get('faces_pow')

    total = 0
    max = -1
    count = 0
    for cell in view_cells:
        if cell.count > max:
            max = cell.count
        if cell.count > 0:
            count += 1
        total += cell.count

    max_spaces_time = spacetime.getMaxTime(accumulate)
    
    num_id = 0
    objs = {}
    cell_ids = {}

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
                height = 14 * float(cell.count) / float(total)
                obj = brick(vec3(cell.x - c, 0, 0), vec3(cell.x + c, 1, height))
            obj.option(color=color)
            objs[num_id] = obj
            if cell.count not in cell_ids:
                cell_ids[cell.count] = []
            cell_ids[cell.count].append(num_id)
            num_id += 1

    elif view_time:
        for cell in view_cells:
            if max_time == 0.0:
                continue
            alpha = float(cell.time) / float(max_spaces_time)
            rad = math.pow(alpha / rad_factor, rad_pow)
            if rad == 0:
                continue
            color = ccolor.getColor(alpha)

            if dim == 3:
                f = 4 * rad
                obj = icosahedron(vec3(cell.x, cell.y, cell.z), f)
            elif dim == 2:
                obj = brick(vec3(cell.x - c, 0, cell.y - c), vec3(cell.x + c, alpha*10, cell.y + c))
            else:
                height = 14 * alpha
                obj = brick(vec3(cell.x - c, 0, 0), vec3(cell.x + c, 1, height))
            obj.option(color=color)
            objs[num_id] = obj
            if cell.count not in cell_ids:
                cell_ids[cell.count] = []
            cell_ids[cell.count].append(num_id)
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

    if ptime > 0 and dim > 1:
        if not accumulate:
            cube = Box(center=vec3(0), width=ptime)
        else:
            t = max_time
            cube = Box(center=vec3(0), width=t if ptime%2 == 0 else t+c)
        objs[num_id] = cube
        num_id += 1

    return objs, count, cell_ids
