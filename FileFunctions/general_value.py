from qgis.PyQt.QtCore import QObject, pyqtSlot

from ..qgisFuncs import add_buttons_to_grid, upgrade_grid
from ..values_window import GeneralValues


class GeneralValue(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.selected_list = []
        self.unselected_list = []
        self._gen_window = None
        self.init()

    def init(self) -> None:
        try:
            self.main.pushButton_return_gen_value.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.main.pushButton_return_gen_value.clicked.connect(lambda: self.deleteLater())
        self.main.back_button_hide_signal.emit()
        self.main.stackedWidget.setCurrentIndex(9)
        add_buttons_to_grid(self.main.gridLayout_17, self.main.layer, self.on_click)

    def _current_classes(self):
        renderer = self.main.layer.renderer()
        return len(renderer.ranges()) if hasattr(renderer, 'ranges') else 5

    @pyqtSlot(int, object)
    def on_click(self, index, obj):
        if self._gen_window is not None:
            try:
                self._gen_window.deleteLater()
            except RuntimeError:
                pass
            self._gen_window = None

        upgrade_grid(self.main.layer, self.main.iface, index, classes=self._current_classes())

        features = self.main.layer.getFeatures()

        self._gen_window = GeneralValues(
            obj.text(),
            features,
            index,
            self.main.pushButton_return_gen_value,
            self.main.page_23
        )
        self._gen_window.update_features_signal.connect(self.main.on_layer_update_feat)
        self._gen_window.close_signal.connect(lambda: self._gen_window.deleteLater())
        self._gen_window.show()

    def deleteLater(self) -> None:
        self.main.stackedWidget.setCurrentIndex(0)
        self.main.back_button_show_signal.emit()
        try:
            self.main.pushButton_return_gen_value.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        super().deleteLater()
