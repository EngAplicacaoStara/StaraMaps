import importlib
import os
import subprocess
import sys

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QThread, Qt, pyqtSignal, QCoreApplication
from qgis.PyQt.QtGui import QColor, QPalette
from qgis.PyQt.QtWidgets import QWidget, QGraphicsDropShadowEffect
from qgis.core import Qgis
from qgis.utils import iface
import importlib.util
from .loading import Loading

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/InfoWindow.ui'))


class InstallThread(QThread):
    info_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.__file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'requirements.txt')

    @staticmethod
    def get_python_executable():
        qgis_bin_dir = os.path.dirname(sys.executable)
        candidates = ["python-qgis.bat", "python-qgis-ltr.bat"]

        for candidate in candidates:
            candidate_path = os.path.join(qgis_bin_dir, candidate)
            if os.path.exists(candidate_path):
                return candidate_path

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

    def tr(self, message):
        return QCoreApplication.translate('InfoWindow', message)

    def __init__(self, parent=None):
        super(InfoWindow, self).__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setupUi(self)
        # Qt6: label text can inherit a light-on-light palette; force readable color.
        self.setStyleSheet(self.styleSheet() + '''
            QLabel { color: rgb(45, 45, 45); }
        ''')
        # QSS alone can still be overridden by platform styles; set palette for the label.
        label_palette = self.label.palette()
        label_palette.setColor(QPalette.ColorRole.WindowText, QColor(45, 45, 45))
        label_palette.setColor(QPalette.ColorRole.Text, QColor(45, 45, 45))
        self.label.setPalette(label_palette)
        self.label.setForegroundRole(QPalette.ColorRole.Text)
        self.label.setStyleSheet('color: rgb(45, 45, 45);')
        self.label.setWordWrap(True)
        self.label.setMinimumHeight(22)
        self.label.setVisible(True)
        self.init()

    def init(self) -> None:
        shadow = QGraphicsDropShadowEffect()
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setBlurRadius(15)
        self.setGraphicsEffect(shadow)
        self.label.setText(self.tr("Iniciando..."))
        self.loading = Loading(self.frame_4)
        self.loading.start()
        self.loading.show()

        self.install_thread = InstallThread()
        self.install_thread.info_signal.connect(self.label.setText)
        self.install_thread.error_signal.connect(lambda msg: iface.messageBar().pushWarning(self.tr("Erro"), msg))
        self.install_thread.finished_signal.connect(lambda: (
            iface.messageBar().pushSuccess(self.tr("Concluído"), self.tr("Instalação finalizada!")),
            self.finished_signal.emit()
        ))
        self.install_thread.start()
