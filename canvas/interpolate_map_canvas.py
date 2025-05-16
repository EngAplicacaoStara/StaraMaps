from canvas.map_canvas import MapCanvas
from qgis.PyQt.QtCore import pyqtSlot, QSize


class InterpolateMapCanvas(MapCanvas):
    def __init__(self, layer, parent=None):
        super().__init__(layer, parent)

        self.smallerPushButtonCanvas.hide()
        self.betweenPushButtonCanvas.hide()
        self.biggerPushButtonCanvas.hide()
        self.addPushButtonCanvasIn.hide()

        self.button_list = [
            self.ResetPushButtonCanvasIn,
            self.MaximizePushButtonCanvasIn,
            self.OkPushButtonCanvasIn,
            self.RevertPushButtonCanvasIn
        ]

        self.frame_30.setFixedHeight(len(self.button_list) * (20 + 5))
        self.button_resize_signal.connect(self.change_size_buttons)

    @pyqtSlot(int)
    def change_size_buttons(self, value) -> None:
        for button in self.button_list:
            new_wid = value
            new_hei = value

            button.resize(QSize(new_wid, new_hei))

        self.frame_30.setFixedHeight(len(self.button_list) * (value + 5))
        self.frame_30.setFixedWidth(value)
