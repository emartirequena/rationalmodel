from PyQt5 import QtWidgets

class TurntableVideoWidget(QtWidgets.QDialog):
    def __init__(self, parent, current_frame) -> None:
        super().__init__(parent)
        
        self.vlayout = QtWidgets.QVBoxLayout()
        self.gridlayout = QtWidgets.QGridLayout()
        self.vlayout.addLayout(self.gridlayout)

        self.label1 = QtWidgets.QLabel('Init frame')
        self.gridlayout.addWidget(self.label1, 0, 0)
        self.init_frame = QtWidgets.QSpinBox(self)
        self.init_frame.setMinimum(0)
        self.init_frame.setMaximum(10000)
        self.init_frame.setValue(current_frame)
        self.gridlayout.addWidget(self.init_frame, 0, 1)

        self.label2 = QtWidgets.QLabel('End frame')
        self.gridlayout.addWidget(self.label2, 1, 0)
        self.end_frame = QtWidgets.QSpinBox(self)
        self.end_frame.setMinimum(0)
        self.end_frame.setMaximum(10000)
        self.end_frame.setValue(current_frame)
        self.gridlayout.addWidget(self.end_frame, 1, 1)

        self.label3 = QtWidgets.QLabel('Video frames')
        self.gridlayout.addWidget(self.label3, 2, 0)
        self.video_frames = QtWidgets.QSpinBox(self)
        self.video_frames.setMinimum(0)
        self.video_frames.setMaximum(10000)
        self.video_frames.setValue(100)
        self.gridlayout.addWidget(self.video_frames, 2, 1)

        self.label4 = QtWidgets.QLabel('Turn degrees')
        self.gridlayout.addWidget(self.label4, 3, 0)
        self.turn_degrees = QtWidgets.QSpinBox(self)
        self.turn_degrees.setMinimum(0)
        self.turn_degrees.setMaximum(10000)
        self.turn_degrees.setValue(360)
        self.gridlayout.addWidget(self.turn_degrees, 3, 1)

        self.hlayout = QtWidgets.QHBoxLayout()
        self.hlayout.addStretch()
        self.button_save = QtWidgets.QPushButton('Save Video', self)
        self.button_save.clicked.connect(self.save)
        self.hlayout.addWidget(self.button_save)
        
        self.button_cancel = QtWidgets.QPushButton('Cancel', self)
        self.button_cancel.clicked.connect(self.close)
        self.hlayout.addWidget(self.button_cancel)

        self.vlayout.addLayout(self.hlayout)
        self.setLayout(self.vlayout)

        self.setWindowTitle('Turntable Video')

    def save(self):
        if self.init_frame.value() > self.end_frame.value():
            QtWidgets.QMessageBox.critical(self, 'End frame must be greater or equal than init frame')
            return
        self.close()
        self.parent().saveTurntableVideo(
            self.init_frame.value(), 
            self.end_frame.value(), 
            self.video_frames.value(),
            self.turn_degrees.value()
        )



