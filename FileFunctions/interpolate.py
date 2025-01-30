import os

import processing
from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QPushButton, QFileDialog
from qgis._analysis import QgsInterpolator, QgsIDWInterpolator, QgsGridFileWriter
from qgis._core import QgsVectorLayer, QgsApplication, QgsTask, QgsWkbTypes, QgsProcessingFeatureSourceDefinition, \
    QgsFeatureRequest, QgsVectorFileWriter, QgsCoordinateTransformContext

from ..loading import Loading
from ..map_canvas import InterpolateMapCanvas
from ..qgisFuncs import upgrade_grid, MyFeedBack, remove_file, list_groups_linked_to_layer, add_buttons_to_grid, \
    same_file


class Interpolate(QObject):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        self.index = 0
        self.manual_layer_contour = None
        self.button_created = False
        self.init()

    def init(self) -> None:
        self.main.stackedWidget.setCurrentIndex(6)
        self.main.back_button_hide_signal.emit()
        self.canvas = InterpolateMapCanvas(self.main.layer, self.main.page_19)

        self.main.progressBar_interpolate.hide()
        self.main.label_interpolate_info.hide()

        self.main.pushButton_return_interpolate.clicked.connect(lambda: self.deleteLater())

        self.task_mgr = QgsApplication.taskManager()
        self.feed = MyFeedBack()
        self.feed.progressChanged.connect(self.main.progressBar_interpolate.setValue)

        layer_path = self.main.layer.dataProvider().dataSourceUri()
        layer_path_split = layer_path.split('/')
        if len(layer_path_split) == 1:
            layer_path = layer_path.replace('\\', '/')
            layer_path_split = layer_path.split('/')

        layer_path_split.pop(-1)
        only_path = '/'.join(layer_path_split)
        self.new_path_tif_mask = only_path + '/' + self.main.layer_name + '[mask].tif'
        self.new_path_interpolated = only_path + '/' + self.main.layer_name + '[Interpolated]'
        add_buttons_to_grid(self.main.gridLayout_12, self.main.layer, self.on_click)

        self.check_saved_exist()

    def check_saved_exist(self):
        path_split = self.main.layer.dataProvider().dataSourceUri()
        path_split = path_split.split('/')

        path_split.pop(-1)

        only_path = '/'.join(path_split)
        output_layer = only_path + '/' + self.main.layer.name() + '[BORD_SAVED].kml'

        if os.path.exists(output_layer):
            vl = QgsVectorLayer(output_layer,
                                self.main.layer.id() + 'temporary', "ogr")

            self.set_manual_contour(vl)

            self.set_manual_contour(vl)

    def deleteLater(self) -> None:
        print(f'{self.__class__} Deleted')
        self.main.stackedWidget.setCurrentIndex(0),
        self.main.label_interpolate.setText(self.tr('Selecione uma Coluna'))
        self.main.stackedWidget_interpolate.setCurrentIndex(0)
        self.canvas.points.deleteLater()
        self.canvas.dock.deleteLater()
        self.canvas.deleteLater()
        self.main.back_button_show_signal.emit()
        self.main.pushButton_return_interpolate.disconnect()
        self.main.pushButtonManualInterpolate.disconnect()
        self.main.InterpolatePushButton.disconnect()
        self.main.pushButtonLoad.disconnect()
        super().deleteLater()

    @pyqtSlot(QgsVectorLayer)
    def set_manual_contour(self, vec) -> None:

        sender = self.sender()
        self.manual_layer_contour = vec

        if isinstance(sender, InterpolateMapCanvas):
            path_split = self.main.layer.dataProvider().dataSourceUri()
            path_split = path_split.split('/')

            path_split.pop(-1)

            only_path = '/'.join(path_split)

            output_layer = only_path + '/' + self.main.layer.name() + '[BORD_SAVED].kml'

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "KML"
            options.fileEncoding = 'utf-8'
            # options.datasourceOptions = ["NameField=ulica"]

            QgsVectorFileWriter.writeAsVectorFormatV2(layer=vec, fileName=output_layer,
                                                      transformContext=QgsCoordinateTransformContext(), options=options)

            self.main.stackedWidget_interpolate.setCurrentIndex(1)

        if not self.button_created:
            self.temp_button = QPushButton(self.main.pushButtonManualInterpolate)
            self.temp_button.setObjectName('temp_button')
            self.temp_button.setText(self.tr('Área realizada') + "\n" + self.tr('(Clique para remover.)'))
            self.temp_button.resize(self.main.pushButtonManualInterpolate.size())
            self.temp_button.clicked.connect(lambda: (
                self.clean_contour(),
                self.temp_button.deleteLater()
            ))
            self.temp_button.show()
            self.button_created = True

        self.manual_layer_contour = vec

    def clean_contour(self):
        self.manual_layer_contour = None
        self.button_created = False
        # check_remove_memorylayer(self.main.layer)

    @pyqtSlot(int, object)
    def on_click(self, index, obj) -> None:
        self.index = index

        upgrade_grid(self.main.layer, self.main.iface, index)
        self.main.stackedWidget_interpolate.setCurrentIndex(1)
        self.main.label_interpolate.setText(self.tr('Interpolar coluna ') + obj.text())

        self.main.pushButtonManualInterpolate.clicked.connect(lambda: (
            self.main.stackedWidget_interpolate.setCurrentIndex(2),
            self.open_canvas()
        ))
        self.main.pushButtonLoad.clicked.connect(self.open_exist)
        self.main.InterpolatePushButton.clicked.connect(self.on_interpolate_clicked)
        if self.button_created:
            self.temp_button.resize(self.main.pushButtonManualInterpolate.size())

    @pyqtSlot()
    def open_exist(self):
        file_name, _ = QFileDialog.getOpenFileName(self.main, 'Abrir arquivo de borda', 'c:\\',
                                                   "Arquivos (*.kml *.shp)")

        if file_name:
            vl = QgsVectorLayer(file_name,
                                self.main.layer.id() + 'temporary', "ogr")

            self.set_manual_contour(vl)

    def open_canvas(self):

        self.canvas.feat_geo_signal.connect(lambda vec: self.set_manual_contour(vec))
        self.canvas.resize(self.main.page_19.size())
        self.canvas.show()

    def on_interpolate_clicked(self):
        self.main.pushButton_return_interpolate.setEnabled(False)
        self.coe_text = self.main.coeEdit.text()
        self.pixel = self.main.pixelSizeLineEdit.text()
        self.main.progressBar_interpolate.show()
        self.main.label_interpolate_info.show()
        if self.coe_text == '' and self.pixel == '':
            return

        self.loading_interpolate = Loading(self.main.InterpolatePushButton)
        self.loading_interpolate.start()
        self.loading_interpolate.show()

        task = QgsTask.fromFunction('my task',
                                    self.get_centroids, self.main.layer, on_finished=self.on_get_centroids_finished)
        self.task_mgr.addTask(task)

    def get_centroids(self, task, layer):

        self.main.label_interpolate_info.setText(self.tr('Gerando centroids ') + layer.name())

        if layer.geometryType() != QgsWkbTypes.PointGeometry:
            params = {
                'INPUT': QgsProcessingFeatureSourceDefinition(layer.dataProvider().dataSourceUri(),
                                                              selectedFeaturesOnly=False, featureLimit=-1,
                                                              flags=QgsProcessingFeatureSourceDefinition.FlagOverrideDefaultGeometryCheck,
                                                              geometryCheck=QgsFeatureRequest.GeometrySkipInvalid),
                'ALL_PARTS': False, 'OUTPUT': 'TEMPORARY_OUTPUT'}

            centroids = processing.run("native:centroids", params, feedback=self.feed)["OUTPUT"]
        else:
            centroids = layer
        return centroids

    def on_get_centroids_finished(self, exception, value=None):

        if exception is None:
            self.main.label_interpolate_info.setText(self.tr('Gerando centroids acabou'))
            task = QgsTask.fromFunction('my task 2', self.get_contour, value,
                                        on_finished=self.on_get_contour_finished)
            self.task_mgr.addTask(task)

    def get_contour(self, task, layer):
        self.main.label_interpolate_info.setText(self.tr('Fazendo contorno ') + layer.name())

        if self.manual_layer_contour is None:
            params = {
                'INPUT': layer,
                'KNEIGHBORS': 10,
                'FIELD': '',
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }
            contour = processing.run("qgis:knearestconcavehull", params, feedback=self.feed).get('OUTPUT', None)
        else:
            contour = self.manual_layer_contour
            self.manual_layer_contour = None
        return [contour, layer]

    def on_get_contour_finished(self, exception, value=None):
        if exception is None:
            self.main.label_interpolate_info.setText(self.tr('Fazendo contorno acabou'))
            task = QgsTask.fromFunction('my task 3', self.get_interpolate, value[1], value[0])
            task.taskCompleted.connect(lambda: self.on_get_interpolate_finished(value[0]))
            self.task_mgr.addTask(task)

    def get_interpolate(self, task, layer, contour):

        self.main.label_interpolate_info.setText(self.tr('Gerando interpolado ') + layer.name())
        layer_data = QgsInterpolator.LayerData()
        layer_data.source = layer
        layer_data.zCoordInterpolation = False
        layer_data.setDistanceCoefficient = float(self.coe_text)
        layer_data.interpolationAttribute = int(self.index)
        idw_interpolator = QgsIDWInterpolator([layer_data])
        export_path = self.new_path_tif_mask

        rect = contour.extent()
        res = int(self.pixel) / 100000  # Converter Sander, valor em metros
        ncols = int((rect.xMaximum() - rect.xMinimum()) / res)
        nrows = int((rect.yMaximum() - rect.yMinimum()) / res)
        output = QgsGridFileWriter(idw_interpolator, export_path, rect, ncols, nrows)
        output.writeFile(feedback=self.feed)

    def on_get_interpolate_finished(self, value):
        self.main.label_interpolate_info.setText(self.tr('Interolando terminou'))
        task = QgsTask.fromFunction('my task 4', self.get_final_clip, value, on_finished=self.on_final_clip_finished)
        self.task_mgr.addTask(task)

    def get_final_clip(self, task, layer):
        self.main.label_interpolate_info.setText(self.tr('Fazendo recorte ') + layer.name())

        params = {'INPUT': self.new_path_tif_mask,
                  'MASK': layer,
                  'SOURCE_CRS': None, 'TARGET_CRS': None, 'TARGET_EXTENT': None,
                  'NODATA': None, 'ALPHA_BAND': False, 'CROP_TO_CUTLINE': True,
                  'KEEP_RESOLUTION': False, 'SET_RESOLUTION': False,
                  'X_RESOLUTION': None, 'Y_RESOLUTION': None,
                  'MULTITHREADING': False, 'OPTIONS': '', 'DATA_TYPE': 0,
                  'EXTRA': '', 'OUTPUT': 'TEMPORARY_OUTPUT'}
        new = processing.run("gdal:cliprasterbymasklayer", params, feedback=self.feed).get('OUTPUT', None)
        return new

    def on_final_clip_finished(self, exeption, value=None):
        if exeption is None:
            self.main.label_interpolate_info.setText(self.tr('Recorte terminou'))
            task = QgsTask.fromFunction('my task 5', self.r_to_vec, value)
            task.taskCompleted.connect(self.on_r_to_vect_finished)
            self.task_mgr.addTask(task)

    def r_to_vec(self, task, layer_path):
        self.main.label_interpolate_info.setText(self.tr('Convertendo para .shp...'))  # + layer_path)

        self.new_path_interpolated = same_file(self.new_path_interpolated + str(self.index) + '.shp')

        params = {'input': layer_path, 'type': 2, 'column': 'value', '-s': False,
                  '-v': True, '-z': False, '-b': False, '-t': False,
                  'output': self.new_path_interpolated,
                  'GRASS_REGION_PARAMETER': None, 'GRASS_REGION_CELLSIZE_PARAMETER': 0,
                  'GRASS_OUTPUT_TYPE_PARAMETER': 0, 'GRASS_VECTOR_DSCO': '', 'GRASS_VECTOR_LCO': '',
                  'GRASS_VECTOR_EXPORT_NOCAT': False}

        processing.run("grass7:r.to.vect", params, feedback=self.feed)

    def on_r_to_vect_finished(self):
        remove_file(self.new_path_tif_mask)
        remove_file(self.new_path_tif_mask + '.aux.xml')

        self.main.label_interpolate_info.hide()
        self.main.progressBar_interpolate.setValue(0)
        self.main.progressBar_interpolate.hide()
        arr = list_groups_linked_to_layer(self.main.project.layerTreeRoot(), self.main.layer)
        tree = arr[::-1][1:]
        self.main.merged_layer_signal.emit(self.new_path_interpolated, tree)
        self.loading_interpolate.stop()
        self.loading_interpolate.deleteLater()
        self.canvas.points.deleteLater()
        self.canvas.dock.deleteLater()
        self.canvas.deleteLater()
        self.main.back_animation_signal.emit()
        self.deleteLater()
