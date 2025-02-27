import os
import subprocess
import sys

from PyQt5 import uic
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect

from .loading import Loading

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/InfoWindow.ui'), resource_suffix='')


class InstallThread(QThread):
    info_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.__file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'requirements.txt')

    def run(self) -> None:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        if os.path.isfile(self.__file):
            with open(self.__file, 'r') as file:
                requirements = file.read().splitlines()
                print(requirements)

            for d in requirements:
                try:
                    __import__(d)
                    self.info_signal.emit(f'{d} já instalado')
                except:
                    self.info_signal.emit(f'Instalando {d}...')
                    subprocess.Popen(['python3', '-m', 'pip', 'install', d], startupinfo=si)
        else:
            print(f'{self.__file} não encontrado.')

        self.finished_signal.emit()


class InfoWindow(QWidget, FORM_CLASS):
    finished_signal = pyqtSignal()

    def __init__(self, parent=None):
        super(InfoWindow, self).__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setupUi(self)
        self.init()

    def init(self) -> None:
        shadow = QGraphicsDropShadowEffect()
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setBlurRadius(15)
        self.setGraphicsEffect(shadow)
        self.loading = Loading(self.frame_4)
        self.loading.start()
        self.loading.show()

        self.install_thread = InstallThread()
        self.install_thread.info_signal.connect(lambda text:
                                                self.label.setText(text)
                                                )
        self.install_thread.finished_signal.connect(self.finished_signal.emit)
        self.install_thread.start()
