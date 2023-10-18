from PyQt5 import QtWidgets

class SaveSpecialsWidget(QtWidgets.QDialog):
    def __init__(self, parent, current_period, maximum_period) -> None:
        super().__init__(parent)
        
        self.vlayout = QtWidgets.QVBoxLayout()
        self.gridlayout = QtWidgets.QGridLayout()
        self.vlayout.addLayout(self.gridlayout)

        self.label1 = QtWidgets.QLabel('Init period')
        self.gridlayout.addWidget(self.label1, 0, 0)
        self.init_period = QtWidgets.QSpinBox(self)
        self.init_period.setMinimum(1)
        self.init_period.setMaximum(maximum_period)
        self.init_period.setValue(current_period)
        self.gridlayout.addWidget(self.init_period, 0, 1)

        self.label2 = QtWidgets.QLabel('End period')
        self.gridlayout.addWidget(self.label2, 1, 0)
        self.end_period = QtWidgets.QSpinBox(self)
        self.end_period.setMinimum(1)
        self.end_period.setMaximum(maximum_period)
        self.end_period.setValue(maximum_period)
        self.gridlayout.addWidget(self.end_period, 1, 1)

        self.label3 = QtWidgets.QLabel('Subfolder')
        self.gridlayout.addWidget(self.label3, 2, 0)
        self.subfolder = QtWidgets.QLineEdit(self)
        self.gridlayout.addWidget(self.subfolder, 2, 1)

        self.hlayout = QtWidgets.QHBoxLayout()
        self.hlayout.addStretch()
        self.button_save = QtWidgets.QPushButton('Save Specials', self)
        self.button_save.clicked.connect(self.save)
        self.hlayout.addWidget(self.button_save)
        
        self.button_cancel = QtWidgets.QPushButton('Cancel', self)
        self.button_cancel.clicked.connect(self.close)
        self.hlayout.addWidget(self.button_cancel)

        self.vlayout.addLayout(self.hlayout)
        self.setLayout(self.vlayout)

        self.setWindowTitle('Save specials')

    def save(self):
        if self.end_period.value() <= self.init_period.value():
            QtWidgets.QErrorMessage(self, 'End period must be greater than init period')
            return
        self.close()
        self.parent().saveSpecialsNumbers(self.init_period.value(), self.end_period.value(), self.subfolder.text())


