from copy import deepcopy

from PyQt5 import QtWidgets
from madcad import rendering
import numpy as np
from PIL import Image, ImageDraw

from screenView import ScreenView
from renderView import RenderView
from timing import timing


class View(QtWidgets.QWidget):
    def __init__(self, type: str, mainWindow, parent=None) -> None:
        super().__init__()
        self.type = type
        self.scene = rendering.Scene()
        self.active = False
        self.view = ScreenView(mainWindow, self.scene, parent=parent)
        self.set_projection()
        self.set_navigation()
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)
        self.setContentsMargins(0, 0, 0, 0)

    def set_projection(self):
        if self.type in ['3D', '3DVIEW']:
            self.view.projection = rendering.Perspective(fov=np.deg2rad(30))
        else:
            self.view.projection = rendering.Orthographic()

    def set_navigation(self):
        if 'LEFT' in self.type:
            self.view.navigation = rendering.Turntable(yaw=np.deg2rad(90), pitch=0)
        elif 'TOP' in self.type:
            self.view.navigation = rendering.Turntable(yaw=0, pitch=np.deg2rad(90))
        else:
            self.view.navigation = rendering.Turntable(yaw=0, pitch=0)

    def set_active(self, active: bool):
        self.active = active

    def load_objs(self, objs):
        self.scene.sync(objs)
        self.view.render()
        self.view.show()

    def initialize(self, objs):
        self.load_objs(objs)
        self.view.center()
        self.view.adjust()
        self.view.update()
        self.update()

    def reinit(self, objs):
        self.load_objs(objs)
        if self.type not in ['3D', '3DVIEW']:
            self.view.center()
            self.view.adjust()
        self.view.update()
        self.update()

    def reset(self, objs):
        self.load_objs(objs)
        self.view.update()
        self.update()

    def center(self):
        self.set_projection()
        self.set_navigation()
        self.view.center()
        self.view.adjust()
        self.view.update()
        self.update()

    def clear(self):
        self.set_projection()
        self.set_navigation()
        self.view.scene.displays.clear()
        self.view.scene.update({})
        self.view.center()
        self.view.adjust()
        self.view.update()
        self.update()

    def switch_display_id(self, id, state=None):
        if len(self.view.scene.item([0])) == 1:
            disp = self.view.scene.item([0])[0].displays[id]
        else:
            disp = self.view.scene.item([0])[id]
        if type(disp).__name__ in ('SolidDisplay', 'WebDisplay'):
            if self.type == '2D':
                disp.vertices.selectsub(1)
            else:
                disp.vertices.selectsub(0)
            disp.selected = state if state is not None else not any(disp.vertices.flags & 0x1)
        else:
            disp.selected = state if state is not None else not disp.selected
        self.view.update()

    def render(self, resx, resy, objs):
        projection = deepcopy(self.view.projection)
        navigation = deepcopy(self.view.navigation)

        scene = rendering.Scene(objs, options=None)
        view = RenderView(scene, projection=projection, navigation=navigation)
        if self.type in ['3DVIEW', '3DLEFT', '3DTOP', '3DFRONT']:
            view.resize((resx // 2, resy // 2))
        else:
            view.resize((resx, resy))
        return view.render()
    
    def rotate3DView(self, dx):
        if self.type in ['3D', '3DVIEW']:
            self.view.navigation.rotate(dx, 0, 0)
            self.view.update()
            self.update()

    def rotate3DVideo(self, dx):
        if self.type in ['3D', '3DVIEW']:
            self.view.navigation.rotate(dx, 0, 0)


class Views(QtWidgets.QWidget):
    def __init__(self, mainWindow, parent=None) -> None:
        super().__init__(parent=parent)
        self.mode = ''
        self.mode_3d = '3DSPLIT'
        self.views = {}
        self.mainWindow = mainWindow
        self.navigation = None
        self.projection = None
        self.main_layout = None
        self.parent = parent
        self.init_views()
        self.set_mode(self.mode_3d)

    def init_views(self):
        self.views = {}
        self.views['1D'] = View('1D', self.mainWindow, parent=self.parent)
        self.views['2D'] = View('2D', self.mainWindow, parent=self.parent)
        self.views['3D'] = View('3D', self.mainWindow, parent=self.parent)
        names = ['3DFRONT', '3DTOP', '3DLEFT', '3DVIEW']
        for name in names:
            self.views[name] = View(name, self.mainWindow, parent=self.parent)

    def set_mode(self, mode: str):
        if self.layout():
            for i in reversed(range(self.layout().count())):
                if self.mode == '3DSPLIT':
                    layout = self.layout().itemAt(i).layout()
                    for j in reversed(range(layout.count())):
                        layout.itemAt(j).widget().setParent(None)
                    layout.setParent(None)
                else:
                    self.layout().itemAt(i).widget().setParent(None)
        else:
            self.main_layout = QtWidgets.QVBoxLayout(self)
            self.setLayout(self.main_layout)

        if mode == '3D':
            self.navigation = deepcopy(self.views['3DVIEW'].view.navigation)
            self.projection = deepcopy(self.views['3DVIEW'].view.projection)
        elif mode == '3DSPLIT':
            self.navigation = deepcopy(self.views['3D'].view.navigation)
            self.projection = deepcopy(self.views['3D'].view.projection)
        else:
            self.navigation = None

        for view in self.views.values():
            view.set_active(False)
        
        if mode == '1D':
            self.views['1D'] = View('1D', self.mainWindow, parent=self.parent)
            self.views['1D'].set_active(True)
            self.main_layout.addWidget(self.views['1D'])
        elif mode == '2D':
            self.views['2D'] = View('2D', self.mainWindow, parent=self.parent)
            self.views['2D'].set_active(True)
            self.main_layout.addWidget(self.views['2D'])
        elif mode == '3D':
            self.views['3D'] = View('3D', self.mainWindow, parent=self.parent)
            if self.navigation:
                self.views['3D'].view.navigation = self.navigation
                self.views['3D'].view.projection = self.projection
            self.views['3D'].set_active(True)
            self.main_layout.addWidget(self.views['3D'])
            self.mode_3d = '3D'
        else:
            names = ['3DFRONT', '3DTOP', '3DLEFT', '3DVIEW']
            for name in names:
                self.views[name] = View(name, self.mainWindow, parent=self.parent)
                self.views[name].set_active(True)
                if self.navigation and name == '3DVIEW':
                    self.views['3DVIEW'].view.navigation = self.navigation
                    self.views['3DVIEW'].view.projection = self.projection
            self.up_layout = QtWidgets.QHBoxLayout()
            self.down_layout = QtWidgets.QHBoxLayout()
            self.up_layout.addWidget(self.views['3DTOP'])
            self.up_layout.addWidget(self.views['3DFRONT'])
            self.down_layout.addWidget(self.views['3DLEFT'])
            self.down_layout.addWidget(self.views['3DVIEW'])
            self.up_layout.setContentsMargins(0, 0, 0, 0)
            self.down_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.addLayout(self.up_layout)
            self.main_layout.addLayout(self.down_layout)
            self.mode_3d = '3DSPLIT'
        
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.mode = mode
        self.update()

    def get_mode(self):
        return self.mode
    
    def get_mode_3d(self):
        return self.mode_3d

    def initialize(self, objs):
        view: View
        for view in self.views.values():
            if view.active:
                view.initialize(objs)

    def reinit(self, objs):
        view: View
        for view in self.views.values():
            if view.active:
                view.reinit(objs)

    @timing
    def reset(self, objs):
        view: View
        for view in self.views.values():
            if view.active:
                view.reset(objs)

    def center(self):
        view: View
        for view in self.views.values():
            if view.active:
                view.center()

    def clear(self):
        view: View
        for view in self.views.values():
            if view.active:
                view.clear()

    def rotate3DView(self, dx):
        if self.mode in ['3D', '3DSPLIT']:
            if self.mode == '3D':
                name = '3D'
            else:
                name = '3DVIEW'
            self.views[name].rotate3DView(dx)
            self.update()

    def rotate3DVideo(self, dx):
        if self.mode in ['3D', '3DSPLIT']:
            if self.mode == '3D':
                name = '3D'
            else:
                name = '3DVIEW'
            self.views[name].rotate3DVideo(dx)

    def switch_display_id(self, id, state=None):
        view: View
        for view in self.views.values():
            if view.active:
                view.switch_display_id(id, state=state)

    def render(self, resx, resy, objs):
        if self.mode != '3DSPLIT':
            return self.views[self.mode].render(resx, resy, objs)

        background = Image.new('RGBA', (resx, resy), (180, 180, 180, 255))
        draw = ImageDraw.Draw(background)
        img_top = self.views['3DTOP'].render(resx, resy, objs)
        img_front = self.views['3DFRONT'].render(resx, resy, objs)
        img_left = self.views['3DLEFT'].render(resx, resy, objs)
        img_view = self.views['3DVIEW'].render(resx, resy, objs)
        background.alpha_composite(img_top,   dest=(0, 0))
        background.alpha_composite(img_front, dest=(resx // 2, 0))
        background.alpha_composite(img_left,  dest=(0, resy // 2))
        background.alpha_composite(img_view,  dest=(resx // 2, resy // 2))
        draw.line((resx // 2, 0, resx // 2, resy), (180, 180, 180, 255), width=4)
        draw.line((0, resy // 2, resx, resy // 2), (180, 180, 180, 255), width=4)
        return background
