from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt


class MainWindowUI:
    def setUpUi(self, mainWindow: QtWidgets.QMainWindow):
        mainWindow.resize(1920, 1080)

        mainWindow.setWindowTitle('View 3D Spacetime Rational Sets')

        mainWindow.mainLayout = QtWidgets.QHBoxLayout()
        mainWindow.leftLayout = QtWidgets.QVBoxLayout()
        mainWindow.rightLayout = QtWidgets.QVBoxLayout()
        mainWindow.mainLayout.addLayout(mainWindow.leftLayout, 10)
        mainWindow.mainLayout.addLayout(mainWindow.rightLayout, 1)
        
        mainWindow.viewLayout = QtWidgets.QVBoxLayout()
        mainWindow.timeLayout = QtWidgets.QHBoxLayout()
        
        mainWindow.leftLayout.addLayout(mainWindow.viewLayout, 10)
        mainWindow.leftLayout.addLayout(mainWindow.timeLayout, 1)

        mainWindow.timeWidget = QtWidgets.QSlider(Qt.Horizontal)
        mainWindow.timeWidget.setMinimum(0)
        mainWindow.timeWidget.setMaximum(100)
        mainWindow.timeWidget.setTickInterval(1)
        mainWindow.timeWidget.setTickPosition(QtWidgets.QSlider.TicksAbove)
        mainWindow.timeWidget.valueChanged.connect(mainWindow.make_objects)
        mainWindow.timeLayout.addWidget(mainWindow.timeWidget)

        mainWindow.time = QtWidgets.QSpinBox(mainWindow)
        mainWindow.time.setMinimumWidth(40)
        mainWindow.time.setMinimum(0)
        mainWindow.time.setMaximum(10000)
        mainWindow.time.valueChanged.connect(mainWindow.timeWidget.setValue)
        mainWindow.timeWidget.valueChanged.connect(mainWindow.time.setValue)
        mainWindow.time.setValue(0)
        mainWindow.timeLayout.addWidget(mainWindow.time)

        mainWindow.gridLayout = QtWidgets.QGridLayout()

        mainWindow.dimLabel = QtWidgets.QLabel('Dimension')
        mainWindow.gridLayout.addWidget(mainWindow.dimLabel, 0, 0)
        mainWindow.dimLayout = QtWidgets.QHBoxLayout()
        mainWindow.button1D = QtWidgets.QPushButton('1D', mainWindow)
        mainWindow.button1D.setMaximumWidth(50)
        mainWindow.button1D.setMinimumHeight(20)
        mainWindow.button1D.clicked.connect(mainWindow.set1D)
        mainWindow.dimLayout.addWidget(mainWindow.button1D)
        mainWindow.button2D = QtWidgets.QPushButton('2D', mainWindow)
        mainWindow.button2D.setMaximumWidth(50)
        mainWindow.button2D.setMinimumHeight(20)
        mainWindow.button2D.clicked.connect(mainWindow.set2D)
        mainWindow.dimLayout.addWidget(mainWindow.button2D)
        mainWindow.button3D = QtWidgets.QPushButton('3D', mainWindow)
        mainWindow.button3D.setMaximumWidth(50)
        mainWindow.button3D.setMinimumHeight(20)
        mainWindow.button3D.clicked.connect(mainWindow.set3D)
        mainWindow.dimLayout.addWidget(mainWindow.button3D)
        mainWindow.gridLayout.addLayout(mainWindow.dimLayout, 0, 1)

        mainWindow.label1 = QtWidgets.QLabel('Period')
        mainWindow.gridLayout.addWidget(mainWindow.label1, 1, 0)
        mainWindow.period = QtWidgets.QSpinBox(mainWindow)
        mainWindow.period.setMinimum(1)
        mainWindow.period.setMaximum(100)
        mainWindow.period.valueChanged.connect(mainWindow.get_period_factors)
        mainWindow.gridLayout.addWidget(mainWindow.period, 1, 1)

        mainWindow.label2 = QtWidgets.QLabel('Max Time')
        mainWindow.gridLayout.addWidget(mainWindow.label2, 2, 0)
        mainWindow.maxTime = QtWidgets.QSpinBox(mainWindow)
        mainWindow.maxTime.valueChanged.connect(mainWindow.timeWidget.setMaximum)
        mainWindow.maxTime.valueChanged.connect(mainWindow.maxTimeChanged)
        mainWindow.maxTime.setMinimum(0)
        mainWindow.maxTime.setMaximum(10000)
        mainWindow.gridLayout.addWidget(mainWindow.maxTime, 2, 1)

        mainWindow.label3 = QtWidgets.QLabel('Number')
        mainWindow.gridLayout.addWidget(mainWindow.label3, 3, 0)
        mainWindow.number = QtWidgets.QDoubleSpinBox(mainWindow)
        mainWindow.number.setMinimum(0)
        mainWindow.number.setDecimals(0)
        mainWindow.number.setMaximum(18446744073709551615)
        mainWindow.number.setEnabled(False)
        mainWindow.gridLayout.addWidget(mainWindow.number, 3, 1)

        mainWindow.label4 = QtWidgets.QLabel('Factors')
        mainWindow.gridLayout.addWidget(mainWindow.label4, 4, 0)
        mainWindow.factorsLabel = QtWidgets.QLabel()
        mainWindow.factorsLabel.setWordWrap(True)
        mainWindow.gridLayout.addWidget(mainWindow.factorsLabel, 4, 1)

        mainWindow.factorsLayout = QtWidgets.QVBoxLayout()
        mainWindow.gridLayout.addLayout(mainWindow.factorsLayout, 5, 0)

        mainWindow.label4 = QtWidgets.QLabel('Divisors')
        mainWindow.gridLayout.addWidget(mainWindow.label4, 6, 0)
        mainWindow.label_num_divisors = QtWidgets.QLabel('')
        mainWindow.gridLayout.addWidget(mainWindow.label_num_divisors, 6, 1)

        mainWindow.rightLayout.addLayout(mainWindow.gridLayout)

        mainWindow.divisors = QtWidgets.QListWidget(mainWindow)
        mainWindow.divisors.clicked.connect(mainWindow.setNumber)
        mainWindow.rightLayout.addWidget(mainWindow.divisors)

        mainWindow.accumulate = QtWidgets.QCheckBox('Accumulate', mainWindow)
        mainWindow.accumulate.setCheckState(Qt.Unchecked)
        mainWindow.rightLayout.addWidget(mainWindow.accumulate)

        mainWindow.computeButton = QtWidgets.QPushButton('Compute', mainWindow)
        mainWindow.rightLayout.addWidget(mainWindow.computeButton)
        mainWindow.computeButton.clicked.connect(mainWindow.compute)

        mainWindow.central = QtWidgets.QWidget(mainWindow)
        mainWindow.setCentralWidget(mainWindow.central)
        mainWindow.central.setLayout(mainWindow.mainLayout)

        mainWindow.menu = mainWindow.menuBar()
        mainWindow.mainMenu = QtWidgets.QMenu('Main')
        mainWindow.actionExit = QtWidgets.QAction('Exit', mainWindow)
        mainWindow.actionExit.setShortcut('Esc')
        mainWindow.actionExit.triggered.connect(mainWindow.close)
        mainWindow.mainMenu.addAction(mainWindow.actionExit)
        mainWindow.menu.addMenu(mainWindow.mainMenu)

        mainWindow.menuUtils = QtWidgets.QMenu('Utils')

        mainWindow.actionSaveImage = QtWidgets.QAction('Save Image', mainWindow)
        mainWindow.actionSaveImage.setShortcut('I')
        mainWindow.actionSaveImage.triggered.connect(mainWindow.saveImage)
        mainWindow.menuUtils.addAction(mainWindow.actionSaveImage)

        mainWindow.actionSaveVideo = QtWidgets.QAction('Save Video', mainWindow)
        mainWindow.actionSaveVideo.setShortcut('V')
        mainWindow.actionSaveVideo.triggered.connect(mainWindow.saveVideo)
        mainWindow.menuUtils.addAction(mainWindow.actionSaveVideo)

        mainWindow.actionSaveSpecials = QtWidgets.QAction('Save Specials', mainWindow)
        mainWindow.actionSaveSpecials.setShortcut('S')
        mainWindow.actionSaveSpecials.triggered.connect(mainWindow.saveSpecials)
        mainWindow.menuUtils.addAction(mainWindow.actionSaveSpecials)

        mainWindow.menuUtils.addSeparator()

        mainWindow.actionFitHistogram = QtWidgets.QAction('Fit Histogram', mainWindow)
        mainWindow.actionFitHistogram.setShortcut('F')
        mainWindow.actionFitHistogram.triggered.connect(mainWindow.fit_histogram)
        mainWindow.menuUtils.addAction(mainWindow.actionFitHistogram)

        mainWindow.actionViewHistogram = QtWidgets.QAction('View Histogram', mainWindow)
        mainWindow.actionViewHistogram.setShortcut('H')
        mainWindow.actionViewHistogram.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mainWindow.actionViewHistogram.triggered.connect(mainWindow.set_view_histogram)
        mainWindow.menuUtils.addAction(mainWindow.actionViewHistogram)

        mainWindow.actionCenterView = QtWidgets.QAction('Center View', mainWindow)
        mainWindow.actionCenterView.setShortcut('C')
        mainWindow.actionCenterView.triggered.connect(mainWindow.center_view)
        mainWindow.menuUtils.addAction(mainWindow.actionCenterView)
        
        mainWindow.menu.addMenu(mainWindow.menuUtils)

        mainWindow.menuSelection = QtWidgets.QMenu('Selection')

        mainWindow.actionSelectAll = QtWidgets.QAction('Select All', mainWindow)
        mainWindow.actionSelectAll.setShortcut('A')
        mainWindow.actionSelectAll.triggered.connect(mainWindow.select_all)
        mainWindow.menuSelection.addAction(mainWindow.actionSelectAll)
        
        mainWindow.actionDeselectAll = QtWidgets.QAction('Deselect All', mainWindow)
        mainWindow.actionDeselectAll.setShortcut('D')
        mainWindow.actionDeselectAll.triggered.connect(mainWindow.deselect_all)
        mainWindow.menuSelection.addAction(mainWindow.actionDeselectAll)
        
        mainWindow.actionInvertSelection = QtWidgets.QAction('Invert Selection', mainWindow)
        mainWindow.actionInvertSelection.setShortcut('Shift+A')
        mainWindow.actionInvertSelection.triggered.connect(mainWindow.invert_selection)
        mainWindow.menuSelection.addAction(mainWindow.actionInvertSelection)

        mainWindow.menu.addMenu(mainWindow.menuSelection)

        mainWindow.menuTime = QtWidgets.QMenu('Time')

        mainWindow.actionLeft = QtWidgets.QAction('Increment time', mainWindow.centralWidget())
        mainWindow.actionLeft.setShortcut('Left')
        mainWindow.actionLeft.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mainWindow.actionLeft.triggered.connect(mainWindow.decrementTime)
        mainWindow.menuTime.addAction(mainWindow.actionLeft)

        mainWindow.actionRight = QtWidgets.QAction('Decrement time', mainWindow.centralWidget())
        mainWindow.actionRight.setShortcut('Right')
        mainWindow.actionRight.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mainWindow.actionRight.triggered.connect(mainWindow.incrementTime)
        mainWindow.menuTime.addAction(mainWindow.actionRight)

        mainWindow.actionInit = QtWidgets.QAction('Go to init', mainWindow.centralWidget())
        mainWindow.actionInit.setShortcut('Home')
        mainWindow.actionInit.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mainWindow.actionInit.triggered.connect(mainWindow.setTimeInit)
        mainWindow.menuTime.addAction(mainWindow.actionInit)

        mainWindow.actionEnd = QtWidgets.QAction('Go to end', mainWindow.centralWidget())
        mainWindow.actionEnd.setShortcut('End')
        mainWindow.actionEnd.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mainWindow.actionEnd.triggered.connect(mainWindow.setTimeEnd)
        mainWindow.menuTime.addAction(mainWindow.actionEnd)

        mainWindow.menu.addMenu(mainWindow.menuTime)

        mainWindow.statusBar = QtWidgets.QStatusBar(mainWindow)
        mainWindow.statusLabel = QtWidgets.QLabel()
        mainWindow.statusBar.addWidget(mainWindow.statusLabel)
        mainWindow.setStatusBar(mainWindow.statusBar)
