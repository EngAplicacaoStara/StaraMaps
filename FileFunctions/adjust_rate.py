from PyQt5.QtCore import QObject, pyqtSlot
from qgis._core import QgsAggregateCalculator

from canvas.map_canvas import RateMapCanvas
from ..qgisFuncs import upgrade_grid, add_buttons_to_grid
from ..values_window import BiggerValues, SmallerValues, BetweenValues, ChangeMValues


class Rate(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.max_value = None
        self.min_value = None
        self.index = 0
        self.init()

    def init(self) -> None:
        self.main.pushButton_return_taxas.clicked.connect(lambda: self.deleteLater())
        self.main.back_button_hide_signal.emit()
        self.main.stackedWidget.setCurrentIndex(2)
        self.rate_canvas = RateMapCanvas(self.main.layer, self.main.frame_7)
        self.rate_canvas.bigger_signal.connect(self.on_bigger_click)
        self.rate_canvas.smaller_signal.connect(self.on_smaller_click)
        self.rate_canvas.between_signal.connect(self.on_between_click)
        self.rate_canvas.add_signal.connect(self.on_add_click)

        add_buttons_to_grid(self.main.gridLayout_7, self.main.layer, self.on_click)

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0)
        self.main.stackedWidget_2.setCurrentIndex(0)
        self.main.label_taxas.setText(self.tr('Taxas > Selecione uma coluna'))
        self.rate_canvas.points.deleteLater()
        self.rate_canvas.dock.deleteLater()
        self.rate_canvas.deleteLater()
        self.main.back_button_show_signal.emit()
        self.main.pushButton_return_taxas.disconnect()
        super().deleteLater()

    @pyqtSlot(int, object)
    def on_click(self, index, obj):
        upgrade_grid(self.main.layer, self.main.iface, index)
        self.main.stackedWidget_2.setCurrentIndex(1)
        self.main.label_taxas.setText(self.tr('Taxas > Selecione uma coluna') + ' > ' + obj.text())

        self.max_value = self.main.layer.aggregate(QgsAggregateCalculator.Max, obj.text())[0]
        self.min_value = self.main.layer.aggregate(QgsAggregateCalculator.Min, obj.text())[0]
        self.index = index
        self.rate_canvas.resize(self.main.frame_7.size())
        self.rate_canvas.show()

    @pyqtSlot()
    def on_bigger_click(self):
        features, geo = self.rate_canvas.points.get_points()
        self.v_window = BiggerValues(self.min_value, self.max_value, features, geo, self.index,
                                     self.main.pushButton_return_taxas,
                                     self.main.frame_7)
        self.v_window.update_features_signal.connect(self.main.on_layer_update_feat)
        self.v_window.finish_signal.connect(lambda: (
            self.rate_canvas.show(),
            upgrade_grid(self.main.layer, self.main.iface, self.index),
            self.v_window.deleteLater()
        ))
        self.v_window.close_signal.connect(lambda: (
            self.rate_canvas.show(),
            self.v_window.deleteLater()
        ))
        self.v_window.show()

    @pyqtSlot()
    def on_smaller_click(self):
        features, geo = self.rate_canvas.points.get_points()
        self.v_window = SmallerValues(self.min_value, self.max_value, features, geo, self.index,
                                      self.main.pushButton_return_taxas,
                                      self.main.frame_7)
        self.v_window.update_features_signal.connect(self.main.on_layer_update_feat)
        self.v_window.finish_signal.connect(lambda: (
            self.rate_canvas.show(),
            upgrade_grid(self.main.layer, self.main.iface, self.index),
            self.v_window.deleteLater()
        ))
        self.v_window.close_signal.connect(lambda: (
            self.rate_canvas.show(),
            self.v_window.deleteLater()
        ))
        self.v_window.show()

    @pyqtSlot()
    def on_between_click(self):
        features, geo = self.rate_canvas.points.get_points()
        self.v_window = BetweenValues(self.min_value, self.max_value, features, geo, self.index,
                                      self.main.pushButton_return_taxas,
                                      self.main.frame_7)
        self.v_window.update_features_signal.connect(self.main.on_layer_update_feat)
        self.v_window.finish_signal.connect(lambda: (
            self.rate_canvas.show(),
            upgrade_grid(self.main.layer, self.main.iface, self.index),
            self.v_window.deleteLater()
        ))
        self.v_window.close_signal.connect(lambda: (
            self.rate_canvas.show(),
            self.v_window.deleteLater()
        ))
        self.v_window.show()

    @pyqtSlot()
    def on_add_click(self):
        features, geo = self.rate_canvas.points.get_points()
        self.v_window = ChangeMValues(self.min_value, self.max_value, features, geo, self.index,
                                      self.main.pushButton_return_taxas,
                                      self.main.frame_7)
        self.v_window.update_features_signal.connect(self.main.on_layer_update_feat)
        self.v_window.finish_signal.connect(lambda: (
            self.rate_canvas.show(),
            upgrade_grid(self.main.layer, self.main.iface, self.index),
            self.v_window.deleteLater()
        ))
        self.v_window.close_signal.connect(lambda: (
            self.rate_canvas.show(),
            self.v_window.deleteLater()
        ))
        self.v_window.show()
