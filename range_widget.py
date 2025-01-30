import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QWidget

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/range.ui'), resource_suffix='')


class RangeWidget(QWidget, FORM_CLASS):
    on_update = pyqtSignal()
    on_feat_update = pyqtSignal(object)

    def __init__(self, layer, index, range_index, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.layer = layer
        self.index = index
        self.lower_value = 0
        self.upper_value = 0
        regex_only_num = QRegExp("[-+]?[0-9]*\.?[0-9]+")
        line_edit_val = QRegExpValidator(regex_only_num, self.newLineEdit)
        self.newLineEdit.setValidator(line_edit_val)
        self.range_index = range_index

    def set_lowerValue(self, value):
        self.lower_value = value
        self.label_2.setText(str(value))

    def set_upperValue(self, value):
        self.upper_value = value
        self.label_3.setText(str(value))

    def set_color(self, color_hex):
        self.frame.setStyleSheet(f'''
            background-color: {color_hex};
        ''')
