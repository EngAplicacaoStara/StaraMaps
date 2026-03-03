import csv
import os
import subprocess
import sys
import time
from pathlib import Path

import utm
from PIL import Image
from qgis.PyQt.QtCore import pyqtSlot, QThread, pyqtSignal, QVariant, Qt, QPointF, QSize, QTimer, QCoreApplication
from qgis.PyQt.QtGui import QFont, QPolygonF, QColor, QPaintEvent, QPainter, QPen, QIcon
from qgis.PyQt.QtWidgets import QFileDialog, QPushButton
from qgis.PyQt import QtWidgets
from qgis.PyQt import uic
from qgis._core import Qgis, QgsLayerTreeGroup, QgsField, QgsVectorFileWriter, QgsVectorLayer, QgsPrintLayout, \
    QgsLayoutItemMap, \
    QgsLayoutPoint, QgsUnitTypes, QgsLayoutSize, QgsLayoutItemLabel, \
    QgsLayoutItemPolygon, QgsFillSymbol, QgsLayoutItemPage, QgsMapSettings, QgsRectangle, QgsLayoutItemPicture, \
    QgsLayoutExporter, QgsLayoutItemMapGrid, QgsLayoutItemScaleBar, QgsScaleBarSettings, QgsTextFormat, \
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

from .FileFunctions.create_field import CreateField
from .FileFunctions.adjust_average import AdjustAverage
from .FileFunctions.adjust_rate import Rate
from .FileFunctions.edit_columns import EditColumns
from .FileFunctions.general_value import GeneralValue
from .FileFunctions.interpolate import Interpolate
from .FileFunctions.manage_zones import ManageZones
from .FileFunctions.merge_layers import Merge
from .File_widget import FileWidget
# from multipleformats import my_layer
from .loading import Loading
from .qgisFuncs import list_groups_linked_to_layer, print_log, InfoButton, add_buttons_to_grid, ResetLayer, \
    upgrade_grid, TextInfoTest

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/FileOptions.ui'), resource_suffix='')


class CSVThread(QThread):
    on_finished = pyqtSignal()

    def __init__(self, layer, dir, parent=None):
        super(CSVThread, self).__init__()
        self.layer = layer
        self.dir = dir

    def run(self) -> None:
        layer = self.layer

        if not layer.isValid():
            print_log(self, self.run, msg="Falha ao carregar a layer")
            self.on_finished.emit()
            return

        field_names = [field.name() for field in layer.fields()]
        csv_name = layer.name().split('.')[0]
        out_path = os.path.join(self.dir, csv_name + '(coordenadas).csv')

        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(field_names + ['X_Coord', 'Y_Coord'])
            for feature in layer.getFeatures():
                centroid = feature.geometry().centroid().asPoint()
                writer.writerow(
                    [feature[name] for name in field_names] +
                    [round(centroid.x(), 8), round(centroid.y(), 8)]
                )

        print_log(self, self.run, msg="Concluído!")
        self.on_finished.emit()


class SaveThreadUTM(QThread):
    on_finished = pyqtSignal()

    def __init__(self, path, layer):
        super(SaveThreadUTM, self).__init__()
        self.path = path
        self.layer = layer

    def run(self) -> None:
        layer = self.layer
        if not layer.isValid():
            print_log(self, self.run, msg="Falha ao carregar a layer")
            self.on_finished.emit()
            return

        # Detect UTM zone from layer centroid
        extent = layer.extent()
        center_x = (extent.xMinimum() + extent.xMaximum()) / 2
        center_y = (extent.yMinimum() + extent.yMaximum()) / 2
        _, _, zone_number, zone_letter = utm.from_latlon(center_y, center_x)
        hemisphere = 6 if zone_letter >= 'N' else 7
        epsg_utm = int(f"32{hemisphere}{zone_number:02d}")

        dest_crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg_utm}")

        name = layer.name().split('.')[0] + "(UTM)"
        output_path = os.path.join(self.path, name + '.shp')

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        options.ct = QgsCoordinateTransform(
            layer.crs(), dest_crs, layer.transformContext()
        )
        QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, output_path, layer.transformContext(), options
        )

        print_log(self, self.run, msg="Concluído!")
        self.on_finished.emit()


class PrintPDF(QThread):
    on_finished = pyqtSignal(object)

    def tr(self, message):
        return QCoreApplication.translate('PrintPDF', message)

    def __init__(self, layer, project, image_path, option_image_path=None, unit='kg/ha', parent=None):
        super(PrintPDF, self).__init__()
        self.layer = layer
        self.project = project
        self.image_path = image_path
        self.option_image_path = option_image_path
        self.unit = unit

    def addLegend(self, layout, map_y, page_height):

        x = 10
        w = 20
        space_bet_map_legend = 20

        available_height = page_height - 15 - map_y - space_bet_map_legend

        rend = self.layer.renderer()
        first_rect = None
        count = len(rend.legendSymbolItems())
        if count > 2:
            step = min(10.0, available_height / count)
            aux = 0.0

            for i, lsi in enumerate(rend.legendSymbolItems()):

                color = lsi.symbol().color().name()
                name = lsi.label()

                item_y = map_y + space_bet_map_legend + aux
                box_h = step * 0.8

                polygon = QPolygonF()
                polygon.append(QPointF(x, 0))
                polygon.append(QPointF(w, 0))
                polygon.append(QPointF(w, box_h))
                polygon.append(QPointF(x, box_h))

                polygonItem = QgsLayoutItemPolygon(polygon, layout)
                polygonItem.attemptMove(
                    QgsLayoutPoint(8, item_y, QgsUnitTypes.LayoutMillimeters))

                layout.addLayoutItem(polygonItem)

                if i == 0:
                    first_rect = polygonItem

                props = {}
                props["color"] = color
                props["style"] = "solid"
                props["style_border"] = "solid"
                props["color_border"] = "0, 0, 0, 255"
                props["width_border"] = "0.5"
                props["joinstyle"] = "miter"

                symbol = QgsFillSymbol.createSimple(props)
                polygonItem.setSymbol(symbol)

                title = QgsLayoutItemLabel(layout)
                title.setText(name)
                _fmt = QgsTextFormat()
                font_size = max(6, min(12, int(step * 0.7)))
                _fmt.setFont(QFont("Arial", font_size, QFont.Bold))
                _fmt.setSize(font_size)
                title.setTextFormat(_fmt)
                title.setVAlign(Qt.AlignVCenter)
                title.setFixedSize(QgsLayoutSize(100, box_h))
                title.attemptMove(
                    QgsLayoutPoint(8 + (w - x) + 2, item_y,
                                   QgsUnitTypes.LayoutMillimeters))
                layout.addLayoutItem(title)

                aux += step
        else:
            step = 10.0
        return first_rect, step, count

    def run(self) -> None:
        layer_name = self.layer.name().split('.')[0]

        project = self.project

        layout = QgsPrintLayout(project)
        layout.initializeDefaults()

        layout.setName(layer_name)

        project.layoutManager().addLayout(layout)

        layout = project.layoutManager().layoutByName(layer_name)

        pc = layout.pageCollection()
        pc.page(0).setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)
        page_width = pc.page(0).pageSize().width()
        page_height = pc.page(0).pageSize().height()

        map = QgsLayoutItemMap(layout)
        map.grid().setEnabled(True)
        map.grid().setIntervalX(0.005)
        map.grid().setIntervalY(0.005)
        map.grid().setAnnotationEnabled(True)
        map.grid().setGridLineColor(QColor(0, 0, 0, 50))
        map.grid().setGridLineWidth(0.2)
        map.grid().setAnnotationPrecision(6)
        map.grid().setAnnotationFrameDistance(2)
        _grid_fmt = map.grid().annotationTextFormat()
        _grid_fmt.setColor(QColor(0, 0, 0))
        map.grid().setAnnotationTextFormat(_grid_fmt)

        map.grid().setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Right)
        map.grid().setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Top)
        map.grid().setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Bottom)
        map.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Bottom)
        map.grid().setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Left)
        map.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
        map.setRect(20, 20, 20, 20)
        map.setLayers([self.layer])
        rect = QgsRectangle(self.layer.extent())
        rect.scale(1.1)

        map.zoomToExtent(rect)
        map.attemptMove(QgsLayoutPoint(5, 30, QgsUnitTypes.LayoutMillimeters))
        map.attemptResize(QgsLayoutSize(page_width - 10, 180, QgsUnitTypes.LayoutMillimeters))

        layout.addLayoutItem(map)
        map_x = map.pos().x()
        map_y = map.pos().y()
        map_width = map.pos().x() + map.rect().width()
        map_height = map.pos().y() + map.rect().height()

        tree = list_groups_linked_to_layer(self.project.layerTreeRoot(), self.layer)

        first_r, node_h, count = self.addLegend(layout, map_height, page_height)

        name = tree[-2] if len(tree) >= 2 else ''
        fild = tree[-3] if len(tree) >= 3 else ''
        tal  = tree[-4] if len(tree) >= 4 else ''

        title = QgsLayoutItemLabel(layout)
        title.setText(name)
        _fmt = QgsTextFormat()
        _fmt.setFont(QFont("Arial", 28, QFont.Bold))
        _fmt.setSize(28)
        title.setTextFormat(_fmt)
        title.adjustSizeToText()
        title.attemptMove(QgsLayoutPoint(5, 5, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(title)

        title1 = QgsLayoutItemLabel(layout)
        title1.setText(fild + '\n' + tal)
        _fmt = QgsTextFormat()
        _fmt.setFont(QFont("Arial", 15))
        _fmt.setSize(15)
        title1.setTextFormat(_fmt)
        title1.setHAlign(Qt.AlignRight)
        title1.setVAlign(Qt.AlignTop)
        title1.adjustSizeToText()
        title1.attemptMove(
            QgsLayoutPoint(page_width - title1.sizeForText().width() - 5, 5, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(title1)

        # criar a moldura do mapa

        polygon = QPolygonF()
        polygon.append(QPointF(map_x, map_y))
        polygon.append(QPointF(map_width, map_y))
        polygon.append(QPointF(map_width, map_height))
        polygon.append(QPointF(map_x, map_height))

        polygonItem = QgsLayoutItemPolygon(polygon, layout)
        layout.addLayoutItem(polygonItem)

        props = {}
        props["color"] = "255, 255, 255, 0"
        props["style"] = "solid"
        props["style_border"] = "solid"
        props["color_border"] = "200, 200, 200, 255"
        props["width_border"] = "0.5"
        props["joinstyle"] = "miter"

        symbol = QgsFillSymbol.createSimple(props)
        polygonItem.setSymbol(symbol)

        scale_bar = QgsLayoutItemScaleBar(layout)
        scale_bar.setFixedSize(QgsLayoutSize(100, 20))
        scale_bar.setLinkedMap(map)
        scale_bar.setStyle('Line Ticks Up')
        scale_bar.setUnits(QgsUnitTypes.DistanceUnit.DistanceMeters)
        scale_bar.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFitWidth)
        scale_bar.setNumberOfSegmentsLeft(0)
        scale_bar.setNumberOfSegments(2)
        scale_bar.setMinimumBarWidth(10)
        scale_bar.setMaximumBarWidth(50)
        scale_bar.setUnitLabel("m")
        _sb_fmt = scale_bar.textFormat()
        _sb_font = _sb_fmt.font()
        _sb_font.setPointSize(9)
        _sb_fmt.setFont(_sb_font)
        _sb_fmt.setSize(9)
        scale_bar.setTextFormat(_sb_fmt)
        scale_bar.setHeight(2)

        # scale_bar.setPos(100, 100)

        scale_bar.attemptMove(QgsLayoutPoint(map_x + 5, map_y + map_height - 45, QgsUnitTypes.LayoutMillimeters))

        layout.addLayoutItem(scale_bar)

        # crair moldura legenda
        w = map.pos().x() + map.rect().width()
        h = page_height - 5
        if first_r is not None:
            x = map.pos().x()
            y = first_r.pos().y()
            y -= 5
            w = map.pos().x() + map.rect().width()
            h = y + node_h * count
            h += 29
            h = min(h, page_height - 5)

            polygon = QPolygonF()
            polygon.append(QPointF(x, y))
            polygon.append(QPointF(w, y))
            polygon.append(QPointF(w, h))
            polygon.append(QPointF(x, h))

            polygonItem = QgsLayoutItemPolygon(polygon, layout)
            layout.addLayoutItem(polygonItem)

        symbol = QgsFillSymbol.createSimple(props)
        polygonItem.setSymbol(symbol)

        image_name_arrow = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources',
                                        'NorthArrow_04.svg')

        north = QgsLayoutItemPicture(layout)
        north.setSvgFillColor(QColor(0, 0, 0, 255))
        north.setMode(QgsLayoutItemPicture.FormatSVG)
        north.setPicturePath(image_name_arrow)
        north.attemptMove(QgsLayoutPoint(10, 38, QgsUnitTypes.LayoutMillimeters))
        north.attemptResize(QgsLayoutSize(*[300, 300], QgsUnitTypes.LayoutPixels))
        layout.addLayoutItem(north)

        pic = QgsLayoutItemPicture(layout)
        pic.setMode(QgsLayoutItemPicture.FormatRaster)
        pic.setPicturePath(self.image_path)
        pic.attemptMove(QgsLayoutPoint(map_x + map_width - 35, page_height - 68, QgsUnitTypes.LayoutMillimeters))
        pic.attemptResize(QgsLayoutSize(*[300, 300], QgsUnitTypes.LayoutPixels))
        layout.addLayoutItem(pic)

        if self.option_image_path:
            image = Image.open(self.option_image_path)
            width, height = image.size
            ratio = width / height
            new_height = 256
            new_width = int(ratio * new_height)

            pic = QgsLayoutItemPicture(layout)
            pic.setMode(QgsLayoutItemPicture.FormatRaster)
            pic.setPicturePath(self.option_image_path)
            pic.attemptResize(QgsLayoutSize(*[new_width, new_height], QgsUnitTypes.LayoutPixels))

            pic.attemptMove(
                QgsLayoutPoint(map_x + map_width - (page_width - w) - pic.rect().width() - 5,
                               page_height - (page_height - h) - pic.rect().height() - 5,
                               QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(pic)

        title_uni = QgsLayoutItemLabel(layout)
        title_uni.setText(self.tr('Unidade: ') + self.unit)
        _fmt = QgsTextFormat()
        _fmt.setFont(QFont("Arial", 8))
        _fmt.setSize(8)
        title_uni.setTextFormat(_fmt)
        title_uni.adjustSizeToText()
        title_uni.attemptMove(QgsLayoutPoint(10, page_height - 10, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(title_uni)

        self.on_finished.emit(layout)


class SaveThread(QThread):
    on_finished = pyqtSignal()

    def __init__(self, path, layer):
        super(SaveThread, self).__init__()
        self.path = path
        self.layer = layer

    def run(self):
        name = self.layer.name() + "(exported)"
        output_path = os.path.join(self.path, name + '.shp')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        QgsVectorFileWriter.writeAsVectorFormatV3(
            self.layer, output_path, self.layer.transformContext(), options
        )
        print_log(self, self.run, msg="Concluído!")
        self.on_finished.emit()


class VRC(QThread):
    on_finished = pyqtSignal()
    on_error = pyqtSignal(str)

    def __init__(self, layer_path, index, new_out_path):
        super(VRC, self).__init__()
        self.layer_path = layer_path
        self.index = index
        self.new_out_path = new_out_path

    def run(self):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        args = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ExternalFunctions",
                            "ExtFunctions.exe")
        if not os.path.isfile(args):
            print_log(self, self.run, msg="Arquivo ExtFunctions.exe não encontrado!")
            self.on_error.emit("ExtFunctions.exe não encontrado.")
            return

        p = subprocess.Popen([args, 'convert_to_vrc', self.layer_path, str(self.index), self.new_out_path],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             startupinfo=si)
        output, err = p.communicate()
        if err:
            print_log(self, self.run, msg=f"Erro VRC: {err.decode(errors='replace')}")
        print_log(self, self.run, msg="Concluído!")
        self.on_finished.emit()


class FileOptions(QtWidgets.QWidget, FORM_CLASS):
    """
    Classe responsável por todas as funções da classe FileWidget, ou seja cada layer que for
    carregada no plugin.
    """

    def tr(self, message):
        return QCoreApplication.translate('FileOptions', message)

    reset_layer_signal = pyqtSignal(str, list)
    merged_layer_signal = pyqtSignal(str, list)
    back_button_hide_signal = pyqtSignal()
    back_button_show_signal = pyqtSignal()
    back_animation_signal = pyqtSignal()
    test_signal = pyqtSignal(object)

    def __init__(self, file_widget: FileWidget, project, iface, itens, main, parent=None):
        super(FileOptions, self).__init__(parent)
        self.pdf_thread = None
        self.file_name = None
        self.st = None
        self.loading_export = None
        self.csv_utm = None
        self.csv = None
        self.loading_csv_utm = None
        self.loading_csv = None
        self.setupUi(self)

        self.pushButtonExport.setText(self.tr("EXPORTAR"))
        self.pushButtonPrint.setText(self.tr("IMPRIMIR"))
        self.pushButtonReset.setText(self.tr("RESETAR"))
        self.pushButtonumaps.setText(self.tr("UNIR"))
        self.pushButtonTaxa.setText(self.tr("TAXAS"))
        self.pushButtonColumn.setText(self.tr("COLUNAS"))
        self.pushButtonInterpolate.setText(self.tr("INTERPOLAR"))
        self.pushButtonChangeMean.setText(self.tr("AJUSTAR MÉDIA"))
        self.pushButtonManejo.setText(self.tr("Z. MANEJO"))
        self.pushButtonGen_value.setText(self.tr("VALOR GERAL"))

        self.label_title.setText(self.tr("União > Escolha um mapa para unir"))
        self.label_taxas.setText(self.tr("Taxas > Selecione uma coluna"))
        self.label_title_export.setText(self.tr("Exportar > Exportar para o formato"))
        self.label_title_export_2.setText(self.tr("Imprimir > Imprimir PDF"))
        self.label_title_3.setText(self.tr("Colunas > Gerenciar Colunas"))
        self.label_interpolate.setText(self.tr("Interpolar > Selecione uma Coluna"))
        self.label_interpolate_2.setText(self.tr("Ajustar Média > Selecionar uma Coluna"))
        self.label_interpolate_3.setText(self.tr("Zonas de manejo"))
        self.label_interpolate_4.setText(self.tr("Valor Geral"))

        self.proLabel.setText(self.tr("Coeficiênte"))
        self.proLabel_2.setText(self.tr("Tamanho do Pixel (Metros)"))
        self.pushButtonManualInterpolate.setText(self.tr("Contorno Manual"))
        self.pushButtonLoad.setText(self.tr("Carregar"))
        self.InterpolatePushButton.setText(self.tr("Interpolar"))

        self.pushButtonImage.setText(self.tr("Selecione uma imagem"))
        self.printPDF_button.setText(self.tr("Imprimir"))

        self.file_widget = file_widget
        self.project = project
        self.iface = iface
        self.itens = itens
        self.main = main
        self.layer = None
        self.layer_name = ''
        self.layer_to_uni = None
        self.messages = TextInfoTest()
        self.init()

    def init(self) -> None:
        self.layer = self.file_widget.layer
        self.layer_name = self.file_widget.filename
        self.pushButtonExport.clicked.connect(self.export_section)
        self.pushButtonPrint.clicked.connect(self.print_pdf)
        self.pushButtonReset.clicked.connect(self.reset_layer)

        self.pushButtonumaps.clicked.connect(lambda: Merge(self))
        self.pushButtonGen_value.clicked.connect(lambda: GeneralValue(self))
        self.pushButtonTaxa.clicked.connect(lambda: Rate(self))
        self.pushButtonColumn.clicked.connect(lambda: EditColumns(self))
        self.pushButtonInterpolate.clicked.connect(lambda: Interpolate(self))
        self.pushButtonChangeMean.clicked.connect(lambda: AdjustAverage(self))
        self.pushButtonManejo.clicked.connect(lambda: ManageZones(self))
        self.pushButtonCreateField.clicked.connect(lambda: CreateField(self))

        InfoButton(self.messages.tax_info(), self.pushButtonChangeMean)
        InfoButton(self.messages.interpolate_info(), self.pushButtonInterpolate)
        InfoButton(self.messages.interpolate_info(), self.pushButtonColumn)
        InfoButton(self.messages.rate_info(), self.pushButtonTaxa)
        InfoButton(self.messages.join_info(), self.pushButtonumaps)
        InfoButton(self.messages.reset_info(), self.pushButtonReset)
        InfoButton(self.messages.print_info(), self.pushButtonPrint)
        InfoButton(self.messages.export_info(), self.pushButtonExport)
        InfoButton(self.messages.manage_info(), self.pushButtonManejo)
        InfoButton(self.messages.general_info(), self.pushButtonGen_value)
        InfoButton(self.messages.manage_zones(), self.pushButtonManejo)
        InfoButton(self.messages.column_info(), self.pushButtonColumn)
        InfoButton(self.messages.create_field_info(), self.pushButtonCreateField)

    @pyqtSlot(object, object, object)
    def on_layer_update_feat(self, features, callback, progress):
        from qgis.utils import iface as _iface
        canvas = _iface.mapCanvas()

        items = list(features.items())
        provider = self.layer.dataProvider()
        chunk_size = 100
        total = len(items)

        # Extract field_index and preserve current class count before chunking
        field_index = -1
        for feat_id, attr_map in items:
            for fi in attr_map:
                field_index = fi
            break
        renderer = self.layer.renderer()
        num_classes = len(renderer.ranges()) if hasattr(renderer, 'ranges') else 5

        canvas.freeze(True)
        idx = 0

        def _finish():
            canvas.freeze(False)
            canvas.refresh()
            if field_index >= 0:
                upgrade_grid(self.layer, _iface, field_index, classes=num_classes, deferred=True)
            for item in self.itens:
                if item.filename == self.file_widget.filename:
                    self.file_widget.update_fields_list()
                    self.file_widget.update()
                    item.update_fields_list()
                    item.update()
            if callable(callback):
                callback()

        def process_chunk():
            nonlocal idx
            chunk = dict(items[idx:idx + chunk_size])
            if chunk:
                provider.changeAttributeValues(chunk)
            idx += chunk_size
            if callable(progress) and total > 0:
                progress(min(idx / total * 100, 100))
            if idx < len(items):
                QTimer.singleShot(0, process_chunk)
            else:
                _finish()

        if items:
            QTimer.singleShot(0, process_chunk)
        else:
            canvas.freeze(False)
            if callable(callback):
                callback()

    @pyqtSlot()
    def export_section(self):

        self.pushButton_return_export.disconnect()
        self.pushButton_return_export.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))

        self.back_button_hide_signal.emit()

        home = str(Path.home())
        self.currentPath.setText(home)

        @pyqtSlot()
        def open_path():
            dire = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr("Salvar"), home,
                                                              QtWidgets.QFileDialog.ShowDirsOnly |
                                                              QtWidgets.QFileDialog.DontResolveSymlinks)

            self.currentPath.setText(dire)

        def change_stack_index(direc=True):
            if direc:

                self.stackedWidget_export.setCurrentIndex(1)
                self.label_title_export.setText(self.tr('Selecione uma coluna:'))

                flds1 = [f for f in self.layer.fields()]
                names1 = [f.name() for f in flds1]

                '''columns = 2
                rows = 99'''

                @pyqtSlot(int)
                def on_click(index, button):
                    field = names1[index]

                    layer_path = self.layer.dataProvider().dataSourceUri()
                    layer_name = self.layer_name + '(' + field + ')' + '.vrc'

                    self.loading_vrc = Loading(button)

                    path_to_save = self.currentPath.text()
                    new_out_path = os.path.join(path_to_save, layer_name)

                    self.loading_vrc.start()
                    self.loading_vrc.show()
                    self.vrc = VRC(layer_path, index, new_out_path)

                    if os.path.exists(path_to_save):
                        def on_vrc_finished():
                            self.loading_vrc.stop()
                            self.loading_vrc.hide()
                            self.start_file(path_to_save)

                        def on_vrc_error(msg):
                            self.loading_vrc.stop()
                            self.loading_vrc.hide()
                            self.iface.messageBar().pushMessage(
                                self.tr("Erro VRC"), msg, level=Qgis.Critical, duration=5
                            )

                        self.vrc.on_finished.connect(on_vrc_finished)
                        self.vrc.on_error.connect(on_vrc_error)
                        self.vrc.start()

                add_buttons_to_grid(self.gridLayout_13, self.layer, on_click)

                self.pushButtonExport_vrc.clicked.disconnect()
            else:
                self.stackedWidget_export.setCurrentIndex(0)
                self.stackedWidget.setCurrentIndex(0)
                self.label_title_export.setText(self.tr('Exportar para:'))
                self.back_button_show_signal.emit()

                ''' É preciso desconctar os sinais, caso contrário sera feita várias chamadas pelo mesmo objeto'''
                self.pushButton_return_export.clicked.disconnect()
                self.findPath.clicked.disconnect()
                self.pushButtonExportSHP.clicked.disconnect()
                self.pushButtonExportCsv.clicked.disconnect()
                self.pushButtonExportSHPUTM.clicked.disconnect()

        self.stackedWidget.setCurrentIndex(3)

        for btn in (self.pushButtonExportSHP, self.pushButtonExportCsv,
                    self.pushButtonExportSHPUTM, self.pushButtonExport_vrc,
                    self.pushButton_return_export, self.findPath):
            try:
                btn.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass

        self.pushButtonExportSHP.clicked.connect(self.export_shp)
        self.pushButtonExportCsv.clicked.connect(self.export_csv)
        self.pushButtonExportSHPUTM.clicked.connect(self.export_csv_utm)
        self.pushButtonExport_vrc.clicked.connect(lambda: change_stack_index(True))
        self.pushButton_return_export.clicked.connect(lambda: change_stack_index(False))
        self.findPath.clicked.connect(open_path)

    @pyqtSlot()
    def export_shp(self):
        path = self.currentPath.text()

        self.loading_shp = Loading(self.pushButtonExportSHP)

        self.loading_shp.start()
        self.loading_shp.show()
        self.st = SaveThread(path, self.layer)
        self.st.on_finished.connect(self.loading_shp.stop)
        self.st.on_finished.connect(self.loading_shp.hide)
        self.st.on_finished.connect(lambda: self.start_file(path))
        self.st.start()

    @staticmethod
    def start_file(path):
        if os.path.exists(path):
            os.startfile(os.path.realpath(path))

    @pyqtSlot()
    def export_csv(self) -> None:
        """
        Gerar .csv adicionando os dados
        de coordenadas lat, long
        """

        path = self.currentPath.text()
        self.loading_csv = Loading(self.pushButtonExportCsv)

        self.loading_csv.start()
        self.loading_csv.show()
        self.csv = CSVThread(self.layer, path)
        self.csv.on_finished.connect(self.loading_csv.stop)
        self.csv.on_finished.connect(self.loading_csv.hide)
        self.csv.on_finished.connect(lambda: self.start_file(path))
        self.csv.start()

    @pyqtSlot()
    def export_csv_utm(self) -> None:
        """
        Exporta a camada como Shapefile reprojetado para UTM,
        detectando automaticamente a zona UTM pelo centroide da camada.
        """

        path = self.currentPath.text()

        self.loading_csv_utm = Loading(self.pushButtonExportSHPUTM)

        self.loading_csv_utm.start()
        self.loading_csv_utm.show()
        self.csv_utm = SaveThreadUTM(path, self.layer)
        self.csv_utm.on_finished.connect(self.loading_csv_utm.stop)
        self.csv_utm.on_finished.connect(self.loading_csv_utm.hide)
        self.csv_utm.on_finished.connect(lambda: self.start_file(path))
        self.csv_utm.start()

    def list_group_layers(self, group):
        layers = []
        for child in group.children():
            if isinstance(child, QgsLayerTreeGroup):
                layers.extend(self.list_group_layers(child))
            else:
                layers.append((child.layer(), group))
        return layers

    @pyqtSlot()
    def reset_layer(self):
        self.reset_loading = Loading(self.pushButtonReset)
        self.reset_loading.start()
        self.reset_loading.show()
        self.back_button_hide_signal.emit()
        self.reset = ResetLayer(self.layer, self.project)
        self.reset.finished_signal.connect(lambda new_layer, tree: (
            self.reset_layer_signal.emit(new_layer, tree),
            self.file_widget.remove_without_signal(),
            self.back_animation_signal.emit(),
            self.reset_loading.stop(),
            self.reset_loading.deleteLater(),
            self.back_button_show_signal.emit(),
            self.deleteLater()
        ))
        self.reset.finished_fail.connect(lambda msg: (
            self.iface.messageBar().pushMessage(msg, level=Qgis.Critical, duration=5),
            self.back_animation_signal.emit(),
            self.reset_loading.stop(),
            self.reset_loading.deleteLater(),
            self.back_button_show_signal.emit(),
            self.deleteLater()
        ))
        self.reset.start()

    @pyqtSlot()
    def print_pdf(self):
        self.back_button_hide_signal.emit()
        home = str(Path.home())
        self.currentPath_pdf.setText(home)

        @pyqtSlot()
        def on_path_select():
            dire = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr("Salvar"), home,
                                                              QtWidgets.QFileDialog.ShowDirsOnly |
                                                              QtWidgets.QFileDialog.DontResolveSymlinks)

            self.currentPath_pdf.setText(dire)

        @pyqtSlot()
        def on_button_image_clicked():
            image_name, _ = QFileDialog.getOpenFileName(self, self.tr('Abrir arquivo de imagem'), 'c:\\',
                                                        self.tr("Arquivos de imagens (*.jpg *.png)"))

            if image_name:
                self.pushButtonImage.setText('')
                self.pushButtonImage.setObjectName(image_name)
                self.pushButtonImage.setIcon(QIcon(image_name))
                self.pushButtonImage.setIconSize(QSize(100, 100))

                if not self.pushButtonImage.children():
                    c_push_button = QPushButton(self.pushButtonImage)
                    c_push_button.setFixedSize(16, 16)
                    c_push_button.setStyleSheet('''
                        QPushButton{
                            image: url(:/plugins/StaraMaps/close.png);
                            padding: 2px;
                            color: rgb(250, 250, 250);
                            border: none;
                        }
                        
                        QPushButton::hover{
                            background-color: rgb(245, 245, 245);
                        }
                    ''')
                    c_push_button.move(5, 5)
                    c_push_button.clicked.connect(
                        lambda: [self.pushButtonImage.setIcon(QIcon()),
                                 self.pushButtonImage.setText(self.tr('Selecione uma imagem')),
                                 self.pushButtonImage.setObjectName('pushButtonImage'),
                                 c_push_button.deleteLater()])
                    c_push_button.show()

        @pyqtSlot(int, object)
        def on_click(idx, obj):
            renderer = self.layer.renderer()
            current_classes = len(renderer.ranges()) if hasattr(renderer, 'ranges') else 5
            upgrade_grid(self.layer, self.iface, idx, classes=current_classes)

            @pyqtSlot()
            def on_print_clicked():
                default_image_name = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources',
                                                  'logomarca_Stara_semcontorno.png')

                option_image_name = None

                if os.path.isfile(self.pushButtonImage.objectName()):
                    option_image_name = self.pushButtonImage.objectName()

                self.loading_pdf = Loading(self.printPDF_button)

                self.loading_pdf.start()
                self.loading_pdf.show()

                self.print_thread = PrintPDF(self.layer,
                                             self.project,
                                             default_image_name,
                                             option_image_name,
                                             self.comboBox_unit.currentText())
                self.print_thread.on_finished.connect(self.open_pdf)
                self.print_thread.on_finished.connect(lambda: (self.loading_pdf.stop(),
                                                               self.loading_pdf.hide(),
                                                               self.loading_pdf.deleteLater()))
                self.print_thread.start()

            self.stackedWidget_3.setCurrentIndex(1)
            try:
                self.pushButtonImage.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                self.printPDF_button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.pushButtonImage.clicked.connect(on_button_image_clicked)
            self.printPDF_button.clicked.connect(on_print_clicked)

        self.stackedWidget.setCurrentIndex(4)

        for btn in (self.pushButton_return_pdf, self.pushButtonImage,
                    self.printPDF_button, self.findPath_pdf):
            try:
                btn.disconnect()
            except (RuntimeError, TypeError):
                pass
        self.widget.paintEvent = None

        self.pushButton_return_pdf.clicked.connect(
            lambda: (
                self.stackedWidget.setCurrentIndex(0),
                self.back_button_show_signal.emit(),
                self.stackedWidget_3.setCurrentIndex(0)
            ))
        self.widget.paintEvent = self.widget_paintEvent

        self.findPath_pdf.clicked.connect(on_path_select)

        add_buttons_to_grid(self.gridLayout_19, self.layer, on_click)

    def widget_paintEvent(self, a0: QPaintEvent) -> None:
        painter = QPainter(self.widget)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.black, 2, Qt.DotLine))
        x_frame = self.frame_28.x()
        width_frame = self.frame_28.width()
        y_frame = self.frame_28.y()
        height_frame = self.frame_28.height()

        x_label = self.pushButtonImage.x()
        y_label = self.pushButtonImage.y()
        height_label = self.pushButtonImage.height()

        painter.drawLine(QPointF(x_frame + width_frame, y_frame), QPointF(x_label, y_label))
        painter.drawLine(QPointF(x_frame + width_frame, y_frame + height_frame),
                         QPointF(x_label, y_label + height_label))

    @pyqtSlot(object)
    def open_pdf(self, layout):

        path = self.currentPath_pdf.text()

        path += '/' + self.layer_name + '.pdf'

        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToPdf(path, QgsLayoutExporter.PdfExportSettings())
        if result != QgsLayoutExporter.Success:
            self.iface.messageBar().pushMessage(
                self.tr("Erro"), self.tr("Falha ao exportar PDF."),
                level=Qgis.Critical, duration=5
            )
        self.start_file(path)

        manager = self.project.layoutManager()
        manager.removeLayout(layout)
