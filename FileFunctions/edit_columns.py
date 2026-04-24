from qgis.PyQt.QtCore import pyqtSlot, QObject, pyqtSignal, QCoreApplication, QTimer
from qgis.core import edit, Qgis
from qgis.utils import iface

from ..loading import Loading
from ..qgisFuncs import CustomButtonSelectable, upgrade_grid
from ..values_window import ColumnValues


class EditColumns(QObject):

    def tr(self, message):
        return QCoreApplication.translate('EditColumns', message)

    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.selected_list = []
        self.unselected_list = []
        self.init()

    def init(self) -> None:
        for btn, sig in (
            (self.main.pushButton_return_column, 'clicked'),
            (self.main.pushButton_delete, 'clicked'),
            (self.main.pushButton_add, 'clicked'),
        ):
            try:
                getattr(btn, sig).disconnect()
            except (RuntimeError, TypeError):
                pass

        self.main.back_button_hide_signal.emit()
        self.main.stackedWidget.setCurrentIndex(5)
        self.main.pushButton_delete.setDisabled(True)

        for i in range(self.main.gridLayout_16.count()):
            item = self.main.gridLayout_16.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.close()
                    widget.deleteLater()

        self.selected_list = []
        self.unselected_list = []

        flds1 = [f for f in self.main.layer.fields()]
        names1 = [f.name() for f in flds1]
        if names1:
            self.add_buttons_to_layout(names1)

        self.main.pushButton_return_column.clicked.connect(lambda: self.deleteLater())
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
            list_button_index.append(button.index)
            button.close()
            button.deleteLater()

        if not list_button_index:
            return

        page = self.main.stackedWidget.widget(5)
        self._loading = Loading(page)
        self._loading.start()
        self._loading.show()
        # QgsVectorLayer editing is not thread-safe in QGIS. Run on main thread
        # after paint cycle so the loading indicator becomes visible first.
        QTimer.singleShot(0, lambda: self._delete_columns(list_button_index))

    def _delete_columns(self, indices):
        ok = False
        error_msg = ""
        # Ensure deterministic order and avoid duplicated indices.
        indices = sorted(set(indices), reverse=True)
        try:
            # If layer is already in edit mode (pencil enabled), delete through
            # layer edit buffer instead of provider direct call.
            if self.main.layer.isEditable():
                ok = True
                for idx in indices:
                    if not self.main.layer.deleteAttribute(idx):
                        ok = False
                        error_msg = self.tr("Falha ao remover um ou mais campos na sessão de edição atual.")
                        break
            else:
                with edit(self.main.layer):
                    ok = self.main.layer.dataProvider().deleteAttributes(indices)
                    if not ok:
                        error_msg = self.tr("O provedor de dados recusou a exclusão dos campos.")
        except Exception as exc:
            ok = False
            error_msg = str(exc)
        self._on_delete_finished(ok, error_msg)

    def _on_delete_finished(self, ok, error_msg=""):
        self._loading.stop()
        self._loading.deleteLater()

        if not ok:
            iface.messageBar().pushMessage(
                self.tr("Erro"),
                error_msg or self.tr("Não foi possível deletar os campos."),
                level=Qgis.Critical, duration=5
            )
            self.selected_list.clear()
            self.unselected_list.clear()
            return

        self.main.layer.updateFields()

        if self.unselected_list:
            self.add_buttons_to_layout(self.unselected_list, replace=True)

        self.main.pushButton_delete.setDisabled(True)
        field_count = len(self.main.layer.fields())
        if field_count > 0:
            safe_index = min(self.main.file_widget.valueComboBox.currentIndex(), field_count - 1)
            safe_index = max(safe_index, 0)
            upgrade_grid(self.main.layer, self.main.iface, index=safe_index)
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
        for btn, sig in (
            (self.main.pushButton_return_column, 'clicked'),
            (self.main.pushButton_delete, 'clicked'),
            (self.main.pushButton_add, 'clicked'),
        ):
            try:
                getattr(btn, sig).disconnect()
            except (RuntimeError, TypeError):
                pass
        super().deleteLater()
