import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QVariant, QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect
from qgis._core import QgsField

from .loading import Loading
from .message import Message, Messages
from .qgisFuncs import RemoveBiggerValues, RemoveSmallerValues, RemoveBetweenValues, ChangeMapValues, ChangeMean, \
    AddNewColumn

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/ValuesWindow.ui'), resource_suffix='')


class ValuesWindow(QWidget, FORM_CLASS):
    close_signal = pyqtSignal()
    finish_signal = pyqtSignal()
    update_features_signal = pyqtSignal(object)

    def __init__(self, back_button=None, parent=None):
        super(ValuesWindow, self).__init__(parent)
        self.setupUi(self)
        regex = QRegularExpression(r"^-?\d*\.?\d+$")
        validator = QRegularExpressionValidator(regex, self.lineEdit)
        self.lineEdit.setValidator(validator)

        self.back_button = back_button
        shadow = QGraphicsDropShadowEffect()
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setBlurRadius(15)
        self.progressBar.hide()
        self.pushButtonClose.clicked.connect(self.close_signal.emit)
        self.goButton.clicked.connect(self.on_go_clicked)
        self.setGraphicsEffect(shadow)
        self.centralize()
        self.hide()

    def centralize(self) -> None:
        self.resize(self.parent().size())
        '''self.move(int(self.parent().width() / 2 - self.width() / 2),
                  int(self.parent().height() / 2 - self.height() / 2))'''

    def check_progress(self):
        if self.progressBar.isVisible():
            self.progressBar.hide()
            self.pushButtonClose.setEnabled(True)
        else:
            self.progressBar.show()
            self.pushButtonClose.setEnabled(False)

    @pyqtSlot()
    def on_go_clicked(self):
        raise NotImplementedError('Não implementado.')

    @pyqtSlot(float)
    def on_percent_update(self, value):
        self.progressBar.setValue(value)


class BiggerValues(ValuesWindow):
    def __init__(self, min_v, max_v, features, geo, index, back_button, parent=None):
        super(BiggerValues, self).__init__(back_button, parent)
        self.min = min_v
        self.max = max_v
        self.features = features
        self.geo = geo
        self.index = index
        self.init()

    def init(self) -> None:
        self.goButton.setText(self.tr("Avançar"))
        self.lineEdit_2.hide()
        self.infoLabel_2.hide()
        self.infoLabel.setText(
            self.tr("Excluir Valores MAIORES que:") + "\n" + f"{self.min}" + self.tr(" e ") + f"{self.max}")

    def on_go_clicked(self) -> None:
        text = self.lineEdit.text()
        if text == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        self.loading = Loading(self.goButton)
        self.loading.start()
        self.loading.show()

        self.check_progress()
        self.back_button.setEnabled(False)
        self.remove_values = RemoveBiggerValues(
            self.features,
            self.geo,
            float(text),
            self.index
        )
        self.remove_values.on_finished.connect(lambda feats: (
            self.update_features_signal.emit(feats),
            self.loading.stop(),
            self.loading.deleteLater(),
            self.check_progress(),
            self.remove_values.deleteLater(),
            self.finish_signal.emit(),
            self.back_button.setEnabled(True),
            self.deleteLater()
        ))
        self.remove_values.on_percent_update.connect(self.on_percent_update)
        self.remove_values.start()


class SmallerValues(ValuesWindow):
    def __init__(self, min, max, features, geo, index, back_button, parent=None):
        super().__init__(back_button, parent)
        self.min = min
        self.max = max
        self.features = features
        self.geo = geo
        self.index = index
        self.init()

    def init(self) -> None:
        self.goButton.setText(self.tr("Avançar"))
        self.lineEdit_2.hide()
        self.infoLabel_2.hide()
        self.infoLabel.setText(
            self.tr("Excluir Valores MENORES que:") + "\n" + f"{self.min}" + self.tr(" e ") + f"{self.max}")

    def on_go_clicked(self) -> None:
        text = self.lineEdit.text()
        if text == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        self.loading = Loading(self.goButton)
        self.loading.start()
        self.loading.show()

        self.check_progress()
        self.back_button.setEnabled(False)
        self.remove_values = RemoveSmallerValues(
            self.features,
            self.geo,
            float(text),
            self.index
        )
        self.remove_values.on_finished.connect(lambda feats: (
            self.update_features_signal.emit(feats),
            self.loading.stop(),
            self.loading.deleteLater(),
            self.check_progress(),
            self.remove_values.deleteLater(),
            self.finish_signal.emit(),
            self.back_button.setEnabled(True),
            self.deleteLater()
        ))
        self.remove_values.on_percent_update.connect(self.on_percent_update)
        self.remove_values.start()


class BetweenValues(ValuesWindow):
    def __init__(self, min, max, features, geo, index, back_button, parent=None):
        super().__init__(back_button, parent)
        self.min = min
        self.max = max
        self.features = features
        self.geo = geo
        self.index = index
        self.init()

    def init(self) -> None:
        self.goButton.setText(self.tr("Avançar"))
        self.infoLabel_2.hide()
        self.lineEdit_2.show()
        self.infoLabel.setText(
            self.tr("Excluir Valores ENTRE:") + "\n" + f"{self.min}" + self.tr(" e ") + f"{self.max}")

    def on_go_clicked(self) -> None:
        text = self.lineEdit.text()
        text_2 = self.lineEdit_2.text()
        if text == '' or text_2 == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        self.loading = Loading(self.goButton)
        self.loading.start()
        self.loading.show()

        self.check_progress()
        self.back_button.setEnabled(False)
        self.remove_values = RemoveBetweenValues(
            self.features,
            self.geo,
            float(text),
            float(text_2),
            self.index
        )
        self.remove_values.on_finished.connect(lambda feats: (
            self.update_features_signal.emit(feats),
            self.loading.stop(),
            self.loading.deleteLater(),
            self.check_progress(),
            self.remove_values.deleteLater(),
            self.finish_signal.emit(),
            self.back_button.setEnabled(True),
            self.deleteLater()
        ))
        self.remove_values.on_percent_update.connect(self.on_percent_update)
        self.remove_values.start()


class ChangeMValues(ValuesWindow):
    def __init__(self, min_v, max_v, features, geo, index, back_button, parent=None):
        super().__init__(back_button, parent)
        self.min = min_v
        self.max = max_v
        self.features = features
        self.geo = geo
        self.index = index
        self.init()

    def init(self) -> None:
        self.goButton.setText(self.tr("Avançar"))
        self.lineEdit_2.hide()
        self.infoLabel_2.hide()
        self.infoLabel.setText(self.tr("Adicionar valor:") + "\n" + f"{self.min}" + self.tr(" e ") + f"{self.max}")

    def on_go_clicked(self) -> None:
        text = self.lineEdit.text()
        if text == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        self.loading = Loading(self.goButton)
        self.loading.start()
        self.loading.show()

        self.check_progress()
        self.back_button.setEnabled(False)
        self.change_values = ChangeMapValues(
            self.features,
            self.geo,
            float(text),
            self.index
        )
        self.change_values.on_finished.connect(lambda feats: (
            self.update_features_signal.emit(feats),
            self.loading.stop(),
            self.loading.deleteLater(),
            self.check_progress(),
            self.change_values.deleteLater(),
            self.finish_signal.emit(),
            self.back_button.setEnabled(True),
            self.deleteLater()
        ))
        self.change_values.on_percent_update.connect(self.on_percent_update)
        self.change_values.start()


class MeanValues(ValuesWindow):
    def __init__(self, field_name, current_mean, features, index, back_button, parent=None):
        super(MeanValues, self).__init__(back_button, parent)
        self.current_mean = current_mean
        if self.current_mean == None:
            self.current_mean = 0
        self.field_name = field_name
        self.features = features
        self.index = index
        self.init()

    def init(self) -> None:
        self.goButton.setText(self.tr("Avançar"))
        self.infoLabel_2.hide()
        self.lineEdit_2.hide()
        self.infoLabel.setText(
            self.tr("Ajustar Média da coluna ") + f"{self.field_name}" + "\n" + f"{'%.2f' % self.current_mean}"
        )

    def on_go_clicked(self):
        text = self.lineEdit.text()
        if text == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        self.loading = Loading(self.goButton)
        self.loading.start()
        self.loading.show()

        self.check_progress()
        self.back_button.setEnabled(False)
        new_mean = float(text)

        diff = new_mean - self.current_mean

        self.change_values = ChangeMean(self.features, None, diff, self.index)
        self.change_values.on_finished.connect(lambda feats: (
            self.update_features_signal.emit(feats),
            self.loading.stop(),
            self.loading.deleteLater(),
            self.check_progress(),
            self.change_values.deleteLater(),
            self.finish_signal.emit(),
            self.back_button.setEnabled(True),
            self.deleteLater()
        ))
        self.change_values.on_percent_update.connect(self.on_percent_update)
        self.change_values.start()


class ColumnValues(ValuesWindow):

    def __init__(self, layer, back_button, parent=None):
        super(ColumnValues, self).__init__(back_button, parent)
        self.layer = layer

        self.goButton.setText(self.tr("Avançar"))
        self.infoLabel.setText(self.tr("Nome da Coluna"))
        self.infoLabel_2.setText(self.tr("Valor"))

        regex = QRegularExpression(r"^[a-zA-Z0-9]+$")
        validator = QRegularExpressionValidator(regex, self.lineEdit)
        self.lineEdit.setValidator(validator)

    def on_go_clicked(self):
        text_1 = self.lineEdit.text()
        text_2 = self.lineEdit_2.text()
        if text_1 == '' or text_2 == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        if text_1.isnumeric():
            self.m = Message(Messages.only_numeric(self), self)
            self.m.show()
            return

        self.loading = Loading(self.goButton)
        self.loading.start()
        self.loading.show()
        self.check_progress()
        self.back_button.setEnabled(False)

        if text_1.isnumeric():
            area_field = QgsField(int(text_1), QVariant.Int)
        else:
            area_field = QgsField(text_1, QVariant.String)

        self.layer.dataProvider().addAttributes([area_field])
        self.layer.updateFields()

        idx = self.layer.dataProvider().fieldNameIndex(text_1)
        features = self.layer.getFeatures()
        self.n_c = AddNewColumn(features, idx, text_2)
        self.n_c.on_finished.connect(
            lambda x: (
                self.update_features_signal.emit(x),
                self.loading.stop(),
                self.loading.deleteLater(),
                self.check_progress(),
                self.n_c.deleteLater(),
                self.layer.updateFields(),
                self.finish_signal.emit(),
                self.back_button.setEnabled(True),
                self.deleteLater()
            ))
        self.n_c.on_percent_update.connect(self.on_percent_update)
        self.n_c.start()


class GeneralValues(ValuesWindow):
    def __init__(self, field_name, features, index, back_button, parent=None):
        super(GeneralValues, self).__init__(back_button, parent)
        self.field_name = field_name
        self.features = features
        self.index = index
        self.init()

    def init(self) -> None:
        self.goButton.setText(self.tr("Avançar"))
        self.infoLabel_2.setText(self.tr("Valor"))
        self.lineEdit.hide()
        self.infoLabel.hide()

    def on_go_clicked(self):
        text = self.lineEdit_2.text()
        if text == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        self.loading = Loading(self.goButton)
        self.loading.start()
        self.loading.show()

        self.check_progress()
        self.back_button.setEnabled(False)

        self.change_values = ChangeMapValues(self.features, None, int(text), self.index)
        self.change_values.on_finished.connect(lambda feats: (
            self.update_features_signal.emit(feats),
            self.loading.stop(),
            self.loading.deleteLater(),
            self.check_progress(),
            self.change_values.deleteLater(),
            self.finish_signal.emit(),
            self.back_button.setEnabled(True),
            self.deleteLater()
        ))
        self.change_values.on_percent_update.connect(self.on_percent_update)
        self.change_values.start()
