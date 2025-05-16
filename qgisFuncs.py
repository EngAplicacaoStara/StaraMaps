import os
import subprocess

from PyQt5.QtCore import QThread, pyqtSignal, QSize, pyqtSlot, QPointF, Qt, QObject, QEvent
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QWidget, QHBoxLayout, QLabel, QApplication, QCheckBox, QComboBox
from qgis._core import QgsLayerTree, QgsVectorLayer, QgsStyle, QgsGraduatedSymbolRenderer, QgsVectorFileWriter, \
    QgsProcessingFeedback, QgsWkbTypes, QgsSpatialIndex, \
    QgsGeometry, QgsProject
from qgis._gui import QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker
from qgis.core import NULL, edit

LOG = True


def list_groups_linked_to_layer(layer_tree_root: QgsLayerTree, layer: QgsVectorLayer) -> list:
    """
    Retorna uma lista com todos os grupos ligados a layer (árvore)
    layer_tree_root: QgsLayerTree
    layer: QgsVectorLayer
    """
    tree_layer = layer_tree_root.findLayer(layer.id())

    groups = []
    if tree_layer:

        layer_parent = tree_layer.parent()
        while True:
            groups.append(layer_parent.name() or 'root')
            layer_parent = layer_parent.parent()

            if layer_parent is None:
                break

    return groups


def get_layer_copy(layer: QgsVectorLayer) -> QgsVectorLayer:
    """
    Cria uma cópia da layer:
    layer: QgsVectorLayer

    return: QgsVectorLayer
    """
    feats = [feat for feat in layer.getFeatures()]
    geo_type = layer.geometryType()
    if geo_type == QgsWkbTypes.Point or geo_type == QgsWkbTypes.PointGeometry:
        mem_layer = QgsVectorLayer("Point?crs=epsg:4326", layer.name(), "memory")

    else:
        mem_layer = QgsVectorLayer("Polygon?crs=epsg:4326", layer.name(), "memory")

    # mem_layer = QgsVectorLayer("Polygon?crs=epsg:4326", f"{layer.name()}_duplicated_layer", "memory")

    mem_layer_data = mem_layer.dataProvider()
    attr = layer.dataProvider().fields().toList()
    mem_layer_data.addAttributes(attr)
    mem_layer.updateFields()
    mem_layer_data.addFeatures(feats)

    '''flds = [f for f in mem_layer_data.fields()]
    names = [f.name() for f in flds]

    ramp_name = 'Spectral'
    num_classes = 5
    classification_method = QgsClassificationEqualInterval()

    format = QgsRendererRangeLabelFormat()
    format.setFormat("%1 - %2")
    format.setPrecision(2)
    format.setTrimTrailingZeroes(True)
    default_style = QgsStyle().defaultStyle()

    # default_style.setColorGroup()
    color_ramp = default_style.colorRamp(ramp_name)

    renderer = QgsGraduatedSymbolRenderer()
    renderer.setClassAttribute(names[0])
    renderer.setClassificationMethod(classification_method)
    renderer.setLabelFormat(format)

    renderer.updateClasses(mem_layer, num_classes)
    renderer.updateColorRamp(color_ramp)

    mem_layer.setRenderer(renderer)
    mem_layer.triggerRepaint()'''
    return mem_layer


def print_log(c, m, a=None, msg=None):
    """
    c: Classe: any
    m: Methodo: any
    a: Variácel: any
    msg: Mensagem: any
    """
    if LOG:
        print(
            "CLASS: " + c.__class__.__name__ + " METHOD: " + m.__name__ + f' {a=}' + f'--> {msg}')


def try_delete_object(obj, method):
    try:
        obj.close()
        obj.deleteLater()
    except Exception as e:
        print_log(obj, method, None, e)


def upgrade_grid(layer, iface, index=0, classes=5):
    flds = [f for f in layer.fields()]
    names = [f.name() for f in flds]

    ramp_name = 'Spectral'
    num_classes = classes
    default_style = QgsStyle().defaultStyle()
    color_ramp = default_style.colorRamp(ramp_name)
    renderer = layer.renderer()

    if isinstance(renderer, QgsGraduatedSymbolRenderer):
        renderer.setClassAttribute(names[index])

        renderer.updateClasses(layer, num_classes)
        renderer.updateColorRamp(color_ramp)

        iface.layerTreeView().refreshLayerSymbology(layer.id())
        layer.triggerRepaint()


def add_buttons_to_grid(grid, layer, signal):
    int_types = ["Integer", "Integer64", "Real"]
    flds1 = [field for field in layer.fields()]
    names1 = [f.name() for f in flds1]
    columns = 2
    rows = 99
    i = 0
    list_size = len(names1)
    flag = False
    for row in range(int(rows)):
        if flag: break
        for column in range(columns):
            if flds1[i].typeName() in int_types:
                push_column = CustomButtom(f'{names1[i]}', i)
                push_column.signal_click.connect(signal)
                grid.addWidget(push_column, row + 1, column)
            else:
                push_column = CustomButtom(f'{names1[i]}', i)
                push_column.set_disable()
                grid.addWidget(push_column, row + 1, column)
            i += 1
            if i == list_size:
                flag = True
                break


def get_widget_top_level(obj_name='StaraMapsDialogBase'):
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if widget.objectName() == obj_name:  # isinstance(widget, QMainWindow):
            frame = widget.children()[1]
            return frame


def remove_file(file):
    # directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'backup', f'{layer_name}.shp')

    if os.path.isfile(file):
        os.remove(file)


def same_file(path):
    layers = QgsProject.instance().mapLayers()
    for layer_id, layer in layers.items():
        path_1, arq_1 = os.path.split(path)
        _, arq_2 = os.path.split(layer.dataProvider().dataSourceUri())

        if arq_1 == arq_2:
            newfilename = 'copy_%s' % arq_1
            newpath = os.path.join(path_1, newfilename)
            path = newpath

    return path


def check_add_memorylayer(layer_to_add):
    layers = QgsProject.instance().mapLayers()
    for layer_id, layer in layers.items():
        if layer.dataProvider().name() == 'memory':
            if layer_to_add.name() == layer.name():
                return

    QgsProject.instance().addMapLayer(layer_to_add, False)


def check_remove_memorylayer(layer_to_remove):
    layers = QgsProject.instance().mapLayers()
    for layer_id, layer in layers.items():
        if layer.dataProvider().name() == 'memory':
            if layer_to_remove.id() + 'temporary' == layer.name():
                QgsProject.instance().removeMapLayer(layer_id)
                return


def check_memory_layer_exists(m_layer):
    layers = QgsProject.instance().mapLayers()
    for layer_id, layer in layers.items():
        if layer.dataProvider().name() == 'memory':

            if m_layer.id() + 'temporary' == layer.name():
                return layer

    return None


def remove_memory_layers(layers):
    for layer_to_del in layers:
        check_remove_memorylayer(layer_to_del)


class MyFeedBack(QgsProcessingFeedback):

    def setProgressText(self, text):
        pass
        # print(text)

    def pushInfo(self, info):
        print(info)

    def pushCommandInfo(self, info):
        print(info)

    def pushDebugInfo(self, info):
        print(info)

    def pushConsoleInfo(self, info):
        print(info)

    def reportError(self, error, fatalError=False):
        print(error, fatalError)


class KMLTOSHP(QThread):
    on_finished = pyqtSignal()

    def __init__(self, layer_path):
        super(KMLTOSHP, self).__init__()
        self.layer_path = layer_path

    def run(self) -> None:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        FNULL = open(os.devnull, 'w')
        args = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ExternalFunctions",
                            "ExtFunctions.exe")

        subprocess.call([args, 'convert_kml_to_shp', self.layer_path], stdout=FNULL,
                        stderr=FNULL,
                        startupinfo=si)

        self.on_finished.emit()


class VRCTOSHP(QThread):
    on_finished = pyqtSignal()

    def __init__(self, layer_path, new_out_path):
        super(VRCTOSHP, self).__init__()
        self.layer_path = layer_path
        self.new_out_path = new_out_path

    def run(self):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        FNULL = open(os.devnull, 'w')
        args = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ExternalFunctions",
                            "ExtFunctions.exe")

        subprocess.call([args, 'convert_to_shp', self.layer_path, self.new_out_path], stdout=FNULL,
                        stderr=FNULL,
                        startupinfo=si)

        self.on_finished.emit()


class DatTxtCsvToSHP(QThread):
    on_finished = pyqtSignal()

    def __init__(self, file_name):
        super(DatTxtCsvToSHP, self).__init__()
        self.file_name = file_name

    def run(self) -> None:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        FNULL = open(os.devnull, 'w')
        args = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ExternalFunctions",
                            "ExtFunctions.exe")

        subprocess.call([args, 'convert_points_to_shp', self.file_name], stdout=FNULL,
                        stderr=FNULL,
                        startupinfo=si)

        self.on_finished.emit()


class LOGTOSHP(QThread):
    on_finished = pyqtSignal()

    def __init__(self, layer_path, new_out_path):
        super(LOGTOSHP, self).__init__()
        self.layer_path = layer_path
        self.new_out_path = new_out_path

    def run(self) -> None:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        FNULL = open(os.devnull, 'w')
        args = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ExternalFunctions",
                            "ExtFunctions.exe")

        subprocess.call([args, 'convert_log_to_csv', self.layer_path, self.new_out_path], stdout=FNULL,
                        stderr=FNULL,
                        startupinfo=si)

        self.on_finished.emit()


class Backup(QThread):
    on_finished = pyqtSignal()
    on_new_layer = pyqtSignal(str)

    def __init__(self, layer):
        super(Backup, self).__init__()
        self.layer = layer

    def run(self) -> None:
        layer_copy = get_layer_copy(self.layer)

        layer_name = layer_copy.name().split('.')[0]

        directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'backup', f'{layer_name}.shp')

        if not os.path.isfile(directory):
            geo_type = layer_copy.geometryType()
            if geo_type == QgsWkbTypes.Point or geo_type == QgsWkbTypes.PointGeometry:
                to_save_layer = QgsVectorLayer("Point?crs=epsg:4326", layer_name, "memory")
            else:
                to_save_layer = QgsVectorLayer("Polygon?crs=epsg:4326", layer_name, "memory")

            feats = [feat for feat in layer_copy.getFeatures()]
            to_save_layer_data = to_save_layer.dataProvider()
            attr = layer_copy.dataProvider().fields().toList()
            to_save_layer_data.addAttributes(attr)
            to_save_layer.updateFields()
            to_save_layer_data.addFeatures(feats)

            QgsVectorFileWriter.writeAsVectorFormat(to_save_layer,
                                                    directory,
                                                    "utf-8", driverName="ESRI Shapefile",
                                                    layerOptions=['GEOMETRY=AS_XYZ'])

            self.on_new_layer.emit(to_save_layer.id())




        else:
            print_log(self, self.run)

        self.on_finished.emit()


class ChangeValues(QThread):
    on_finished = pyqtSignal(object)
    on_percent_update = pyqtSignal(float)

    def __init__(self, feautes, geometry, field_index):
        super(ChangeValues, self).__init__()
        self.features = feautes
        self.geo = geometry
        self.field_index = field_index

    def run(self) -> None:
        raise NotImplementedError('Não Implementado.')


class RemoveBiggerValues(ChangeValues):
    def __init__(self, feautes, geometry, value, field_index):
        super(RemoveBiggerValues, self).__init__(feautes, geometry, field_index)
        self.value = value

    def run(self) -> None:

        features = [c for c in self.features]
        feat_count = len(features)
        progress_count = 0

        list_feat_to_update = {}
        if self.geo:
            for feat in features:
                value = feat.attributes()[self.field_index]
                if feat.geometry().within(self.geo):
                    if value > self.value:
                        list_feat_to_update[feat.id()] = {self.field_index: 0}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        else:
            for feat in features:
                value = feat.attributes()[self.field_index]
                if value > self.value:
                    list_feat_to_update[feat.id()] = {self.field_index: 0}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        self.on_finished.emit(list_feat_to_update)


class RemoveSmallerValues(ChangeValues):
    def __init__(self, features, geometry, value, field_index):
        super().__init__(features, geometry, field_index)
        self.value = value

    def run(self) -> None:
        features = [c for c in self.features]
        feat_count = len(features)
        progress_count = 0

        list_feat_to_update = {}
        if self.geo:
            for feat in features:
                value = feat.attributes()[self.field_index]
                if feat.geometry().within(self.geo):
                    if value < self.value:
                        list_feat_to_update[feat.id()] = {self.field_index: 0}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        else:
            for feat in features:
                value = feat.attributes()[self.field_index]
                if value < self.value:
                    list_feat_to_update[feat.id()] = {self.field_index: 0}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        self.on_finished.emit(list_feat_to_update)


class RemoveBetweenValues(ChangeValues):
    def __init__(self, features, geometry, value_1, value_2, field_index):
        super().__init__(features, geometry, field_index)
        self.value_1 = value_1
        self.value_2 = value_2

    def run(self) -> None:
        features = [c for c in self.features]

        feat_count = len(features)
        progress_count = 0

        list_feat_to_update = {}
        if self.geo:
            for feat in features:
                value = feat.attributes()[self.field_index]
                if feat.geometry().within(self.geo):
                    if value > self.value_1 and value < self.value_2:
                        list_feat_to_update[feat.id()] = {self.field_index: 0}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        else:
            for feat in features:
                value = feat.attributes()[self.field_index]
                if value > self.value_1 and value < self.value_2:
                    list_feat_to_update[feat.id()] = {self.field_index: 0}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        self.on_finished.emit(list_feat_to_update)


class ChangeBetweenValues(ChangeValues):
    def __init__(self, features, geometry, value_1, value_2, new_value, field_index):
        super().__init__(features, geometry, field_index)
        self.value_1 = value_1
        self.value_2 = value_2
        self.new_value = new_value

    def run(self) -> None:

        features = [c for c in self.features]

        feat_count = len(features)

        progress_count = 0

        list_feat_to_update = {}

        for i, n_value in enumerate(self.new_value):
            for feat in features:
                value = feat.attributes()[self.field_index]
                if self.value_1[i] <= value <= self.value_2[i]:
                    list_feat_to_update[feat.id()] = {self.field_index: n_value}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        self.on_finished.emit(list_feat_to_update)


class ChangeMapValues(ChangeValues):
    def __init__(self, features, geometry, value, field_index):
        super().__init__(features, geometry, field_index)
        self.value = value

    def run(self) -> None:
        features = [c for c in self.features]

        feat_count = len(features)
        progress_count = 0

        list_feat_to_update = {}
        if self.geo:
            for feat in features:
                if feat.geometry().within(self.geo):
                    # attrs = feat.attributes()
                    # current_value = attrs[self.field_index]
                    list_feat_to_update[feat.id()] = {
                        self.field_index: self.value}  # {self.field_index: current_value + self.value}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        else:
            for feat in features:
                # attrs = feat.attributes()
                # current_value = attrs[self.field_index]
                list_feat_to_update[feat.id()] = {
                    self.field_index: self.value}  # {self.field_index: current_value + self.value}

                value = (progress_count / feat_count) * 100
                self.on_percent_update.emit(float("%.2f" % value))
                progress_count += 1

        self.on_finished.emit(list_feat_to_update)


class ChangeMean(ChangeValues):
    def __init__(self, features, geometry, value, field_index):
        super().__init__(features, geometry, field_index)
        self.value = value

    def run(self) -> None:

        features = [c for c in self.features]
        feat_count = len(features)
        progress_count = 0
        list_feat_to_update = {}
        for feat in features:
            value = feat.attributes()[self.field_index]
            if value == NULL:
                value = 0
            new_value = value + self.value
            list_feat_to_update[feat.id()] = {self.field_index: new_value}
            value = (progress_count / feat_count) * 100
            self.on_percent_update.emit(float("%.2f" % value))
            progress_count += 1

        self.on_finished.emit(list_feat_to_update)


class AddNewColumn(ChangeValues):

    def __init__(self, features, field_index, value):
        super(AddNewColumn, self).__init__(features, None, field_index)
        self.value = value

    def run(self) -> None:
        features = [c for c in self.features]
        feat_count = len(features)
        progress_count = 0
        list_feat_to_update = {}
        for feat in features:
            list_feat_to_update[feat.id()] = {
                self.field_index: self.value}
            value = (progress_count / feat_count) * 100
            self.on_percent_update.emit(float("%.2f" % value))
            # time.sleep(0.001)
            progress_count += 1

        self.on_finished.emit(list_feat_to_update)


class CustomButtom(QPushButton):
    signal_click = pyqtSignal(int, object)

    def __init__(self, text, index, parent=None):
        super(CustomButtom, self).__init__(parent)

        self.setText(text)
        self.setMinimumSize(QSize(100, 50))
        self.setMaximumSize(QSize(100, 50))
        self.index = index
        self.default_style = '''
        QPushButton{
            border:  2px solid rgb(243, 116, 53);	
            color:  rgb(243, 116, 53);
            border-radius: 5px;
            font: 12pt url(:/plugins/StaraMaps/Roboto-Regular.ttf);
        }

        QPushButton::hover{
            background-color: rgb(233, 106, 43);
            color: rgb(250, 250, 250);
        }

        QPushButton::pressed{
            background-color: rgb(223, 96, 33);
            color: rgb(250, 250, 250);
        }
        QPushButton:disabled{
            border: 2px solid rgba(100, 100, 100, 40);
            color: rgb(100, 100, 100, 40);
        }

        '''
        self.setStyleSheet(self.default_style)

        self.clicked.connect(lambda: self.signal_click.emit(self.index, self))

    def set_disable(self):
        self.setDisabled(True)


class CustomColumn(QWidget):
    combobox_enabled_signal = pyqtSignal(int, bool)
    combobox_status_changed_sigal = pyqtSignal(object)

    def __init__(self, index, itens, parent=None):
        super(QWidget, self).__init__(parent)
        self.index = index
        self.itens = itens
        self.init()

    def init(self) -> None:
        layout_w = QHBoxLayout()

        self.combobox = QComboBox()
        self.combobox.setEnabled(False)
        self.combobox.currentIndexChanged.connect(lambda: self.combobox_status_changed_sigal.emit(self))

        self.check = QCheckBox(str(self.index))
        # self.check.stateChanged.connect(self.enabled_combobox)
        self.check.clicked.connect(self.enabled_combobox)
        layout_w.addWidget(self.check)
        layout_w.addWidget(self.combobox)

        self.add_itens_to_combobox()
        self.setLayout(layout_w)

    def reconnect(self) -> None:
        self.combobox.currentIndexChanged.connect(lambda: self.combobox_status_changed_sigal.emit(self))

    def diconn(self) -> None:
        self.combobox.currentIndexChanged.disconnect()

    def add_itens_to_combobox(self) -> None:
        for i in self.itens:
            self.combobox.addItem(i)

        self.combobox.setCurrentIndex(self.index)

    @pyqtSlot()
    def enabled_combobox(self):
        if self.check.isChecked():
            self.combobox.setEnabled(True)
            self.combobox_enabled_signal.emit(self.index, True)
        else:
            self.combobox.setEnabled(False)
            self.combobox_enabled_signal.emit(self.index, False)


class CustomButtonSelectable(CustomButtom):
    on_clicked_signal_replicated = pyqtSignal()

    def __init__(self, text, index, parent=None):
        super(CustomButtonSelectable, self).__init__(text, index, parent)
        self.clicked.connect(self.on_clicked)
        self.flag_selected = False
        self.selected_style = '''
            QPushButton{
                border:  2px solid rgb(243, 116, 53);
                background-color: rgb(243, 116, 53);	
                color:  rgb(255, 255, 255);
                border-radius: 5px;
                font: 12pt url(:/plugins/StaraMaps/Roboto-Regular.ttf);
        }
        '''

    @pyqtSlot()
    def on_clicked(self):
        if self.flag_selected:
            self.setStyleSheet(self.default_style)
        else:
            self.setStyleSheet(self.selected_style)

        self.flag_selected = not self.flag_selected
        self.on_clicked_signal_replicated.emit()


class InfoWithoutIcon:
    def __init__(self, info, parent=None):
        self.info = info

        parent.setToolTipDuration(50000)
        parent.setToolTip(self.info)


class Info(QPushButton):
    def __init__(self, info, parent=None):
        super(Info, self).__init__(parent)
        self.setFixedSize(QSize(12, 12))
        self.info = info
        self.show()

        self.setToolTipDuration(50000)
        self.setToolTip(self.info)


class InfoButton(Info):
    def __init__(self, info, parent=None):
        super(InfoButton, self).__init__(info, parent)
        self.init()
        self.show()

    def init(self) -> None:
        self.parent().enterEvent = self.parent_enter
        self.parent().leaveEvent = self.parent_leave
        self.setObjectName('info_button')
        self.setStyleSheet('''
            QPushButton{
                border: none;
                background-color: transparent; 
                image: url(:/plugins/StaraMaps/ponto-de-interrogacao.png);
          }''')

        width = self.parent().width()
        self.move(width - self.width() - 5, 5)

    def parent_enter(self, event):
        self.setStyleSheet('''
                    QPushButton{
                        border: none;
                        background-color: transparent; 
                        image: url(:/plugins/StaraMaps/ponto-de-interrogacao-gray.png);
                    }''')

    def parent_leave(self, event):
        self.setStyleSheet('''
                            QPushButton{
                                border: none;
                                background-color: transparent; 
                                image: url(:/plugins/StaraMaps/ponto-de-interrogacao.png);
                            }''')


class InfoLineEdit(Info):
    def __init__(self, info, parent=None):
        super(InfoLineEdit, self).__init__(info, parent)
        self.init()
        self.show()

    def init(self) -> None:
        self.setObjectName('info_button')
        self.parent().moveEvent = self.parent_resized
        self.setStyleSheet('''
            QPushButton{
                border: none;
                background-color: transparent; 
                image: url(:/plugins/StaraMaps/ponto-de-interrogacao.png);
          }''')

        width = self.parent().width()
        self.move(width - self.width(), 0)

    def parent_resized(self, event):
        width = self.parent().width()
        self.move(width - self.width(), 0)


class TextInfoTest(QObject):

    def __init__(self):
        super().__init__()

    def tax_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Ajustar Média'),
            self.tr(
                'Função que realiza o ajuste de todos os valores a partir de uma nova média dos valores, isso acrescentará um valor proporcional entre a diferença da média original para adicionada.'),
            self.tr('1° - Selecione a coluna para realizar o ajuste.'),
            self.tr('2º - Adicione o valor da nova média.'),
            self.tr('3º - Clique em Avançar e os valores serão ajustados.')
        )

    def column_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>

            <b>{}</b>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>

            <b>{}</b>
            <ul>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Editar Colunas'),
            self.tr(
                'Essa função permite criar ou excluir colunas de informações, no caso de criar o usuário pode escolher a informação para ser preenchida na nova coluna:'),
            self.tr('Criar coluna'),
            self.tr('1° - Selecione a opção criar.'),
            self.tr('2º - Atribua um nome a nova coluna.'),
            self.tr('3º - Defina um novo valor a coluna.'),
            self.tr('Excluir coluna'),
            self.tr('1° - Selecione a coluna que deseja excluir.'),
            self.tr('2º - Selecione o ícone da lixeira para excluir a coluna selecionada.')
        )

    def interpolate_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
            </p>
        </html>
        """.format(
            self.tr('Interpolar Layer'),
            self.tr('Essa função permite realizar uma interpolação do tipo IDW para uma malha de pontos.'),
            self.tr('1° - Selecione a coluna de dados para interpolação.'),
            self.tr('2º - Defina os valores de coeficiente e tamanho de Pixel (metros).'),
            self.tr(
                '3° - Para delimitar a área da interpolação, podendo ser manual a critério do usuário, caso não realizada será feita de forma automática, '
                'ou pode ser carregada a partir de um arquivo de contorno já criado.'),
            self.tr('4° - Após definidos os critérios basta clicar em Interpolar.'),
            self.tr(
                '5° - Será criada uma nova camada interpolada no mesmo grupo da camada base, com o sufixo [Interpolated].')
        )

    def reset_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
        </html>
        """.format(
            self.tr('Resetar Layer'),
            self.tr(
                'Essa função é usada quando a layer é modificada e por alguma razão seja necessário retornar para o estado original da layer. '
                'Esse estado é salvo em forma de backup assim que a layer é importada para visualização.')
        )

    def manage_zones(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
            </p>
        </html>
        """.format(
            self.tr('Zonas de manejo'),
            self.tr(
                'Esta função permite criar zonas de manejo a partir de uma classificação dos valores presentes na camada, '
                'podendo ser utilizados para criar mapas de aplicação em taxa variável.'),
            self.tr('1° - Selecione a coluna base que servirá de referência.'),
            self.tr('2º - Defina o número de zonas de manejo.'),
            self.tr('3° - Adicione os valores desejados de acordo com a zona de manejo.'),
            self.tr('4° - Após preenchimento clique em OK para criar as zonas de manejo.')
        )

    def export_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Exportar Layer'),
            self.tr('Função responsável por exportar a layer no formato escolhido:'),
            self.tr('1° - Selecione um local para salvar o arquivo.'),
            self.tr('2º - Escolha o formato que deseja salvar.'),
            self.tr('3° - Arquivo é salvo.')
        )

    def rate_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Ajustar Taxas da Layer'),
            self.tr('Função responsável por alterar as taxas da camada em edição.'),
            self.tr('1º - Selecione a coluna em que se deseja alterar os valores.'),
            self.tr(
                '2º - Se preferir delimitar apenas uma área do mapa, a função disponibiliza o recurso de seleção específica, '
                'basta criar um polígono em torno da área, caso isso não seja operado, as alterações serão aplicadas para toda a camada.'),
            self.tr('3º - Escolha a função que deseja aplicar*.'),
            self.tr('4º - Na janela, adicione o valor.'),
            self.tr('5º - Clique em {}').format(self.tr('Avançar')),
            self.tr('6º - A taxa da camada ou da seleção específica será alterada.'),
            self.tr('*Funções disponíveis:'),
            self.tr('Excluir valores MENORES QUE {}').format(self.tr('valor')),
            self.tr('Excluir valores ENTRE {} {}').format(self.tr('valor inferior'), self.tr('valor superior')),
            self.tr('Excluir valores MAIORES QUE {}').format(self.tr('valor')),
            self.tr('Substituir valores em uma área específica {}').format(self.tr('valor'))
        )

    def print_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Imprimir Layer'),
            self.tr('Função responsável por imprimir a layer, é necessário selecionar um local para salvar, também é '
                    'possível selecionar uma imagem se sua preferência para anexar junto ao documento.'),
            self.tr('1º - Selecione um local para salvar o arquivo.'),
            self.tr('2º - Selecione uma imagem, se preferir.(UTM)'),
            self.tr('3º - Clique em imprimir.'),
            self.tr('4º - O pdf será salvo e automaticamente aberto.')
        )

    def join_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Unir Layers'),
            self.tr('Função responsável por unir 2 layers:'),
            self.tr('1º - Selecione um local para salvar a nova layer.'),
            self.tr('2º - Selecione um mapa para unir com a layer atual.(UTM)'),
            self.tr('3º - Selecione as colunas que deseja unir.'),
            self.tr('4º - Clique em {}').format(self.tr('Unir Mapas')),
            self.tr('5º - Uma nova layer será adicionada no grupo da layer atual. {}').format(self.tr('Unir Mapas'))
        )

    def manage_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Unir Layers'),
            self.tr('Função responsável por unir 2 layers:'),
            self.tr('1º - Selecione um local para salvar a nova layer.'),
            self.tr('2º - Selecione um mapa para unir com a layer atual.(UTM)'),
            self.tr('3º - Selecione as colunas que deseja unir.'),
            self.tr('4º - Clique em {}').format(self.tr('Unir Mapas')),
            self.tr('5º - Uma nova layer será adicionada no grupo da layer atual. {}').format(self.tr('Unir Mapas'))
        )

    def general_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Valor Geral'),
            self.tr('Esta função permite somar ou subtrair um valor numérico do mapa de taxa variável.'),
            self.tr('1º - Selecione a coluna que deseja alterar os valores.'),
            self.tr(
                '2º - Se desejar somar um valor basta inseri-lo, caso deseje realizar uma subtração o valor de conter o sinal - seguido do valor.'),
            self.tr('3º - Clique em {} e os valores de todo o mapa serão alterados.').format(self.tr('avançar'))
        )

    def smaller_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Excluir valores menores que'),
            self.tr(
                'Exclui valores menores que o informado, pode ser do mapa completo ou apenas de uma determinada área'),
            self.tr('1º - Selecionar o contorno da área de interesse na aba de seleção (opcional)'),
            self.tr('2º - Clique sobre o ícone da função (<)'),
            self.tr('3º - Informe o valor de corte'),
            self.tr('4º - Clique sobre o ícone (Avançar)')
        )

    def between_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Excluir valores entre o intervalo'),
            self.tr(
                'Exclui valores entre um intervalo informado, pode ser do mapa completo ou apenas de uma determinada área'),
            self.tr('1º - Selecionar o contorno da área de interesse na aba de seleção (opcional)'),
            self.tr('2º - Clique sobre o ícone da função (<->)'),
            self.tr('3º - Informe os valores de corte inferior e superior'),
            self.tr('4º - Clique sobre o ícone (Avançar)')
        )

    def bigger_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Excluir valores maiores que'),
            self.tr(
                'Exclui valores maiores que o informado, pode ser do mapa completo ou apenas de uma determinada área'),
            self.tr('1º - Selecionar o contorno da área de interesse na aba de seleção (opcional)'),
            self.tr('2º - Clique sobre o ícone da função (>)'),
            self.tr('3º - Informe o valor de corte'),
            self.tr('4º - Clique sobre o ícone (Avançar)')
        )

    def reset_points_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
        </html>
        """.format(
            self.tr('Redefinir'),
            self.tr('Redefine todos os pontos da área de seleção')
        )

    def maximize_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
        </html>
        """.format(
            self.tr('Minimizar/Maximizar janela'),
            self.tr('Minimizar/Maximizar janela de seleção')
        )

    def ok_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
        </html>
        """.format(
            self.tr('Confirmar'),
            self.tr('Confirmar área desenhada')
        )

    def revert_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
        </html>
        """.format(
            self.tr('Retornar último ponto'),
            self.tr('Redefine o último ponto criado na área de seleção')
        )

    def add_info(self) -> str:
        return """
        <html>
            <b>{}</b>
            </br>
            <p>{}</p>
            <ul>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
                <li>{}</li>
            </ul>
        </html>
        """.format(
            self.tr('Inserir/substituir valores'),
            self.tr('Insere novos valores aos polígonos, pode ser do mapa completo ou apenas de uma determinada área.'),
            self.tr('1º - Selecionar o contorno da área de interesse na aba de seleção (opcional)'),
            self.tr('2º - Clique sobre o ícone da função (+)'),
            self.tr('3º - Informe o novo valor'),
            self.tr('4º - Clique sobre o ícone (Avançar)')
        )


class CustomVertexMarker(QgsVertexMarker):
    move_signal = pyqtSignal(object)

    def __init__(self, canvas, point, parent):
        super(CustomVertexMarker, self).__init__(canvas)
        self.canvas = canvas
        self.current_point = point
        self.parent = parent
        self.event_filter = CanvasEventFilter(self)
        self.canvas.viewport().installEventFilter(self.event_filter)
        self.setIconType(QgsVertexMarker.ICON_BOX)
        self.click_flag = False
        self.setColor(QColor(0, 255, 0))
        self.setIconSize(5)
        self.setPenWidth(3)
        self.canvas.refresh()
        self.parent.showPoly()
        self.canvas.updateCanvasItemPositions()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.click_flag = True
            self.setColor(QColor(0, 255, 0))
            self.setIconSize(20)
            self.setPenWidth(10)
            self.parent.showPoly()
            self.canvas.updateCanvasItemPositions()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.click_flag = False
            self.setColor(QColor(0, 255, 0))
            self.setIconSize(5)
            self.setPenWidth(3)
            self.canvas.refresh()
            self.parent.showPoly()
            self.canvas.updateCanvasItemPositions()

    def mouseMoveEvent(self, event):
        if self.click_flag:
            point = self.toMapCoordinates(event.pos())
            self.current_point = point
            self.setCenter(point)
            self.parent.showPoly()
            self.canvas.updateCanvasItemPositions()


class CanvasEventFilter(QObject):

    def __init__(self, marker):
        self.marker = marker
        super(CanvasEventFilter, self).__init__()

    def eventFilter(self, obj, event):

        if event.type() == QEvent.MouseButtonPress:
            # forward event if marker is under current mouse position
            if self.marker.isUnderMouse():
                self.marker.mousePressEvent(event)

        elif event.type() == QEvent.MouseButtonRelease:
            if self.marker.isUnderMouse():
                self.marker.mouseReleaseEvent(event)

        elif event.type() == QEvent.MouseMove:
            self.marker.mouseMoveEvent(event)

            # self.marker.exit(event)

        return False


class PolyMapTool(QgsMapToolEmitPoint):
    click_signal = pyqtSignal()

    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.rubberband = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberband.setColor(QColor(255, 0, 0))
        self.rubberband.setFillColor(QColor(210, 153, 90, 125))
        self.rubberband.setWidth(1)
        self.points = []
        self.green_points = []

        # self.deactivated.connect(self.tool_deactivated)

    def canvasPressEvent(self, e):

        self.canvas.updateCanvasItemPositions()

        if e.button() != Qt.LeftButton:
            return

        point = self.toMapCoordinates(e.pos())

        m = CustomVertexMarker(self.canvas, point, self)
        m.setCenter(point)

        self.green_points.append(m)
        self.points.append(m)
        self.isEmittingPoint = True
        self.showPoly()
        self.click_signal.emit()

    def showPoly(self):
        for g_p in self.green_points:
            if not g_p.isVisible():
                g_p.show()
        self.rubberband.reset(QgsWkbTypes.PolygonGeometry)
        for point in self.points[:-1]:
            self.rubberband.addPoint(point.current_point, False)
        if self.points:
            self.rubberband.addPoint(self.points[-1].current_point, True)
        self.rubberband.show()

    def tool_deactivated(self):
        if self.rubberband is not None:
            self.rubberband.reset()

    def reset(self):
        self.rubberband.reset(QgsWkbTypes.PolygonGeometry)
        for g_p in self.green_points:
            self.canvas.scene().removeItem(g_p)
        self.points.clear()
        self.green_points.clear()
        self.rubberband.show()
        self.click_signal.emit()

    def get_points(self):

        self.pt_idx = QgsSpatialIndex(self.canvas.layer(0).getFeatures())
        if self.points:
            points = [point.current_point for point in self.points]

            # geo = QgsGeometry.fromPolygonXY([self.points])
            geo = QgsGeometry.fromPolygonXY([points])
            point_candidates = self.pt_idx.intersects(geo.boundingBox())
            value, geo = self.canvas.layer(0).getFeatures(point_candidates), geo
        else:
            value, geo = self.canvas.layer(0).getFeatures(), None

        self.reset()
        return value, geo

    def get_only_points(self):
        if self.points:
            points = [point.current_point for point in self.points]
            geo = QgsGeometry.fromPolygonXY([points])

        else:
            geo = QgsGeometry.fromPolygonXY([])

        return geo


class CustomDockTitleBar(QWidget):
    def __init__(self, parent):
        super(CustomDockTitleBar, self).__init__()
        self.parent = parent

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel("Layer")
        self.title.setFixedHeight(35)
        self.start = QPointF(0.0, 0.0)
        self.pressing = False

        self.layout.addWidget(self.title)

        self.setLayout(self.layout)

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.end = self.mapToGlobal(event.pos())
            self.movement = self.end - self.start
            self.parent.move(self.mapToGlobal(self.movement).x(), self.mapToGlobal(self.movement).y())
            self.start = self.end

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False


class ResetLayer(QThread):
    finished_signal = pyqtSignal(object, object)
    finished_fail = pyqtSignal()

    def __init__(self, layer, project):
        super().__init__()

        self.tree = list_groups_linked_to_layer(project.layerTreeRoot(), layer)
        self.tree.pop(-1)
        self.tree.reverse()

        self.layer_name = layer.name().split('.')[0]
        self.current_layer_path = layer.dataProvider().dataSourceUri()

        print(self.layer_name)
        print(self.current_layer_path)

        self.layer_backup_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                              'backup', f'{self.layer_name}.shp')
        print(self.layer_backup_path)

    def run(self) -> None:
        if os.path.isfile(self.layer_backup_path):
            backup_layer = QgsVectorLayer(os.path.abspath(self.layer_backup_path), self.layer_name, "ogr")
            new_layer = QgsVectorLayer(os.path.abspath(self.current_layer_path), self.layer_name, "ogr")

            with edit(new_layer):
                flds = [f for f in new_layer.fields()]
                names = [f.name() for f in flds]
                fields_to_temove = []
                for name in names:
                    fieldindex_to_delete = new_layer.fields().indexFromName(name)
                    fields_to_temove.append(fieldindex_to_delete)

                new_layer.dataProvider().deleteAttributes(fields_to_temove)

                for feat in new_layer.getFeatures():
                    new_layer.deleteFeature(feat.id())
            new_layer.updateFields()

            backup_layer_feats = [feat for feat in backup_layer.getFeatures()]

            attr = backup_layer.dataProvider().fields().toList()

            new_layer.dataProvider().addAttributes(attr)
            new_layer.updateFields()
            new_layer.dataProvider().addFeatures(backup_layer_feats)

            self.finished_signal.emit(new_layer, self.tree)
        else:
            print_log(self, self.run, msg='Arquivo não existe!')
            self.finished_fail.emit()
