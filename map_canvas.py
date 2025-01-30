import os
import sys

import requests
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QSize
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QDockWidget
from qgis.PyQt import uic
from qgis._core import QgsRasterLayer, QgsVectorLayer, QgsFeature
from qgis._gui import QgsMapCanvas

from .qgisFuncs import PolyMapTool, InfoWithoutIcon, TextInfoTest

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/MapCanvas.ui'), resource_suffix='')


class MapCanvas(QWidget, FORM_CLASS):
    feat_geo_signal = pyqtSignal(QgsVectorLayer)
    smaller_signal = pyqtSignal()
    between_signal = pyqtSignal()
    bigger_signal = pyqtSignal()
    add_signal = pyqtSignal()

    button_resize_signal = pyqtSignal(int)

    def __init__(self, layer, parent=None):
        super(MapCanvas, self).__init__(parent)
        self.setupUi(self)

        self.smallerPushButtonCanvas.setCursor(QCursor(Qt.PointingHandCursor))
        self.betweenPushButtonCanvas.setCursor(QCursor(Qt.PointingHandCursor))
        self.biggerPushButtonCanvas.setCursor(QCursor(Qt.PointingHandCursor))
        self.ResetPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.MaximizePushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.OkPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.RevertPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.addPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))

        self.messages = TextInfoTest()

        InfoWithoutIcon(self.messages.smaller_info(), self.smallerPushButtonCanvas)
        InfoWithoutIcon(self.messages.between_info(), self.betweenPushButtonCanvas)
        InfoWithoutIcon(self.messages.bigger_info(), self.biggerPushButtonCanvas)
        InfoWithoutIcon(self.messages.reset_points_info(), self.ResetPushButtonCanvasIn)
        InfoWithoutIcon(self.messages.maximize_info(), self.MaximizePushButtonCanvasIn)
        InfoWithoutIcon(self.messages.ok_info(), self.OkPushButtonCanvasIn)
        InfoWithoutIcon(self.messages.revert_info(), self.RevertPushButtonCanvasIn)
        InfoWithoutIcon(self.messages.add_info(), self.addPushButtonCanvasIn)

        self.RevertPushButtonCanvasIn.setEnabled(False)
        self.ResetPushButtonCanvasIn.setEnabled(False)
        self.OkPushButtonCanvasIn.setEnabled(False)

        self.ResetPushButtonCanvasIn.clicked.connect(self.on_ResetPushButtonCanvas_clicked)
        self.MaximizePushButtonCanvasIn.clicked.connect(self.on_MaximizePushButtonCanvas_clicked)
        self.OkPushButtonCanvasIn.clicked.connect(self.on_OkPushButtonCanvas_clicked)
        self.RevertPushButtonCanvasIn.clicked.connect(self.on_RevertPushButtonCanvas_clicked)

        self.smallerPushButtonCanvas.clicked.connect(lambda: (
            self.smaller_signal.emit(),
            self.dock.setFloating(False),
            self.hide()

        ))
        self.betweenPushButtonCanvas.clicked.connect(lambda: (
            self.between_signal.emit(),
            self.dock.setFloating(False),
            self.hide()
        ))
        self.biggerPushButtonCanvas.clicked.connect(lambda: (
            self.bigger_signal.emit(),
            self.dock.setFloating(False),
            self.hide()
        ))

        self.addPushButtonCanvasIn.clicked.connect(lambda: (
            self.add_signal.emit(),
            self.dock.setFloating(False),
            self.hide()

        ))

        self.layer = layer

        self.layout_canvas = QHBoxLayout()

        self.canvasInterpolate = QgsMapCanvas()

        service_uri = "type=xyz&zmin=0&zmax=20&url=https://" + requests.utils.quote(
            "mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}")
        self.R_layer = QgsRasterLayer(service_uri, 'OSM', 'wms')

        self.dock = QDockWidget()
        self.dock.topLevelChanged.connect(self.__check_dock_without_change)
        self.dock.setWindowTitle('Layer')
        self.dock.setFeatures(QDockWidget.DockWidgetFloatable |
                              QDockWidget.DockWidgetMovable)
        self.dock.setWidget(self.canvasInterpolate)
        self.layout_canvas.addWidget(self.dock)
        self.layout_canvas.setContentsMargins(0, 0, 0, 0)

        self.frame_30.setParent(self.canvasInterpolate)
        self.frame_30.show()

        self.canvasInterpolate.setLayers([self.layer, self.R_layer])
        self.canvasInterpolate.setDestinationCrs(self.layer.crs())

        self.points = PolyMapTool(self.canvasInterpolate)
        self.points.click_signal.connect(self.check_points)
        self.canvasInterpolate.setMapTool(self.points)

        self.canvasInterpolate.setExtent(self.layer.extent())
        self.canvasInterpolate.refreshAllLayers()

        self.setLayout(self.layout_canvas)

    @pyqtSlot(bool)
    def check_points(self, value) -> None:
        if value:
            self.RevertPushButtonCanvasIn.setEnabled(True)
            self.ResetPushButtonCanvasIn.setEnabled(True)
            self.OkPushButtonCanvasIn.setEnabled(True)
        else:
            self.RevertPushButtonCanvasIn.setEnabled(False)
            self.ResetPushButtonCanvasIn.setEnabled(False)
            self.OkPushButtonCanvasIn.setEnabled(False)

    @pyqtSlot()
    def __check_dock_without_change(self) -> None:
        if self.dock.isFloating():
            self.MaximizePushButtonCanvasIn.setStyleSheet('''
                                           QPushButton{
                                               background-color: rgb(243, 116, 53);
                                               border: none;	
                                               color: rgb(250, 250, 250);
                                               border-radius: 5px;
                                               font: 12pt url(:/plugins/StaraMaps/Roboto-Regular.ttf);
                                               image: url(:/plugins/StaraMaps/minimizar.png);
                                               padding-left: 2px;
                                               padding-right: 2px;
                                               padding-top: 2px; 
                                               padding-bottom: 2px;
                                           }

                                           QPushButton::hover{
                                               background-color: rgb(233, 106, 43);
                                           }

                                           QPushButton::pressed{
                                               background-color: rgb(223, 96, 33);
                                           }
                                       ''')
            self.button_resize_signal.emit(40)
            self.dock.showMaximized()


        else:
            self.MaximizePushButtonCanvasIn.setStyleSheet('''
                                                           QPushButton{
                                                               background-color: rgb(243, 116, 53);
                                                               border: none;	
                                                               color: rgb(250, 250, 250);
                                                               border-radius: 5px;
                                                               font: 12pt url(:/plugins/StaraMaps/Roboto-Regular.ttf);
                                                               image: url(:/plugins/StaraMaps/maximizar.png);
                                                               padding-left: 2px;
                                                               padding-right: 2px;
                                                               padding-top: 2px; 
                                                               padding-bottom: 2px;
                                                           }

                                                           QPushButton::hover{
                                                               background-color: rgb(233, 106, 43);
                                                           }

                                                           QPushButton::pressed{
                                                               background-color: rgb(223, 96, 33);
                                                           }
                                                       ''')
            self.button_resize_signal.emit(20)

    def __check_dock(self):
        if self.dock.isFloating():
            self.dock.setFloating(False)
        else:
            self.dock.setFloating(True)

    @pyqtSlot()
    def on_ResetPushButtonCanvas_clicked(self):
        self.points.reset()

    @pyqtSlot()
    def on_MaximizePushButtonCanvas_clicked(self):
        self.__check_dock()

    @pyqtSlot()
    def on_OkPushButtonCanvas_clicked(self):
        _, geo = self.points.get_points()
        self.dock.setFloating(False)
        vl = QgsVectorLayer("Polygon?crs=epsg:4326", self.layer.id() + 'temporary', "memory")
        pr = vl.dataProvider()
        vl.startEditing()
        fet = QgsFeature()
        fet.setGeometry(geo)
        pr.addFeatures([fet])
        vl.commitChanges()
        self.feat_geo_signal.emit(vl)

    @pyqtSlot()
    def on_RevertPushButtonCanvas_clicked(self):
        if self.points.points:
            self.points.points.pop(-1)
            g_p = self.points.green_points.pop(-1)
            self.canvasInterpolate.scene().removeItem(g_p)
            self.points.showPoly()
            self.points.click_signal.emit(len(self.points.green_points) != 0)


class InterpolateMapCanvas(MapCanvas):
    def __init__(self, layer, parent=None):
        super().__init__(layer, parent)

        self.smallerPushButtonCanvas.hide()
        self.betweenPushButtonCanvas.hide()
        self.biggerPushButtonCanvas.hide()
        self.addPushButtonCanvasIn.hide()

        self.frame_30.setFixedHeight(4 * (20 + 5))
        self.button_resize_signal.connect(self.change_size_buttons)

    @pyqtSlot(int)
    def change_size_buttons(self, value) -> None:
        button_list = [
            self.ResetPushButtonCanvasIn,
            self.MaximizePushButtonCanvasIn,
            self.OkPushButtonCanvasIn,
            self.RevertPushButtonCanvasIn
        ]

        for button in button_list:
            new_wid = value
            new_hei = value

            button.resize(QSize(new_wid, new_hei))

        self.frame_30.setFixedHeight(len(button_list) * (value + 5))
        self.frame_30.setFixedWidth(value)


class RateMapCanvas(MapCanvas):
    def __init__(self, layer, parent=None):
        super().__init__(layer, parent)

        self.canvasInterpolate.setLayers([self.layer])
        self.canvasInterpolate.setDestinationCrs(self.layer.crs())
        self.canvasInterpolate.setExtent(self.layer.extent())
        self.canvasInterpolate.refreshAllLayers()

        self.OkPushButtonCanvasIn.hide()

        self.frame_30.setFixedHeight(7 * (20 + 5))

        self.button_resize_signal.connect(self.change_size_buttons)

    @pyqtSlot(int)
    def change_size_buttons(self, value) -> None:
        button_list = [
            self.smallerPushButtonCanvas,
            self.betweenPushButtonCanvas,
            self.biggerPushButtonCanvas,
            self.ResetPushButtonCanvasIn,
            self.MaximizePushButtonCanvasIn,
            self.RevertPushButtonCanvasIn,
            self.addPushButtonCanvasIn
        ]

        for button in button_list:
            new_wid = value
            new_hei = value

            button.resize(QSize(new_wid, new_hei))

        self.frame_30.setFixedHeight(len(button_list) * (value + 5))
        self.frame_30.setFixedWidth(value)
