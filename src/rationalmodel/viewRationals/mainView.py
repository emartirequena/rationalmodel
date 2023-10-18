from madcad import rendering
from PyQt5 import QtCore, QtWidgets


class MainView(rendering.View):
    def __init__(self, mainWindow: QtWidgets.QMainWindow, scene: rendering.Scene, projection: rendering.Perspective | rendering.Orthographic, parent: QtWidgets.QWidget=None):
        self.mainWindow = mainWindow
        super().__init__(scene, projection=projection, parent=parent)

    def mouseClick(self, evt):
        obj = self.itemat(QtCore.QPoint(evt.x(), evt.y()))
        if obj:
            center = self.scene.item(obj).box.center
            t = self.mainWindow.timeWidget.value()
            spacetime = self.mainWindow.spacetime
            if spacetime:
                if self.mainWindow.dim == 2:
                    x = center.x
                    y = center.z
                    z = 0.0
                else:
                    x = center.x
                    y = center.y
                    z = center.z
                cell = spacetime.getCell(t, x, y, z, accumulate=self.mainWindow._check_accumulate())
                if not cell:
                    return False
                count = cell.count
                self.mainWindow.select_cells(count)
                self.mainWindow.refresh_selection()
            return True
        return False

    def control(self, _, evt):
        if evt.type() == 3:
            return self.mouseClick(evt)
        return False


