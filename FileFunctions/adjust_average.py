from PyQt5.QtCore import pyqtSlot, QObject
from qgis._core import QgsAggregateCalculator

from ..qgisFuncs import upgrade_grid, add_buttons_to_grid
from ..values_window import MeanValues


class AdjustAverage(QObject):

    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.init()

    def init(self) -> None:
        self.main.stackedWidget.setCurrentIndex(7)
        self.main.back_button_hide_signal.emit()
        self.main.pushButton_return_mean.clicked.connect(lambda: self.deleteLater())

        add_buttons_to_grid(self.main.gridLayout_6, self.main.layer, self.on_click)

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0)
        self.main.back_button_show_signal.emit()
        self.main.pushButton_return_mean.disconnect()
        super().deleteLater()

    @pyqtSlot(int, object)
    def on_click(self, index, obj):
        upgrade_grid(self.main.layer, self.main.iface, index)
        features = self.main.layer.getFeatures()

        mean_value = self.main.layer.aggregate(QgsAggregateCalculator.Mean, obj.text())[0]

        mean_window = MeanValues(
            obj.text(),
            mean_value,
            features,
            index,
            self.main.pushButton_return_mean,
            self.main.page_17
        )
        mean_window.update_features_signal.connect(self.main.on_layer_update_feat)
        mean_window.finish_signal.connect(lambda:
                                          (
                                              upgrade_grid(self.main.layer, self.main.iface, index),
                                              mean_window.deleteLater()
                                          )
                                          )
        mean_window.close_signal.connect(lambda: (
            mean_window.deleteLater()
        ))
        mean_window.show()
