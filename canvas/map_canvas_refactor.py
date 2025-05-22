import sys
import os

import requests
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QDockWidget
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtCore import Qt, pyqtSlot, pyqtSignal, QSize
from qgis._gui import QgsMapCanvas
from qgis._core import QgsRasterLayer, QgsCoordinateReferenceSystem

from qgisFuncs import PolyMapTool

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../ui/MapCanvas.ui'), resource_suffix='')


class MapCanvasRefactor(QWidget, FORM_CLASS):
    button_resize_signal = pyqtSignal(int)


    def __init__(self, layer, parent=None):
        super(MapCanvasRefactor, self).__init__(parent)
        self.setupUi(self)

        self.layer = layer
        self.smallerPushButtonCanvas.setCursor(QCursor(Qt.PointingHandCursor))
        self.betweenPushButtonCanvas.setCursor(QCursor(Qt.PointingHandCursor))
        self.biggerPushButtonCanvas.setCursor(QCursor(Qt.PointingHandCursor))
        self.ResetPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.MaximizePushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.OkPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.RevertPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))
        self.addPushButtonCanvasIn.setCursor(QCursor(Qt.PointingHandCursor))

        self.ResetPushButtonCanvasIn.clicked.connect(self.on_reset_PushButtonCanvas_clicked)
        self.MaximizePushButtonCanvasIn.clicked.connect(self.on_maximize_PushButtonCanvas_clicked)
        self.OkPushButtonCanvasIn.clicked.connect(self.on_ok_PushButtonCanvas_clicked)
        self.RevertPushButtonCanvasIn.clicked.connect(self.on_revert_PushButtonCanvas_clicked)

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

        # self.canvasInterpolate.setLayers([self.layer, self.R_layer])
        # self.canvasInterpolate.setDestinationCrs(self.layer.crs())
        self.canvasInterpolate.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))

        # Centraliza o mapa no ponto
        # self.canvasInterpolate.setCenter(ponto_wgs84)
        self.canvasInterpolate.setExtent(self.layer.extent())

        self.points = PolyMapTool(self.canvasInterpolate)
        self.points.click_signal.connect(self.check_points)
        self.canvasInterpolate.setMapTool(self.points)

        self.setLayout(self.layout_canvas)

        self.button_list = [
            self.smallerPushButtonCanvas,
            self.betweenPushButtonCanvas,
            self.biggerPushButtonCanvas,
            self.ResetPushButtonCanvasIn,
            self.MaximizePushButtonCanvasIn,
            self.OkPushButtonCanvasIn,
            self.RevertPushButtonCanvasIn,
            self.addPushButtonCanvasIn
        ]

        self.button_resize_signal.connect(self.change_size_buttons)

    @pyqtSlot()
    def check_points(self) -> None:
        if len(self.points.green_points) != 0:
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

    @pyqtSlot()
    def on_reset_PushButtonCanvas_clicked(self):
        self.points.reset()

    @pyqtSlot()
    def on_maximize_PushButtonCanvas_clicked(self):
        self.__check_dock()

    def force_close_dock(self):
        self.dock.setFloating(False)

    @pyqtSlot()
    def on_ok_PushButtonCanvas_clicked(self):
        raise NotImplementedError('not implemented')

    @pyqtSlot()
    def on_revert_PushButtonCanvas_clicked(self):
        if self.points.points:
            self.points.points.pop(-1)
            g_p = self.points.green_points.pop(-1)
            self.canvasInterpolate.scene().removeItem(g_p)
            self.points.showPoly()
            self.check_points()

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

    @pyqtSlot(int)
    def change_size_buttons(self, value) -> None:

        for button in self.button_list:
            new_wid = value
            new_hei = value

            button.resize(QSize(new_wid, new_hei))

        self.frame_30.setFixedHeight(len(self.button_list) * (value + 10))
        self.frame_30.setFixedWidth(value)

    def __check_dock(self):
        if self.dock.isFloating():
            self.dock.setFloating(False)
        else:
            self.dock.setFloating(True)
