from PyQt5.QtCore import pyqtSlot, QObject
from qgis.core import edit

from ..qgisFuncs import CustomButtonSelectable, upgrade_grid
from ..values_window import ColumnValues


class EditColumns(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.selected_list = []
        self.unselected_list = []
        self.init()

    def init(self) -> None:
        self.main.pushButton_return_column.clicked.connect(lambda: self.deleteLater())

        self.main.back_button_hide_signal.emit()
        self.main.stackedWidget.setCurrentIndex(5)
        self.main.pushButton_delete.setDisabled(True)
        widgets = (self.main.gridLayout_16.itemAt(i).widget() for i in range(self.main.gridLayout_16.count()))
        for widget in widgets:
            widget.close()
            widget.deleteLater()
        self.selected_list = []
        self.unselected_list = []

        flds1 = [f for f in self.main.layer.fields()]
        names1 = [f.name() for f in flds1]
        if names1:
            self.add_buttons_to_layout(names1)

        self.main.pushButton_delete.clicked.connect(self.on_delete_click)
        self.main.pushButton_add.clicked.connect(self.on_add_click)

    def add_buttons_to_layout(self, l, replace=False):
        columns = 2
        rows = 99
        i = 0
        list_size = len(l)
        flag = False
        for row in range(int(rows)):
            if flag: break
            for column in range(columns):
                if replace:
                    push_column = CustomButtonSelectable(l[i].text(), i)
                    l[i].close()
                    l[i].deleteLater()
                else:
                    push_column = CustomButtonSelectable(f'{l[i]}', i)
                push_column.on_clicked_signal_replicated.connect(self.on_click)
                self.main.gridLayout_16.addWidget(push_column, row + 1, column)
                i += 1
                if i == list_size:
                    flag = True
                    break
        if replace:
            l.clear()

    @pyqtSlot()
    def on_click(self):
        self.selected_list.clear()
        self.unselected_list.clear()
        widgets = (self.main.gridLayout_16.itemAt(i).widget() for i in range(self.main.gridLayout_16.count()))
        for widget in widgets:
            if isinstance(widget, CustomButtonSelectable):
                if widget.flag_selected:
                    self.selected_list.append(widget)
                else:
                    self.unselected_list.append(widget)

        if self.selected_list:
            self.main.pushButton_delete.setDisabled(False)
        else:
            self.main.pushButton_delete.setDisabled(True)

    @pyqtSlot()
    def on_delete_click(self):
        list_button_index = []
        for button in self.selected_list:
            index = button.index
            list_button_index.append(index)
            button.close()
            button.deleteLater()

        if list_button_index:
            with edit(self.main.layer):
                self.main.layer.dataProvider().deleteAttributes(list_button_index)
            self.main.layer.updateFields()
            list_button_index.clear()
        self.main.pushButton_delete.setDisabled(True)

        if self.unselected_list:
            self.add_buttons_to_layout(self.unselected_list, replace=True)

        upgrade_grid(self.main.layer, self.main.iface)
        '''Atualizar a lista de campos dos widgets'''
        # https://gis.stackexchange.com/questions/109078/deleting-column-field-in-pyqgis
        for item in self.main.itens:
            if item.filename == self.main.file_widget.filename:
                self.main.file_widget.update_fields_list()
                self.main.file_widget.update()
                item.update_fields_list()
                item.update()
        self.selected_list.clear()
        self.unselected_list.clear()

    @pyqtSlot()
    def on_add_click(self):
        v_window = ColumnValues(self.main.layer, self.main.pushButton_return_column, self.main.frame_61)
        v_window.update_features_signal.connect(self.main.on_layer_update_feat)
        v_window.finish_signal.connect(lambda: (
            self.main.back_button_show_signal.emit(),
            self.main.stackedWidget.setCurrentIndex(0),
            self.deleteLater()
        ))
        v_window.close_signal.connect(lambda: (
            v_window.deleteLater()
        ))
        v_window.show()

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0)
        self.main.back_button_show_signal.emit()
        self.main.pushButton_return_column.disconnect()
        super().deleteLater()
