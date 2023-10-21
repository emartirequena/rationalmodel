from copy import deepcopy

from PyQt5 import QtWidgets, QtCore, QtGui
from madcad import rendering
import numpy as np

from mainView import MainView
from renderView import RenderView


class View(QtWidgets.QWidget):
    def __init__(self, type: str, mainWidnow, ctx=None, parent=None) -> None:
        super().__init__(parent=parent)
        self.type = type
        self.ctx = ctx
        self.scene = rendering.Scene(ctx=ctx)
        self.active = False
        if type in ['3D', '3DVIEW']:
            projection = rendering.Perspective()
        else:
            projection = rendering.Orthographic()
        if 'LEFT' in self.type:
            navigation = rendering.Turntable(yaw=np.deg2rad(90), pitch=0)
        elif 'TOP' in self.type:
            navigation = rendering.Turntable(yaw=0, pitch=np.deg2rad(90))
        else:
            navigation = rendering.Turntable(yaw=0, pitch=0)
        self.view = MainView(mainWindow=mainWidnow, scene=self.scene, projection=projection, navigation=navigation)
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)
        self.setContentsMargins(0, 0, 0, 0)

    def set_active(self, active: bool):
        self.active = active

    def initialize(self, objs):
        self.view.scene.displays.clear()
        self.view.scene.update(objs)
        self.view.scene.render(self.view)
        self.view.show()
        self.view.center()
        self.view.adjust()
        self.view.update()
        self.update()

    def reset(self, objs):
        print(f'------- View {self.type} reset({len(objs)}) objs')
        self.view.scene.displays.clear()
        self.view.scene.update(objs)
        self.view.scene.render(self.view)
        self.view.show()
        self.view.update()
        self.update()

    def center(self):
        if 'LEFT' in self.type:
            self.view.navigation = rendering.Turntable(yaw=np.deg2rad(90), pitch=0)
        elif 'TOP' in self.type:
            self.view.navigation = rendering.Turntable(yaw=0, pitch=np.deg2rad(90))
        else:
            self.view.navigation = rendering.Turntable(yaw=0, pitch=0)
        self.view.center()
        self.view.adjust()
        self.view.update()
        self.update()

    def clear(self):
        if self.type in ['3D', '3DVIEW']:
            self.view.projection = rendering.Perspective()
        else:
            self.view.projection = rendering.Orthographic()
        if 'LEFT' in self.type:
            self.view.navigation = rendering.Turntable(yaw=np.deg2rad(90), pitch=0)
        elif 'TOP' in self.type:
            self.view.navigation = rendering.Turntable(yaw=0, pitch=np.deg2rad(90))
        else:
            self.view.navigation = rendering.Turntable(yaw=0, pitch=0)
        self.view.center()
        self.view.adjust()

        self.view.scene.displays.clear()
        self.view.scene.update({})
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

    def get_ctx(self):
        return self.scene.ctx
        

class Views(QtWidgets.QWidget):
    def __init__(self, mainWindow, parent=None) -> None:
        super().__init__(parent=parent)
        self.mode = ''
        self.views = {}
        self.mainWindow = mainWindow
        self.navigation = None
        self.main_layout = None
        self.parent = parent
        self.init_views()
        self.set_mode('3DSPLIT')

    def init_views(self):
        self.views = {}
        self.views['1D'] = View('1D', self.mainWindow, None, parent=self.parent)
        self.ctx = self.views['1D'].get_ctx()
        self.views['2D'] = View('2D', self.mainWindow, ctx=self.ctx, parent=self.parent)
        self.views['3D'] = View('3D', self.mainWindow, ctx=self.ctx, parent=self.parent)
        names = ['3DFRONT', '3DTOP', '3DLEFT', '3DVIEW']
        for name in names:
            self.views[name] = View(name, self.mainWindow, ctx=self.ctx, parent=self.parent)

    def set_mode(self, mode: str):
        if self.layout():
            for i in reversed(range(self.layout().count())):
                if self.mode == '3DSPLIT':
                    self.layout().itemAt(i).layout().setParent(None)
                else:
                    self.layout().itemAt(i).widget().setParent(None)
        else:
            self.main_layout = QtWidgets.QVBoxLayout(self)
        self.update()

        if mode == '3D':
            self.navigation = deepcopy(self.views['3DVIEW'].view.navigation)
        elif mode == '3DVIEW':
            self.navigation = deepcopy(self.views['3D'].view.navigation)
        else:
            self.navigation = None

        for view in self.views.values():
            view.set_active(False)
        
        if mode == '1D':
            self.views['1D'].set_active(True)
            self.main_layout.addWidget(self.views['1D'])
        elif mode == '2D':
            self.views['2D'].set_active(True)
            self.main_layout.addWidget(self.views['2D'])
        elif mode == '3D':
            if self.navigation:
                self.views['3D'].view.navigation = self.navigation
            self.views['3D'].set_active(True)
            self.main_layout.addWidget(self.views['3D'])
        else:
            names = ['3DFRONT', '3DTOP', '3DLEFT', '3DVIEW']
            for name in names:
                self.views[name].set_active(True)
                if self.navigation and name == '3DVIEW':
                    self.views['3DVIEW'].view.navigation = self.navigation
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
        
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.mode = mode
        self.update()

    def initialize(self, objs):
        for view in self.views.values():
            if view.active:
                view.initialize(objs)

    def reset(self, objs):
        for view in self.views.values():
            if view.active:
                view.reset(objs)

    def center(self):
        for view in self.views.values():
            if view.active:
                view.center()

    def clear(self):
        for view in self.views.values():
            if view.active:
                view.clear()

    def switch_display_id(self, id, state=None):
        for view in self.views.values():
            if view.active:
                view.switch_display_id(id, state=state)
