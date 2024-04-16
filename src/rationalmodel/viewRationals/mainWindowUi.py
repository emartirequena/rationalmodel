from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt


class MainWindowUI:
    def setUpUi(self, mw: QtWidgets.QMainWindow):
        mw.resize(1920, 1080)

        mw.setWindowTitle('View Rationals Sets Spacetime Distribution')

        mw.mainLayout = QtWidgets.QHBoxLayout()
        mw.leftLayout = QtWidgets.QVBoxLayout()
        mw.rightLayout = QtWidgets.QVBoxLayout()
        mw.mainLayout.addLayout(mw.leftLayout, 10)
        mw.mainLayout.addLayout(mw.rightLayout, 1)
        
        mw.viewLayout = QtWidgets.QVBoxLayout()
        mw.timeLayout = QtWidgets.QHBoxLayout()
        
        mw.leftLayout.addLayout(mw.viewLayout, 10)
        mw.leftLayout.addLayout(mw.timeLayout, 1)

        mw.timeWidget = QtWidgets.QSlider(Qt.Horizontal)
        mw.timeWidget.setMinimum(0)
        mw.timeWidget.setMaximum(100)
        mw.timeWidget.setTickInterval(1)
        mw.timeWidget.setTickPosition(QtWidgets.QSlider.TicksAbove)
        mw.timeWidget.valueChanged.connect(mw.draw_objects)
        mw.timeLayout.addWidget(mw.timeWidget)

        mw.time = QtWidgets.QSpinBox(mw)
        mw.time.setMinimumWidth(40)
        mw.time.setMinimum(0)
        mw.time.setMaximum(10000)
        mw.time.valueChanged.connect(mw.timeWidget.setValue)
        mw.timeWidget.valueChanged.connect(mw.time.setValue)
        mw.time.setValue(0)
        mw.timeLayout.addWidget(mw.time)

        mw.gridLayout = QtWidgets.QGridLayout()

        mw.dimLabel = QtWidgets.QLabel('Dimension')
        mw.gridLayout.addWidget(mw.dimLabel, 0, 0)
        mw.dimLayout = QtWidgets.QHBoxLayout()
        mw.button1D = QtWidgets.QPushButton('1D', mw)
        mw.button1D.setMaximumWidth(50)
        mw.button1D.setMinimumHeight(20)
        mw.button1D.clicked.connect(mw.set1D)
        mw.dimLayout.addWidget(mw.button1D)
        mw.button2D = QtWidgets.QPushButton('2D', mw)
        mw.button2D.setMaximumWidth(50)
        mw.button2D.setMinimumHeight(20)
        mw.button2D.clicked.connect(mw.set2D)
        mw.dimLayout.addWidget(mw.button2D)
        mw.button3D = QtWidgets.QPushButton('3D', mw)
        mw.button3D.setMaximumWidth(50)
        mw.button3D.setMinimumHeight(20)
        mw.button3D.clicked.connect(mw.set3D)
        mw.dimLayout.addWidget(mw.button3D)
        mw.gridLayout.addLayout(mw.dimLayout, 0, 1)

        mw.label1 = QtWidgets.QLabel('Period')
        mw.gridLayout.addWidget(mw.label1, 1, 0)
        mw.period = QtWidgets.QSpinBox(mw)
        mw.period.setMinimum(1)
        mw.period.setMaximum(100)
        mw.period.valueChanged.connect(mw.get_period_factors)
        mw.gridLayout.addWidget(mw.period, 1, 1)

        mw.label2 = QtWidgets.QLabel('Max Time')
        mw.gridLayout.addWidget(mw.label2, 2, 0)
        mw.maxTime = QtWidgets.QSpinBox(mw)
        mw.maxTime.valueChanged.connect(mw.timeWidget.setMaximum)
        mw.maxTime.valueChanged.connect(mw.maxTimeChanged)
        mw.maxTime.setMinimum(0)
        mw.maxTime.setMaximum(10000)
        mw.gridLayout.addWidget(mw.maxTime, 2, 1)

        mw.label3 = QtWidgets.QLabel('Number')
        mw.gridLayout.addWidget(mw.label3, 3, 0)
        mw.number = QtWidgets.QDoubleSpinBox(mw)
        mw.number.setMinimum(0)
        mw.number.setDecimals(0)
        mw.number.setMaximum(18446744073709551615)
        mw.number.setEnabled(False)
        mw.gridLayout.addWidget(mw.number, 3, 1)

        mw.label4 = QtWidgets.QLabel('Factors')
        mw.gridLayout.addWidget(mw.label4, 4, 0)
        mw.factorsLabel = QtWidgets.QLabel()
        mw.factorsLabel.setWordWrap(True)
        mw.gridLayout.addWidget(mw.factorsLabel, 4, 1)

        mw.factorsLayout = QtWidgets.QVBoxLayout()
        mw.gridLayout.addLayout(mw.factorsLayout, 5, 0)

        mw.label4 = QtWidgets.QLabel('Divisors')
        mw.gridLayout.addWidget(mw.label4, 6, 0)
        mw.label_num_divisors = QtWidgets.QLabel('')
        mw.gridLayout.addWidget(mw.label_num_divisors, 6, 1)

        mw.rightLayout.addLayout(mw.gridLayout)

        mw.divisors = QtWidgets.QListWidget(mw)
        mw.divisors.clicked.connect(mw.setNumber)
        mw.rightLayout.addWidget(mw.divisors)

        mw.accumulate = QtWidgets.QCheckBox('Accumulate', mw)
        mw.accumulate.setCheckState(Qt.Unchecked)
        mw.rightLayout.addWidget(mw.accumulate)

        mw.computeButton = QtWidgets.QPushButton('Compute', mw)
        mw.rightLayout.addWidget(mw.computeButton)
        mw.computeButton.clicked.connect(mw.compute)

        mw.central = QtWidgets.QWidget(mw)
        mw.setCentralWidget(mw.central)
        mw.central.setLayout(mw.mainLayout)

        mw.menu = mw.menuBar()
        mw.mainMenu = QtWidgets.QMenu('Main')
        mw.actionExit = QtWidgets.QAction('Exit', mw)
        mw.actionExit.setShortcut('Esc')
        mw.actionExit.triggered.connect(mw.close)
        mw.mainMenu.addAction(mw.actionExit)
        mw.menu.addMenu(mw.mainMenu)

        mw.menuFiles = QtWidgets.QMenu('Files')

        mw.actionSave = QtWidgets.QAction('Save Number', mw)
        mw.actionSave.setShortcut('S')
        mw.actionSave.triggered.connect(mw.save)
        mw.menuFiles.addAction(mw.actionSave)

        mw.actionLoad = QtWidgets.QAction('Load Number', mw)
        mw.actionLoad.setShortcut('L')
        mw.actionLoad.triggered.connect(mw.load)
        mw.menuFiles.addAction(mw.actionLoad)

        mw.menu.addMenu(mw.menuFiles)

        mw.menuUtils = QtWidgets.QMenu('Utils')

        mw.actionSaveImage = QtWidgets.QAction('Save Image', mw)
        mw.actionSaveImage.setShortcut('I')
        mw.actionSaveImage.triggered.connect(mw.saveImage)
        mw.menuUtils.addAction(mw.actionSaveImage)

        mw.actionSaveVideo = QtWidgets.QAction('Save Video', mw)
        mw.actionSaveVideo.setShortcut('V')
        mw.actionSaveVideo.triggered.connect(mw.callSaveVideo)
        mw.menuUtils.addAction(mw.actionSaveVideo)

        mw.actionCancelVideo = QtWidgets.QAction('Cancel Video', mw)
        mw.actionCancelVideo.setShortcut('K')
        mw.actionCancelVideo.triggered.connect(mw.cancelVideo)
        mw.menuUtils.addAction(mw.actionCancelVideo)

        mw.menuUtils.addSeparator()

        mw.actionFitHistogram = QtWidgets.QAction('Fit Histogram', mw)
        mw.actionFitHistogram.setShortcut('F')
        mw.actionFitHistogram.triggered.connect(mw.fit_histogram)
        mw.menuUtils.addAction(mw.actionFitHistogram)

        mw.actionViewHistogram = QtWidgets.QAction('View Histogram', mw)
        mw.actionViewHistogram.setShortcut('H')
        mw.actionViewHistogram.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mw.actionViewHistogram.triggered.connect(mw.set_view_histogram)
        mw.menuUtils.addAction(mw.actionViewHistogram)

        mw.actionCenterView = QtWidgets.QAction('Center View', mw)
        mw.actionCenterView.setShortcut('C')
        mw.actionCenterView.triggered.connect(mw.center_view)
        mw.menuUtils.addAction(mw.actionCenterView)
        
        mw.actionSwapView = QtWidgets.QAction('Swap 3D View', mw)
        mw.actionSwapView.setShortcut('Space')
        mw.actionSwapView.triggered.connect(mw.swap_3d_view)
        mw.menuUtils.addAction(mw.actionSwapView)

        mw.menuUtils.addSeparator()

        mw.actionViewObjects = QtWidgets.QAction('View Objects', mw)
        mw.actionViewObjects.setShortcut('O')
        mw.actionViewObjects.setCheckable(True)
        mw.actionViewObjects.setChecked(True)
        mw.actionViewObjects.triggered.connect(mw.update_view)
        mw.menuUtils.addAction(mw.actionViewObjects)

        mw.actionViewTime = QtWidgets.QAction('View Time', mw)
        mw.actionViewTime.setShortcut('P')
        mw.actionViewTime.setCheckable(True)
        mw.actionViewTime.setChecked(False)
        mw.actionViewTime.triggered.connect(mw.update_view)
        mw.menuUtils.addAction(mw.actionViewTime)

        mw.viewActionGroup = QtWidgets.QActionGroup(mw)
        mw.viewActionGroup.addAction(mw.actionViewObjects)
        mw.viewActionGroup.addAction(mw.actionViewTime)
        
        mw.actionViewNextNumber = QtWidgets.QAction('View Next Number', mw)
        mw.actionViewNextNumber.setShortcut('N')
        mw.actionViewNextNumber.setCheckable(True)
        mw.actionViewNextNumber.setChecked(False)
        mw.actionViewNextNumber.triggered.connect(mw.update_view)
        mw.menuUtils.addAction(mw.actionViewNextNumber)

        mw.menu.addMenu(mw.menuUtils)

        mw.menuTurntable = QtWidgets.QMenu('Turntable')

        mw.actionTurntable = QtWidgets.QAction('Start/Stop Turntable', mw)
        mw.actionTurntable.setShortcut('T')
        mw.actionTurntable.triggered.connect(mw.turntable)
        mw.menuTurntable.addAction(mw.actionTurntable)

        mw.actionTurntableFaster = QtWidgets.QAction('Turntable Faster', mw)
        mw.actionTurntableFaster.setShortcut('+')
        mw.actionTurntableFaster.triggered.connect(mw.turntableFaster)
        mw.menuTurntable.addAction(mw.actionTurntableFaster)

        mw.actionTurntableSlower = QtWidgets.QAction('Turntable Slower', mw)
        mw.actionTurntableSlower.setShortcut('-')
        mw.actionTurntableSlower.triggered.connect(mw.turntableSlower)
        mw.menuTurntable.addAction(mw.actionTurntableSlower)

        mw.menu.addMenu(mw.menuTurntable)

        mw.menuSelection = QtWidgets.QMenu('Selection')

        mw.actionSelectAll = QtWidgets.QAction('Select All', mw)
        mw.actionSelectAll.setShortcut('A')
        mw.actionSelectAll.triggered.connect(mw.select_all)
        mw.menuSelection.addAction(mw.actionSelectAll)
        
        mw.actionDeselectAll = QtWidgets.QAction('Deselect All', mw)
        mw.actionDeselectAll.setShortcut('D')
        mw.actionDeselectAll.triggered.connect(mw.deselect_all)
        mw.menuSelection.addAction(mw.actionDeselectAll)
        
        mw.actionInvertSelection = QtWidgets.QAction('Invert Selection', mw)
        mw.actionInvertSelection.setShortcut('Shift+A')
        mw.actionInvertSelection.triggered.connect(mw.invert_selection)
        mw.menuSelection.addAction(mw.actionInvertSelection)

        mw.menu.addMenu(mw.menuSelection)

        mw.menuTime = QtWidgets.QMenu('Time')

        mw.actionLeft = QtWidgets.QAction('Decrement time', mw.centralWidget())
        mw.actionLeft.setShortcut('Left')
        mw.actionLeft.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mw.actionLeft.triggered.connect(mw.decrementTime)
        mw.menuTime.addAction(mw.actionLeft)

        mw.actionRight = QtWidgets.QAction('Increment time', mw.centralWidget())
        mw.actionRight.setShortcut('Right')
        mw.actionRight.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mw.actionRight.triggered.connect(mw.incrementTime)
        mw.menuTime.addAction(mw.actionRight)

        mw.actionInit = QtWidgets.QAction('Go to init', mw.centralWidget())
        mw.actionInit.setShortcut('Home')
        mw.actionInit.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mw.actionInit.triggered.connect(mw.setTimeInit)
        mw.menuTime.addAction(mw.actionInit)

        mw.actionEnd = QtWidgets.QAction('Go to end', mw.centralWidget())
        mw.actionEnd.setShortcut('End')
        mw.actionEnd.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        mw.actionEnd.triggered.connect(mw.setTimeEnd)
        mw.menuTime.addAction(mw.actionEnd)

        mw.menu.addMenu(mw.menuTime)

        mw.statusBar = QtWidgets.QStatusBar(mw)
        mw.statusLabel = QtWidgets.QLabel()
        mw.statusBar.addWidget(mw.statusLabel)
        mw.setStatusBar(mw.statusBar)
