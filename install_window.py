import importlib
import os
import subprocess
import sys

from PyQt5 import uic
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect
from qgis.core import Qgis
from qgis.utils import iface
import importlib.util
from .loading import Loading

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/InfoWindow.ui'), resource_suffix='')


class InstallThread(QThread):
    info_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.__file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'requirements.txt')

    @staticmethod
    def get_python_executable():
        full_version = Qgis.QGIS_VERSION  # Ex: '3.34.11-Prizren'
        qgis_version = full_version.split('-')[0]  # '3.34.11'

        paths = [
            fr"C:\Program Files\QGIS {qgis_version}\bin\python-qgis-ltr.bat",
            fr"C:\Program Files\QGIS {qgis_version}\bin\python-qgis.bat"
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return None

    def ensure_package_installed(self, package_name):

        python_exec = self.get_python_executable()
        if not python_exec:
            self.info_signal.emit(f'Python Path not found...')
            self.error_signal.emit("Não foi possível localizar o interpretador Python do QGIS.")
            return

        try:
            subprocess.run(
                [python_exec, "-m", "pip", "install", package_name],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.CalledProcessError:
            self.info_signal.emit(f'Erro ao instalar {package_name}')
            self.error_signal.emit(f"Falha ao instalar o pacote '{package_name}'")

    def run(self) -> None:
        if os.path.isfile(self.__file):
            with open(self.__file, 'r') as file:
                requirements = file.read().splitlines()

            for d in requirements:
                try:
                    importlib.import_module(d)
                    self.info_signal.emit(f'{d} já está instalado')
                except ImportError:
                    self.info_signal.emit(f'Instalando {d}...')
                    self.ensure_package_installed(d)
        else:
            self.error_signal.emit(f'{self.__file} não encontrado.')

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
        self.install_thread.error_signal.connect(lambda msg: iface.messageBar().pushWarning("Erro", msg))
        self.install_thread.finished_signal.connect(lambda: (
            iface.messageBar().pushSuccess("Concluído", "Instalação finalizada!"),
            self.finished_signal.emit()
        ))
        self.install_thread.start()
