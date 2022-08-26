import os
import sys
import math
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from madcad import *

from spacetime import SpaceTime
from spacetime2 import SpaceTime as SpaceTimeRedifussion
from utils import divisors, factorGenerator

settings_file = r'settings.txt'


def colorBlend(a, b, alpha):
    r = mathutils.lerp(a.x, b.x, alpha)
    g = mathutils.lerp(a.y, b.y, alpha)
    b = mathutils.lerp(a.z, b.z, alpha)
    return vec3(r, g, b)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setUpUi()
        self.objs = []
        settings.load(os.path.join(os.path.dirname(__file__), settings_file))
        self.view = None
        self.make_view()
        self.showMaximized()
        self.spacetime = None
        self.factors = ''

    def setUpUi(self):
        self.resize(1000, 700)
        self.mainLayout = QtWidgets.QHBoxLayout()
        self.leftLayout = QtWidgets.QVBoxLayout()
        self.rightLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addLayout(self.leftLayout, 10)
        self.mainLayout.addLayout(self.rightLayout, 1)
        
        self.viewLayout = QtWidgets.QVBoxLayout()
        self.timeLayout = QtWidgets.QHBoxLayout()
        
        self.leftLayout.addLayout(self.viewLayout, 10)
        self.leftLayout.addLayout(self.timeLayout, 1)
        
        self.timeWidget = QtWidgets.QSlider(Qt.Horizontal)
        self.timeWidget.setMinimum(0)
        self.timeWidget.setMaximum(1000)
        self.timeWidget.setTickInterval(1)
        self.timeWidget.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.timeWidget.valueChanged.connect(self.make_objects)
        self.timeLayout.addWidget(self.timeWidget)

        self.time = QtWidgets.QSpinBox(self)
        self.time.setMinimumWidth(40)
        self.time.setMaximum(10000)
        self.time.valueChanged.connect(self.timeWidget.setValue)
        self.timeWidget.valueChanged.connect(self.time.setValue)
        self.timeLayout.addWidget(self.time)
        self.time.setValue(0)

        self.gridLayout = QtWidgets.QGridLayout()
        
        self.label1 = QtWidgets.QLabel('Period')
        self.gridLayout.addWidget(self.label1, 0, 0)
        self.period = QtWidgets.QSpinBox(self)
        self.period.setMinimum(1)
        self.period.setMaximum(100)
        self.period.valueChanged.connect(self.get_period_factors)
        self.period.valueChanged.connect(self.fillDivisors)
        self.gridLayout.addWidget(self.period, 0, 1)

        self.label2 = QtWidgets.QLabel('Max Time')
        self.gridLayout.addWidget(self.label2, 1, 0)
        self.maxTime = QtWidgets.QSpinBox(self)
        self.maxTime.valueChanged.connect(self.timeWidget.setMaximum)
        self.maxTime.setMinimum(0)
        self.maxTime.setMaximum(10000)
        self.period.valueChanged.connect(self.maxTime.setValue)
        self.period.valueChanged.connect(self.time.setValue)
        self.gridLayout.addWidget(self.maxTime, 1, 1)

        self.label3 = QtWidgets.QLabel('Number')
        self.gridLayout.addWidget(self.label3, 2, 0)
        self.number = QtWidgets.QSpinBox(self)
        self.number.setMinimum(0)
        self.number.setMaximum(2147483647)
        self.gridLayout.addWidget(self.number, 2, 1)

        self.label4 = QtWidgets.QLabel('Factors')
        self.gridLayout.addWidget(self.label4, 3, 0)
        self.factorsLabel = QtWidgets.QLabel()
        self.factorsLabel.setWordWrap(True)
        self.gridLayout.addWidget(self.factorsLabel, 3, 1)

        self.rightLayout.addLayout(self.gridLayout)

        self.factorsLayout = QtWidgets.QVBoxLayout()
        self.rightLayout.addLayout(self.factorsLayout)

        self.label4 = QtWidgets.QLabel('Divisors')
        self.rightLayout.addWidget(self.label4)

        self.divisors = QtWidgets.QListWidget(self)
        self.divisors.clicked.connect(self.setNumber)
        self.rightLayout.addWidget(self.divisors)

        self.redifussion = QtWidgets.QCheckBox('Redifussion', self)
        self.redifussion.setCheckState(Qt.Unchecked)
        self.rightLayout.addWidget(self.redifussion)

        self.computeButton = QtWidgets.QPushButton('Compute', self)
        self.rightLayout.addWidget(self.computeButton)
        self.computeButton.clicked.connect(self.compute)

        self.central = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central)
        self.central.setLayout(self.mainLayout)

    def compute(self):
        print('Creating spacetime...')
        if self.redifussion.isChecked():
            self.spacetime = SpaceTimeRedifussion(self.period.value(), self.maxTime.value(), dim=3)
        else:
            self.spacetime = SpaceTime(self.period.value(), self.maxTime.value(), dim=3)

        print('Setting rational set for number:', self.number.value())
        self.spacetime.setRationalSet(self.number.value())
        print('Adding rational set...')
        self.spacetime.addRationalSet()
        self.timeWidget.setValue(self.maxTime.value())
        self.make_objects()

    def make_objects(self):
        if not self.spacetime:
            return
        time = self.timeWidget.value()
        if time >= len(self.spacetime.spaces):
            return
        space = self.spacetime.spaces[time]

        self.objs = []

        print('Drawing frame:', time)

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
            alpha = float(num)/float(max)
            rad = alpha * 0.5
            if rad < 0.07:
                rad = 0.07
            color1 = vec3(1, 0.5, 0.2)
            color2 = vec3(0.5, 0.2, 1)
            color = colorBlend(color2, color1, alpha)
            sphere = uvsphere(vec3(x, y, z), rad, resolution=('div', int(20 * math.pow(rad, 0.2))))
            sphere.option(color=color)

            self.objs.append(sphere)

        print('Drwaing completed...')

        axisX = Axis(vec3(0), X)
        axisY = Axis(vec3(0), Y)
        axisZ = Axis(vec3(0), Z)
        self.objs.append([axisX, axisY, axisZ])

        cube = Box(center=vec3(0), width=time)

        self.objs.append(cube)

        if isinstance(self.objs, list):
            self.objs = dict(enumerate([self.objs]))
        print('Objects list created...')
    
        self.make_view()

    def make_view(self):
        if self.view and len(self.view.scene.displays):
            while len(self.view.scene.displays):
                obj = self.view.scene.displays.pop(0)
                del obj
            self.view.scene.update(self.objs)
            self.view.scene.render(self.view)
            self.view.update()
        else:
            scene = rendering.Scene(self.objs, options=None)
            self.viewLayout.takeAt(0)
            self.view = rendering.View(scene, parent=self.central)
            self.viewLayout.addWidget(self.view)
            self.view.show()
            self.view.center()
            self.view.adjust(scene.box())

    def get_factors(self, n):
        factors = factorGenerator(n)
        labels = []
        for factor in factors:
            if factors[factor] == 1:
                labels.append(str(factor))
            else:
                labels.append(str(factor) + '^' + str(factors[factor]))

        label = ', '.join(labels)
        return label

    def get_period_factors(self, T):
        label = self.get_factors(pow(8, T)-1)
        self.factorsLabel.setText(label)

    def fillDivisors(self, T):
        numbers = divisors(pow(8, T)-1)
        self.divisors.clear()
        self.divisors.addItems([str(x) + ' = ' + self.get_factors(x) for x in numbers])

    def setNumber(self, index):
        item = self.divisors.item(index.row())
        self.number.setValue(int(item.text().split(' ', 1)[0]))


if __name__=="__main__":
    app = QtWidgets.QApplication(sys. argv)
    wi = MainWindow()
    wi.show()
    sys.exit(app.exec())
