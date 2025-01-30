import os

from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QLabel


class Loading(QLabel):
    def __init__(self, parent=None):
        super(Loading, self).__init__(parent)
        self.setFixedSize(32, 32)
        self.setObjectName('loading_label')
        self.setStyleSheet('''#loading_label{
                                        border: none;
                                        background-color: transparent;
                                }
                                    ''')

        self.__movie = QMovie(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icons', '1494.gif'))
        self.setMovie(self.__movie)

        width = self.width()
        height = self.height()
        wid_width = self.parent().width()
        wid_height = self.parent().height()
        right_margin = 0

        x = int((wid_width - right_margin) / 2 - (width / 2))
        y = int((wid_height - height) / 2)

        self.setGeometry(x, y, width, height)

    def start(self) -> None:
        self.parent().setEnabled(False)
        self.__movie.start()

    def stop(self) -> None:
        self.parent().setEnabled(True)
        self.__movie.stop()
