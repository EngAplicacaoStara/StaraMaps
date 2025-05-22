import sys
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface
from qgis.core import Qgis

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/field_name.ui'), resource_suffix='')


class FieldName(QWidget, FORM_CLASS):
    on_click_accept = pyqtSignal(str)

    def __init__(self, parent=None):
        super(FieldName, self).__init__(parent.dock)
        self.setupUi(self)
        self.goButton.clicked.connect(self.on_go_clicked)
        self.cancelButton.clicked.connect(self.hide)

    def on_go_clicked(self):
        # Check Name Field
        if self.lineEdit.text() == "":
            iface.messageBar().pushMessage("Digine o nome do campo", level=Qgis.MessageLevel.Info,
                                           duration=5)
            return
        self.hide()
        self.on_click_accept.emit(self.lineEdit.text())


