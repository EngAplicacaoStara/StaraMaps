import os
from pathlib import Path

import processing
from PyQt5.QtCore import QObject, pyqtSlot, QSize, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QListWidgetItem

from loading import Loading
from ..File_widget import FileWidget
from ..qgisFuncs import get_layer_copy, list_groups_linked_to_layer, CustomColumn, print_log, MyFeedBack


class MergeThread(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, res_columns_layer1, res_columns_layer2, out_file):
        super().__init__()
        self.res_columns_layer1 = res_columns_layer1
        self.res_columns_layer2 = res_columns_layer2
        self.out_file = out_file
        self.feed = MyFeedBack()

    def run(self) -> None:
        try:
            params = {'LAYERS': [self.res_columns_layer1, self.res_columns_layer2],
                      'CRS': 'EPSG:4326',
                      'OUTPUT': self.out_file}

            processing.run('qgis:mergevectorlayers', params, feedback=self.feed)
        except Exception as e:
            print(e)

        self.finished_signal.emit()


class Merge(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main

        self.layer_to_uni = None
        self.init()

    def init(self) -> None:
        self.main.pushButton_return.clicked.connect(lambda: self.deleteLater())

        self.main.back_button_hide_signal.emit()
        self.main.stackedWidget.setCurrentIndex(1)
        home = str(Path.home())
        self.main.currentPath_join.setText(home)

        for item in self.main.itens:
            # print()
            if item.filename != self.main.file_widget.filename and \
                    item.layer.geometryType() == self.main.layer.geometryType():
                item_widget = QListWidgetItem()
                file = FileWidget(
                    item=item_widget,
                    path=item.layer.dataProvider().dataSourceUri(),
                    project=item.project,
                    iface=item.iface,
                    layer_exist=item.layer,
                    temp=True
                )
                file.valueComboBox.hide()
                file.frame_4.hide()
                item_widget.setSizeHint(QSize(100, 80))
                self.main.listWidget_chose.addItem(item_widget)
                self.main.listWidget_chose.setItemWidget(item_widget, file)

        self.main.findPath_join.clicked.connect(self.open_path)
        self.main.join_button.clicked.connect(self.merge_maps)
        self.main.listWidget_chose.itemClicked[QListWidgetItem].connect(self.on_item_click)

    def merge_maps(self) -> None:
        itens_layer1 = [
            self.main.listWidget_layer1_flds.itemWidget(self.main.listWidget_layer1_flds.item(x)).combobox.currentText()
            for x in range(self.main.listWidget_layer1_flds.count()) if
            self.main.listWidget_layer1_flds.itemWidget(
                self.main.listWidget_layer1_flds.item(x)).combobox.isEnabled()]
        itens_layer2 = [
            self.main.listWidget_layer2_flds.itemWidget(self.main.listWidget_layer2_flds.item(x)).combobox.currentText()
            for x in range(self.main.listWidget_layer2_flds.count()) if
            self.main.listWidget_layer2_flds.itemWidget(
                self.main.listWidget_layer2_flds.item(x)).combobox.isEnabled()]

        layer_copy_1 = get_layer_copy(self.main.layer)
        layer_copy_2 = get_layer_copy(self.layer_to_uni)

        res_columns_layer1 = self.delete_columns(layer_copy_1, itens=itens_layer1)
        res_columns_layer2 = self.delete_columns(layer_copy_2, itens=itens_layer2)

        directory = '[' + self.main.layer_name + ']' + '[' + self.layer_to_uni.name() + ']' + "_merged"
        parent_dir = self.main.layer.dataProvider().dataSourceUri().split('/')
        new_dir = '/'.join(parent_dir[:-1])

        path = os.path.join(new_dir, directory)
        new_path = os.path.join(self.main.currentPath_join.text(), path)

        if not os.path.exists(new_path):
            os.mkdir(new_path)

        out_file = new_path + f"/{directory}.shp"

        self.loading = Loading(self.main.join_button)
        self.loading.start()
        self.loading.show()

        self.merge_thread = MergeThread(res_columns_layer1, res_columns_layer2, out_file)
        self.merge_thread.finished_signal.connect(lambda: self.on_merge_finished(out_file))
        self.merge_thread.start()

    def on_merge_finished(self, out_file):
        self.loading.stop(),
        self.loading.deleteLater()
        arr = list_groups_linked_to_layer(self.main.project.layerTreeRoot(), self.main.layer)
        tree = arr[::-1][1:]
        self.main.merged_layer_signal.emit(out_file, tree)
        self.deleteLater()
        self.main.back_animation_signal.emit()

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0),
        self.main.stackedWidget_column.setCurrentIndex(0),
        self.main.back_button_show_signal.emit(),
        self.main.listWidget_chose.clear(),
        self.main.listWidget_layer1_flds.clear(),
        self.main.listWidget_layer2_flds.clear(),
        self.main.label_title.setText(self.tr("Escolha um mapa para unir"))
        self.main.pushButton_return.clicked.disconnect()
        self.main.findPath_join.clicked.disconnect()
        self.main.listWidget_chose.disconnect()
        self.main.join_button.disconnect()
        super().deleteLater()

    def open_path(self):
        home = str(Path.home())
        dire = QFileDialog.getExistingDirectory(self.main, self.tr("Salvar"), home,
                                                QFileDialog.ShowDirsOnly |
                                                QFileDialog.DontResolveSymlinks)

        self.main.currentPath_join.setText(dire)

    def delete_columns(self, layer, itens):
        dropfields = [field.name() for field in
                      layer.fields() if
                      field.name() not in itens]  # iterate over the layer's fields and store the fieldnames in a list

        if not dropfields:
            return layer

        alg_params = {
            'COLUMN': dropfields,
            'INPUT': layer,
            'OUTPUT': 'memory:{}'.format(layer.name())
        }
        temp = processing.run('qgis:deletecolumn', alg_params)
        return temp['OUTPUT']

    @pyqtSlot(QListWidgetItem)
    def on_item_click(self, item):
        widget = self.main.listWidget_chose.itemWidget(item)
        self.main.stackedWidget_column.setCurrentIndex(1)
        self.main.label_title.setText(self.tr("Selecione a(s) coluna(s) que deseja unir"))

        self.layer_to_uni = widget.layer

        flds1 = [f for f in self.main.layer.fields()]
        names1 = [f.name() for f in flds1]

        flds2 = [f for f in widget.layer.fields()]
        names2 = [f.name() for f in flds2]

        self.main.label_layer1.setText(self.main.layer_name + self.tr(" (ATUAL)"))
        self.main.label_layer2.setText(self.layer_to_uni.name())

        for i in range(len(names1)):
            iteml = QListWidgetItem(self.main.listWidget_layer1_flds)
            custom_c = CustomColumn(i, names1)
            custom_c.combobox_enabled_signal.connect(self.on_combobox_enabled)
            custom_c.combobox_status_changed_sigal.connect(self.on_combobox_status_changed)
            iteml.setSizeHint(QSize(100, 40))
            self.main.listWidget_layer1_flds.addItem(iteml)
            self.main.listWidget_layer1_flds.setItemWidget(iteml, custom_c)

        for i in range(len(names2)):
            iteml = QListWidgetItem(self.main.listWidget_layer2_flds)
            custom_c = CustomColumn(i, names2)
            custom_c.combobox_enabled_signal.connect(self.on_combobox_enabled)
            custom_c.combobox_status_changed_sigal.connect(self.on_combobox_status_changed)
            iteml.setSizeHint(QSize(100, 40))
            self.main.listWidget_layer2_flds.addItem(iteml)
            self.main.listWidget_layer2_flds.setItemWidget(iteml, custom_c)

    @pyqtSlot(object)
    def on_combobox_status_changed(self, custom_column):
        all_list_itens = []
        parent_list = None
        id_1 = id(custom_column.parent().parent())
        id_2 = id(self.main.listWidget_layer1_flds)

        if id_1 == id_2:
            all_list_itens = [self.main.listWidget_layer1_flds.item(x) for x in
                              range(self.main.listWidget_layer1_flds.count())]
            parent_list = self.main.listWidget_layer1_flds
        else:
            all_list_itens = [self.main.listWidget_layer2_flds.item(x) for x in
                              range(self.main.listWidget_layer2_flds.count())]
            parent_list = self.main.listWidget_layer2_flds

        if parent_list == None:
            print_log(self, self.on_combobox_status_changed, parent_list)
            return

        last_c = []
        for item in all_list_itens:
            widget = parent_list.itemWidget(item)
            widget.diconn()

            id_c_1 = id(widget.combobox)
            id_c_2 = id(custom_column.combobox)
            if id_c_1 != id_c_2:
                all_combo = [widget.combobox.itemText(i) for i in range(widget.combobox.count())]

                for text in all_combo:
                    if text != custom_column.combobox.currentText() and text not in last_c:
                        index = widget.combobox.findText(text, Qt.MatchFixedString)

                        widget.combobox.setCurrentIndex(index)
                        break

            last_c.append(widget.combobox.currentText())
            widget.reconnect()

    @pyqtSlot(int, bool)
    def on_combobox_enabled(self, index, status):
        items_list1 = [self.main.listWidget_layer1_flds.item(x) for x in
                       range(self.main.listWidget_layer1_flds.count())]
        items_widgets1 = [self.main.listWidget_layer1_flds.itemWidget(item) for item in items_list1]
        items_list2 = [self.main.listWidget_layer2_flds.item(x) for x in
                       range(self.main.listWidget_layer2_flds.count())]
        items_widgets2 = [self.main.listWidget_layer2_flds.itemWidget(item) for item in items_list2]
        all_items = items_widgets1 + items_widgets2
        accepts = 0
        for item in all_items:
            if item.index == index:
                accepts += 1
                item.combobox.setEnabled(status)
                item.check.setChecked(status)
                if accepts == 2:
                    break
