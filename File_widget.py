import math
import os
import pathlib

from PyQt5.QtCore import QFileInfo, QPropertyAnimation, QSequentialAnimationGroup, QEasingCurve, QPoint, \
    pyqtSignal, pyqtSlot
from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt import uic
from qgis._core import QgsVectorFileWriter, QgsCoordinateReferenceSystem
from qgis.core import QgsStyle, QgsVectorLayer, QgsLayerTreeLayer, QgsClassificationEqualInterval, \
    QgsRendererRangeLabelFormat, QgsGraduatedSymbolRenderer, QgsFillSymbol, QgsSingleSymbolRenderer, QgsLineSymbol
from qgis.utils import *

from .loading import Loading
from .qgisFuncs import Backup

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/File_widget.ui'), resource_suffix='')


class BackupThread(QThread):
    on_finished = pyqtSignal(object)

    def __init__(self, filename, layer, project, parent=None):
        super(BackupThread, self).__init__()
        self.filename = filename
        self.layer = layer
        self.project = project

    def run(self):
        name = self.filename.split('.')[0]
        full_direct = self.project.absolutePath()
        full_path = os.path.join(full_direct, 'backup' + '/' + name + '_backup')
        os.makedirs(full_path, exist_ok=True)
        output_path = os.path.join(full_path,
                                   name + '_backup' + '.shp')
        writer = QgsVectorFileWriter.writeAsVectorFormat(self.layer,
                                                         output_path,
                                                         "UTF-8",
                                                         driverName="ESRI Shapefile"
                                                         )

        del writer
        self.on_finished.emit(output_path)


class FileWidget(QtWidgets.QWidget, FORM_CLASS):
    closeSignal = pyqtSignal(object)
    optionsSignal = pyqtSignal(object)
    remove_signal = pyqtSignal(object)
    terrain_signal = pyqtSignal(object, bool)

    def __init__(self, item, path, project, iface=None, layer_exist=None, temp=False,
                 parent=None, file_extencion=False):
        super(FileWidget, self).__init__(parent)
        self.layer = None
        self.item = item
        self.setupUi(self)
        self.path = path
        self.value_field = None
        self.filename = "Name"
        self.project = project
        self.iface = iface
        self.exist = layer_exist
        self.layer_id = ''
        self.layer_clone = None
        self.initial_setting = {}
        self.temp = temp
        self.remove_with_signal = True
        self.is_txt = file_extencion
        self.init()

        if not self.temp and not layer_exist:
            self.do_backup()

        if self.temp:
            self.pushButton_up.hide()
            self.pushButton_del.hide()
            self.checkBox.hide()

        ''' passar o iface aqui'''

    def init(self):

        self.loading = Loading(self.pushButtonOptions)
        self.pushButton_up.clicked.connect(self.bring_to_front)
        self.pushButton_del.clicked.connect(self.remove)
        self.checkBox.stateChanged.connect(self.check_state)
        # self.checkBox_terrain.stateChanged.connect(
        # lambda: self.terrain_signal.emit(self.layer, self.checkBox_terrain.isChecked()))
        # self.checkBox_terrain.stateChanged.connect(self.terrain_state)

        # self.pushButtonClose.clicked.connect(self.remove)
        self.pushButtonOptions.clicked.connect(lambda: self.optionsSignal.emit(self))

        self.valueComboBox.currentTextChanged.connect(self.textChanged)
        self.path = self.path.replace('\\', '/')
        filename_with_ext = self.path.split('/')[-1]
        self.filename = filename_with_ext.split('.')[0]

        ext = pathlib.Path(self.path).suffix

        '''Verificar se a layer já existe, caso exista deve utilizar-la, não criar uma nova
        Caso criar uma nova partindo de uma layer existente os valores do comboBox não alteram'''

        # if not self.temp:
        if self.exist is not None:
            self.layer = self.exist
        else:
            self.layer = QgsVectorLayer(os.path.abspath(self.path), self.filename, "ogr")

        self.layer.setCrs(QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId))
        self.layer_id = self.layer.id()

        self.update_fields_list()
        label_width = self.loading.width()
        label_height = self.loading.height()
        wid_width = self.frame_4.width()
        wid_height = self.frame_4.height()
        right_margin = 20

        x = int((wid_width - right_margin) - label_width)
        y = int((wid_height - label_height) / 2)

        self.loading.setGeometry(x, y, label_width, label_height)
        size = self.get_file_size()
        self.labelFileName.setText(self.filename)
        self.labelFileName.setToolTip(self.filename)
        self.labelFileName.setToolTipDuration(2500)
        self.labelExt.setText(ext)
        self.labelFileSize.setText(size)

        self.init_checkBox_state()

    def init_checkBox_state(self) -> None:
        node = self.project.layerTreeRoot().findLayer(self.layer_id)
        if node:
            if node.itemVisibilityChecked():
                self.checkBox.setChecked(True)
            else:
                self.checkBox.setChecked(False)

    @pyqtSlot()
    def check_state(self) -> None:
        node = self.project.layerTreeRoot().findLayer(self.layer_id)

        if node:

            if self.checkBox.isChecked():
                node.setItemVisibilityChecked(True)
            else:
                node.setItemVisibilityChecked(False)

    @pyqtSlot()
    def bring_to_front(self):
        root = self.project.layerTreeRoot()
        root.findLayer(self.layer.id()).setItemVisibilityChecked(True)
        self.checkBox.setChecked(True)
        root.setHasCustomLayerOrder(True)
        order = root.customLayerOrder()
        # print(f'-> bring_to_front (LAYER) {self.layer}')
        print(f'-> bring_to_front {order}')
        order.insert(0, order.pop(order.index(self.layer)))  # vlayer to the top
        print(f'-> bring_to_front (AFTER) {order}')
        root.setCustomLayerOrder(order)

    def update_fields_list(self):

        flds = [f for f in self.layer.fields()]
        names = [f.name() for f in flds]
        self.valueComboBox.clear()
        for name in names:
            self.valueComboBox.addItem(name)

        self.value_field = names[0] if names else None

    def do_backup(self):

        self.loading_file_wid_bac = Loading(self.labelExt)
        self.loading_file_wid_bac.start()
        self.loading_file_wid_bac.show()
        self.backup = Backup(self.layer)
        self.backup.on_new_layer.connect(self.remove_layer)
        self.backup.on_finished.connect(self.loading_file_wid_bac.stop)
        self.backup.on_finished.connect(self.loading_file_wid_bac.hide)
        self.backup.on_finished.connect(self.loading_file_wid_bac.deleteLater)
        self.backup.start()

    @pyqtSlot(str)
    def remove_layer(self, id):
        self.project.removeMapLayer(id)

    def textChanged(self, text):

        if self.temp or text == "":
            return
        self.value_field = text
        ramp_name = 'Spectral'
        num_classes = 5
        default_style = QgsStyle().defaultStyle()
        color_ramp = default_style.colorRamp(ramp_name)
        renderer = self.layer.renderer()

        if isinstance(renderer, QgsGraduatedSymbolRenderer):
            renderer.setClassAttribute(text)

            renderer.updateClasses(self.layer, num_classes)
            renderer.updateColorRamp(color_ramp)

            self.iface.layerTreeView().refreshLayerSymbology(self.layer.id())
            self.layer.triggerRepaint()

    def get_file_size(self):

        info = QFileInfo(self.path)
        size_bytes = info.size()
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB")  # , "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])

    def do_animation(self):
        self.dragAnim = QPropertyAnimation(self, b"pos")
        self.dragAnim.setEasingCurve(QEasingCurve.InOutCubic)
        self.dragAnim.setStartValue(QPoint(self.geometry().x(), self.geometry().y()))
        self.dragAnim.setEndValue(QPoint(self.geometry().x() + 15, self.geometry().y()))
        self.dragAnim.setDuration(200)

        self.dragAnim2 = QPropertyAnimation(self, b"pos")
        self.dragAnim2.setEasingCurve(QEasingCurve.InOutCubic)
        self.dragAnim2.setStartValue(QPoint(self.geometry().x() + 15, self.geometry().y()))
        self.dragAnim2.setEndValue(QPoint(self.geometry().x(), self.geometry().y()))
        self.dragAnim2.setDuration(200)

        self.sequential = QSequentialAnimationGroup()
        self.sequential.addAnimation(self.dragAnim)
        self.sequential.addAnimation(self.dragAnim2)
        self.sequential.start()

    def do_animation_form_loop(self):
        self.dragAnim = QPropertyAnimation(self, b"pos")
        self.dragAnim.setEasingCurve(QEasingCurve.OutCubic)
        self.dragAnim.setStartValue(QPoint(self.geometry().x(), self.geometry().y()))
        self.dragAnim.setEndValue(QPoint(self.geometry().x(), self.geometry().y() + 15))
        self.dragAnim.setDuration(800)

        self.dragAnim2 = QPropertyAnimation(self, b"pos")
        self.dragAnim2.setEasingCurve(QEasingCurve.OutCubic)
        self.dragAnim2.setStartValue(QPoint(self.geometry().x(), self.geometry().y() + 15))
        self.dragAnim2.setEndValue(QPoint(self.geometry().x(), self.geometry().y()))
        self.dragAnim2.setDuration(1000)

        self.sequential = QSequentialAnimationGroup()
        self.sequential.addAnimation(self.dragAnim)
        self.sequential.addAnimation(self.dragAnim2)
        self.sequential.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def remove(self):

        """
        Não excluir aqui, excluir pelo sinal quem vem do QGis implementado no StaraMaps_dialog.py
        self.project.layersRemoved.connect(self.deleteSignalFromQgis)
        """
        self.project.removeMapLayer(self.layer)

    def remove_without_signal(self):
        self.remove_with_signal = False
        self.remove()

    def check_and_create_path(self, root, path):
        if not path:
            return root

        first_no = path[0]
        for child in root.children():
            if child.name() == first_no:
                return self.check_and_create_path(child, path[1:])

        p = root.insertGroup(2, first_no)
        return self.check_and_create_path(p, path[1:])

    def addLayerOnQGis(self, list_groups, layer_type='a'):

        root = self.project.layerTreeRoot()
        last_node = self.check_and_create_path(root, list_groups)

        self.project.addMapLayer(self.layer, False)
        last_node.insertChildNode(0, QgsLayerTreeLayer(self.layer))

        # if not self.is_txt:
        if layer_type == "a":
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
            renderer.setClassAttribute(self.value_field)
            renderer.setClassificationMethod(classification_method)
            renderer.setLabelFormat(format)

            renderer.updateClasses(self.layer, num_classes)
            renderer.updateColorRamp(color_ramp)

            self.layer.setRenderer(renderer)
            self.layer.triggerRepaint()

        elif layer_type == "b":

            fill_symbol = QgsFillSymbol.createSimple({
                'color': '215, 178, 179, 128',  # Cor de preenchimento
                'outline_color': '#eb3700',  # Cor do contorno
                'outline_width': '0,66'  # Largura do contorno
            })

            renderer = QgsSingleSymbolRenderer(fill_symbol)
            self.layer.setRenderer(renderer)

        elif layer_type == "l":
            line_symbol = QgsLineSymbol.createSimple({
                'color': '0, 241, 241, 255',  # Cor azul com 50% de opacidade (RGBA)
                'width': '0,46'  # Largura da linha
            })

            renderer = QgsSingleSymbolRenderer(line_symbol)
            self.layer.setRenderer(renderer)

        canvas = self.iface.mapCanvas()
        extent = self.layer.extent()
        canvas.setExtent(extent)
        canvas.refresh()

    def getLayerByNameInsideGroup(self, group):
        # List all layers in a group
        layer = ""
        for child in group.children():
            if isinstance(child, QgsLayerTreeLayer):
                if child.layer().name() == self.filename:
                    layer = child.layer()
            else:
                layer = self.getLayerByNameInsideGroup(child)

        return layer
