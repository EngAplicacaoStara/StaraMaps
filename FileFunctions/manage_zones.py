import os
import re
import time

from PyQt5.QtCore import QObject, QSize, pyqtSlot
from PyQt5.QtWidgets import QListWidgetItem
from qgis._core import QgsVectorFileWriter

from loading import Loading
from ..qgisFuncs import add_buttons_to_grid, upgrade_grid, ChangeBetweenValues, get_layer_copy, \
    list_groups_linked_to_layer, same_file
from ..range_widget import RangeWidget


class ManageZones(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.index = 0
        self.init()

    def init(self) -> None:
        self.main.pushButton_return_manejo.clicked.connect(lambda: self.deleteLater())
        self.main.addPushButton.clicked.connect(self.on_button_clicked)
        self.main.spinBox.valueChanged.connect(self.update_classes)
        self.main.stackedWidget.setCurrentIndex(8)
        self.main.back_button_hide_signal.emit()

        add_buttons_to_grid(self.main.gridLayout_15, self.main.layer, self.on_click)

    @pyqtSlot()
    def update_classes(self):
        upgrade_grid(self.main.layer, self.main.iface, self.index, self.main.spinBox.value())
        self.update_list()

    @pyqtSlot(int, object)
    def on_click(self, index, obj) -> None:

        self.index = index
        upgrade_grid(self.main.layer, self.main.iface, index)
        self.main.stackedWidget_manage.setCurrentIndex(1)

        self.update_list()

    def update_list(self):
        self.main.listWidget.clear()
        renderer = self.main.layer.renderer()
        ranges = renderer.ranges()

        colors = [lsi.symbol().color() for lsi in renderer.legendSymbolItems()]

        for i in range(len(ranges)):
            item = QListWidgetItem()

            range_widget = RangeWidget(self.main.layer, self.index, i)
            range_widget.on_update.connect(lambda: (
                upgrade_grid(self.main.layer, self.main.iface, self.index)

            ))

            range_widget.set_lowerValue(round(ranges[i].lowerValue(), 2))
            range_widget.set_upperValue(round(ranges[i].upperValue(), 2))
            range_widget.set_color(colors[i].name())

            item.setSizeHint(QSize(200, 30))
            self.main.listWidget.addItem(item)
            self.main.listWidget.setItemWidget(item, range_widget)

    def on_button_clicked(self):

        items = [self.main.listWidget.item(x) for x in range(self.main.listWidget.count())]

        features = self.main.layer.getFeatures()
        new_value = []
        values_1 = []
        values_2 = []
        for i in range(len(items)):
            widget = self.main.listWidget.itemWidget(items[i])
            text = widget.newLineEdit.text()
            if text:
                new_value.append(float(text))
                values_1.append(widget.lower_value)
                values_2.append(widget.upper_value)

        self.loading_manage = Loading(self.main.addPushButton)
        self.loading_manage.start()
        self.loading_manage.show()

        self.change_values = ChangeBetweenValues(features,
                                                 None,
                                                 values_1,
                                                 values_2,
                                                 new_value,
                                                 self.index
                                                 )

        self.change_values.on_finished.connect(lambda list_to_up: (
            self.loading_manage.stop(),
            self.loading_manage.deleteLater(),
            self.create_new_layer(list_to_up),
            upgrade_grid(self.main.layer, self.main.iface, self.index, classes=len(items)),
            self.on_update()
        ))

        self.change_values.start()

    def create_new_layer(self, feat) -> None:
        start_time = time.time()
        print(feat)
        path = re.split("/ //", self.main.layer.dataProvider().dataSourceUri())
        if len(path) == 1:
            path = path[0].split('\\')
        if len(path) == 1:
            path = path[0].split('/')

        path.pop(-1)
        only_path = '\\'.join(path)

        new_layer = get_layer_copy(self.main.layer)
        new_layer.dataProvider().changeAttributeValues(feat)
        new_layer.updateFields()
        new_layer.commitChanges()

        output_path = os.path.join(only_path, f'{self.main.layer.name()}_manageZ' + '.shp')

        output_path = same_file(output_path)
        print(output_path)
        QgsVectorFileWriter.writeAsVectorFormat(new_layer,
                                                output_path,
                                                "UTF-8",
                                                driverName="ESRI Shapefile"
                                                )

        arr = list_groups_linked_to_layer(self.main.project.layerTreeRoot(), self.main.layer)
        tree = arr[::-1][1:]
        self.main.merged_layer_signal.emit(output_path, tree)

        print("--- %s seconds ---" % (time.time() - start_time))

    @pyqtSlot()
    def on_update(self):

        renderer = self.main.layer.renderer()
        ranges = renderer.ranges()

        items = [self.main.listWidget.item(x) for x in range(self.main.listWidget.count())]
        if len(items) == len(ranges):
            for i in range(len(ranges)):
                widget = self.main.listWidget.itemWidget(items[i])
                widget.set_lowerValue(round(ranges[i].lowerValue(), 2))
                widget.set_upperValue(round(ranges[i].upperValue(), 2))
        else:
            print('tamanho diferente')

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0)
        self.main.stackedWidget_manage.setCurrentIndex(0)
        self.main.listWidget.clear()

        self.main.pushButton_return_manejo.disconnect()
        self.main.back_button_show_signal.emit()

        super().deleteLater()
