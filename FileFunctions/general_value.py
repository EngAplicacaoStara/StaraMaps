from PyQt5.QtCore import QObject, pyqtSlot

from ..qgisFuncs import add_buttons_to_grid, upgrade_grid
from ..values_window import GeneralValues


class GeneralValue(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.selected_list = []
        self.unselected_list = []
        self.init()

    def init(self) -> None:
        self.main.pushButton_return_gen_value.clicked.connect(lambda: self.deleteLater())
        self.main.back_button_hide_signal.emit()
        self.main.stackedWidget.setCurrentIndex(9)

        add_buttons_to_grid(self.main.gridLayout_17, self.main.layer, self.on_click)

    @pyqtSlot(int, object)
    def on_click(self, index, obj):
        upgrade_grid(self.main.layer, self.main.iface, index)

        features = self.main.layer.getFeatures()

        mean_window = GeneralValues(
            obj.text(),
            features,
            index,
            self.main.pushButton_return_gen_value,
            self.main.page_23
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

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0)
        self.main.back_button_show_signal.emit()
        self.main.pushButton_return_gen_value.disconnect()
        super().deleteLater()
