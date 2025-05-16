import os

from PyQt5.QtCore import QObject

from canvas.create_field_map_canvas import CreateFieldMapCanvas
from qgis.PyQt.QtCore import pyqtSlot
from qgis._core import QgsVectorFileWriter, QgsVectorLayer


class CreateField(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.index = 0
        self.canvas = CreateFieldMapCanvas(self.main)
        print(self.main.layer.source())
        self.init()

    def init(self) -> None:
        self.main.stackedWidget.setCurrentIndex(10)
        self.main.back_button_hide_signal.emit()
        self.main.pushButton_return_create_field.clicked.connect(lambda: self.deleteLater())
        self.canvas.resize(self.main.page_26.size())
        self.canvas.feat_geo_signal.connect(self.save_new_layer)
        self.canvas.show()

    @pyqtSlot(QgsVectorLayer, str)
    def save_new_layer(self, layer, name) -> None:
        error = QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            os.path.dirname(self.main.layer.source()) + f"/{name}.shp",
            "UTF-8",
            layer.crs(),
            "ESRI Shapefile"
        )
        self.main.main.check_file_extension(os.path.dirname(self.main.layer.source()) + f"/{name}.shp")
        self.deleteLater()

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0)
        self.main.back_button_show_signal.emit()
        self.main.pushButton_return_create_field.disconnect()
        self.canvas.points.deleteLater()
        self.canvas.dock.deleteLater()
        self.canvas.deleteLater()
        self.main.back_animation_signal.emit()
        super().deleteLater()
