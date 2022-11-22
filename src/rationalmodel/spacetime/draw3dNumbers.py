import os
import time
import math

import bpy
import bmesh

from spacetime.spacetime import SpaceTime
from spacetime.rationals import c
from spacetime.utils import divisors

root_dir = r'C:\Users\emart\OneDrive\Documentos\Enrique\Proyectos\spacetime'
fps = 4


def createMaterial(object, name, color):
    
    material_basic = bpy.data.materials.new(name=name)
    material_basic.use_nodes = True
    principled_node = material_basic.node_tree.nodes.get('Principled BSDF')
    principled_node.inputs[0].default_value = color
    principled_node.inputs[21].default_value = color[3]
    object.active_material = material_basic


def createSphere(collection, empty, name, x, y, z, rad, color):

    # Create an empty mesh and the object.
    mesh = bpy.data.meshes.new(name)
    basic_sphere = bpy.data.objects.new(name, mesh)

    # Add the object into the scene.
#    bpy.data.collections[collection].objects['Empty'].link(basic_spehere)
    bpy.data.collections[collection].objects.link(basic_sphere)
    basic_sphere.parent = empty

    # Select the newly created object
    bpy.context.view_layer.objects.active = basic_sphere
    basic_sphere.select_set(True)
    basic_sphere.location = (x, y, z)
    createMaterial(basic_sphere, 'mat', color)

    # Construct the bmesh sphere and assign it to the blender mesh.
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=rad)
    bm.to_mesh(mesh)
    
    bm.free()

    bpy.ops.object.modifier_add(type='TRIANGULATE')
#    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.ops.object.shade_smooth() 
    


def deleteAllSpheres(collection_name, rootName):

    # Get the collection from its name
    collection = bpy.data.collections[collection_name]

    # Will collect meshes from delete objects
    meshes = set()

    # Get objects in the collection if they are meshes
    for obj in [o for o in collection.objects if o.type == 'MESH' and rootName in o.name]:
        # Store the internal mesh
        meshes.add( obj.data )
        # Delete the object
        bpy.data.objects.remove( obj )

    # Look at meshes that are orphean after objects removal
    for mesh in [m for m in meshes if m.users == 0 and rootName in m.name]:
        # Delete the meshes
        bpy.data.meshes.remove( mesh )    


class Space3d(object):
    def __init__(self, T, nt, n):
        print('Creating Collection...')
        scene = bpy.context.scene
        self.coll = bpy.data.collections.get('Spheres')
        if self.coll is None:
            self.coll = bpy.data.collections.new('Spheres')
        if not scene.user_of_id(self.coll):
            bpy.context.collection.children.link(self.coll)
            print('Collection Spheres created...')
            
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        self.empty = bpy.context.selected_objects[0]
        
        print ('Computing spacetime...')
        self.spacetime = SpaceTime(T, nt, dim=3)
        self.spacetime.setRationalSet(n)
        self.spacetime.addRationalSet()

    def drawTime(self, t):
        print('Deleting spheres...')    
        deleteAllSpheres('Spheres', 'pepe')
        space = self.spacetime.spaces[t]

        print('Drawing frame:', t)

        max = -1
        count = 0
        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num > max:
                max = num
            if cell['count']:
                count += 1
        print('Num spheres:', count)

        for i in range(len(space.cells)):
            cell = space.cells[i].get()
            num = cell['count']
            if num == 0:
                continue
            x, y, z = cell['pos']
            rad = 0.5
            alpha = num/max
            if alpha < 0.005:
                alpha = 0.005
            color = (1, 0.5, 0.2, alpha)
            createSphere('Spheres', self.empty, 'pepe', x, y, z, rad, color)
            
        print('Drwaing completed...')
        

    def renderNumber(self, T, t, N, deg):
        if t % fps == 0:
            self.drawTime(int(t/fps))
            
        print('Rendering frame:', t)
        output_dir = os.path.join(root_dir, '3D_T{0:02d}_{1}'.format(T, N))
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        output_file = '3D_T{0:02d}_{1}.%04d.png'.format(T, N)
        bpy.context.scene.render.filepath = os.path.join(output_dir, (output_file % t))
        bpy.ops.render.render(write_still = True)
        
        self.empty.rotation_euler[2] += deg


def main(T, nt, N):
    deg = 2.0*math.pi/(nt*fps)
    print('rotation = ', deg*(2.0*math.pi))
    space = Space3d(T, nt, N)
    for t in range(nt*fps + 1):
        space.renderNumber(T, t, N, deg)


if __name__ == '__main__':
   main(8, 24, 45)
#   space = Space3d(8, 24, 45)
#   space.renderNumber(8, 4, 45)