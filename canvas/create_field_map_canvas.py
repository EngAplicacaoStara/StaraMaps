import os

from canvas.map_canvas_refactor import MapCanvasRefactor
from qgis.PyQt.QtCore import pyqtSignal
from qgis._core import QgsVectorLayer, QgsFeature, QgsVectorFileWriter, QgsProject

from field_name import FieldName


class CreateFieldMapCanvas(MapCanvasRefactor):
    feat_geo_signal = pyqtSignal(QgsVectorLayer, str)

    def __init__(self, parent=None):
        super().__init__(parent.layer, parent.frame_43)

        self.smallerPushButtonCanvas.hide()
        self.betweenPushButtonCanvas.hide()
        self.biggerPushButtonCanvas.hide()
        self.addPushButtonCanvasIn.hide()

        self.field_name_widget = FieldName(self)
        self.field_name_widget.on_click_accept.connect(self.create_new_layer)
        #self.field_name_widget.setFixedSize(300, 150)

        self.field_name_widget.hide()

        self.button_list = [
            self.ResetPushButtonCanvasIn,
            self.MaximizePushButtonCanvasIn,
            self.RevertPushButtonCanvasIn,
        ]
        self.change_size_buttons(20)
        self.canvasInterpolate.setLayers([self.R_layer])
        self.check_points()

    def on_ok_PushButtonCanvas_clicked(self):
        self.field_name_widget.setFixedSize(self.size())
        self.field_name_widget.show()

    def create_new_layer(self, name):
        geo = self.points.get_only_points()
        self.dock.setFloating(False)
        vl = QgsVectorLayer("Polygon?crs=epsg:4326", self.layer.id() + 'temporary', "memory")
        pr = vl.dataProvider()
        vl.startEditing()
        fet = QgsFeature()
        fet.setGeometry(geo)
        pr.addFeatures([fet])
        vl.commitChanges()
        self.feat_geo_signal.emit(vl, name)
