import os

from qgis.PyQt.QtCore import QObject, pyqtSlot
from qgis._core import QgsVectorFileWriter, QgsVectorLayer, Qgis
from qgis.utils import iface

from ..canvas.create_field_map_canvas import CreateFieldMapCanvas


class CreateField(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.index = 0
        self.canvas = CreateFieldMapCanvas(self.main)
        self.init()

    def init(self) -> None:
        self.main.stackedWidget.setCurrentIndex(10)
        self.main.back_button_hide_signal.emit()
        try:
            self.main.pushButton_return_create_field.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.main.pushButton_return_create_field.clicked.connect(lambda: self.deleteLater())
        self.canvas.resize(self.main.page_26.size())
        self.canvas.feat_geo_signal.connect(self.save_new_layer)
        self.canvas.show()

    @pyqtSlot(QgsVectorLayer, str)
    def save_new_layer(self, layer, name) -> None:
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        out_path = os.path.join(os.path.dirname(self.main.layer.source()), f"{name}.shp")
        error, msg, *_ = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, out_path, layer.transformContext(), options
        )
        if error != QgsVectorFileWriter.NoError:
            iface.messageBar().pushMessage(
                self.tr("Erro ao salvar bordadura"), msg, level=Qgis.Critical, duration=5
            )
            return
        self.main.main.check_file_extension(out_path)
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
