import os
import sys
import typing

import geopandas as gpd
import pandas as pd
from PyQt5 import uic
from PyQt5.QtCore import QSize, pyqtSlot, pyqtSignal, QThread
from PyQt5.QtGui import QFocusEvent
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QListWidget
from shapely.geometry import Point

from loading import Loading
from message import Message, Messages

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/PointMap.ui'), resource_suffix='')


class PointToShpConvert(QThread):
    error_signal = pyqtSignal()
    finished_signal = pyqtSignal()

    def __init__(self, column_1, column_2, file, out_file, parent=None):
        super(PointToShpConvert, self).__init__(parent)
        self.column_1 = column_1
        self.column_2 = column_2
        self.file = file
        self.out_file = out_file

    def __conversion(self) -> tuple:
        lat = None
        long = None
        self.df = pd.read_csv(self.file, sep=r'[;, \t]+', engine='python')

        column_1 = self.df.get(self.column_1)
        column_2 = self.df.get(self.column_2)

        if column_1 is not None and column_2 is not None:
            lat = column_1
            long = column_2

        # Caso a arquivo não tenha colunas (header)
        if lat is None and long is None:
            self.df = pd.read_csv(self.file, sep=r'[;, \t]+', engine='python')
            cols = list(self.df.columns.values)
            for count, column in enumerate(cols):
                cols[count] = "F" + str(count)

            vals = self.df.values.tolist()  # get the values for the rows
            self.df = pd.DataFrame(vals, columns=cols)
            column_1 = self.df.get('F0')
            column_2 = self.df.get('F1')
            if column_1 is not None and column_2 is not None:
                lat = column_1
                long = column_2

        return lat, long

    def run(self) -> None:
        lat, long = self.__conversion()

        # Nada deu certo
        if lat is None and long is None:
            self.error_signal.emit()
            return

        try:
            df = pd.read_csv(self.file, sep=r'[;, \t]+', engine='python')
            geometry = [Point(xy) for xy in zip(lat, long)]
            crs = {'init': 'epsg:4326'}
            gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
            gdf.to_file(filename=self.out_file, driver='ESRI Shapefile')
        except Exception as e:
            print(e)
            self.error_signal.emit(e)
        self.finished_signal.emit()


class FloatList(QListWidget):
    def __init__(self, parent=None):
        super(FloatList, self).__init__(parent)
        self.inicial_height = 0
        self.init()

    def addItem(self, item) -> None:
        super().addItem(item)

    def addItems(self, labels: typing.Iterable[typing.Optional[str]]) -> None:
        super().addItems(labels)

    def clear(self) -> None:
        super().clear()

    def init(self) -> None:
        self.inicial_height = self.parent().height()
        self.setFixedWidth(100)
        self.parent().focusInEvent = self.parent_focusIn_event

        self.itemClicked.connect(self.list_item_clicked)
        self.hide()

    def list_item_clicked(self, item):
        self.parent().setText(item.text())
        self.parent().setMinimumHeight(self.inicial_height)
        self.parent().setMaximumHeight(self.inicial_height)
        self.resize(self.height(), self.parent().height())
        self.hide()
        print('aqui')

    @pyqtSlot(QFocusEvent)
    def parent_focusIn_event(self, event: QFocusEvent) -> None:
        self.parent().setMinimumHeight(80)
        self.parent().setMaximumHeight(80)
        self.resize(self.height(), self.parent().height())
        self.show()


class PointMap(QWidget, FORM_CLASS):
    finish_signal = pyqtSignal()
    cancel_signal = pyqtSignal()

    def __init__(self, file, out_file, parent=None):
        super(PointMap, self).__init__(parent)
        self.setupUi(self)
        self.file = file
        self.out_file = out_file
        self.init()
        self.centralize()
        self.show()

    def init(self) -> None:
        self.setMaximumWidth(350)
        self.setMaximumWidth(350)
        shadow = QGraphicsDropShadowEffect()
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setBlurRadius(15)
        self.setGraphicsEffect(shadow)

        self.addPushButton.clicked.connect(self.add)
        self.cancelPushButton.clicked.connect(self.cancel_signal.emit)

        self.check_columns()

    def centralize(self) -> None:
        self.resize(QSize(self.parent().width() - 140, self.parent().height() - 120))
        self.move(int(self.parent().width() / 2 - self.width() / 2),
                  int(self.parent().height() / 2 - self.height() / 2))

    @staticmethod
    def count_decimal_places(value):
        """Conta o número de casas decimais em um valor float."""
        text = str(value)
        if '.' in text:
            return len(text.split('.')[1])
        return 0

    def identify_coordinate_columns(self, df):
        float_columns = df.select_dtypes(include=['float64']).columns
        column_scores = {}
        for col in float_columns:
            # Calcula a variabilidade
            variability = df[col].max() - df[col].min()

            # Calcula a média de casas decimais
            decimal_places_avg = df[col].apply(self.count_decimal_places).mean()

            # Define um score baseado na variabilidade e na quantidade média de casas decimais
            column_scores[col] = (variability, decimal_places_avg)

        # Ordena as colunas pelo score (variabilidade e casas decimais), priorizando maior variabilidade e precisão
        sorted_columns = sorted(column_scores, key=lambda x: (column_scores[x][1], column_scores[x][0]), reverse=True)

        # Verifica se temos pelo menos duas colunas com alta variabilidade e precisão
        if len(sorted_columns) < 2:
            raise ValueError("Não foi possível identificar duas colunas de coordenadas no arquivo CSV.")

        # Seleciona as duas colunas com maior variabilidade e precisão como coordenadas

        return sorted_columns[:2]

    def check_columns(self) -> None:
        df = pd.read_csv(self.file, sep=r'[;, \t]+', engine='python')
        columns = self.identify_coordinate_columns(df)

        self.longLineEdit.setText(columns[1])
        self.latLineEdit.setText(columns[0])

        self.lat = FloatList(self.latLineEdit)
        self.lat.addItems(columns)
        self.long = FloatList(self.longLineEdit)
        self.long.addItems(columns)

    @pyqtSlot()
    def add(self) -> None:
        c_1 = self.longLineEdit.text()
        c_2 = self.latLineEdit.text()
        if c_1 == '' or c_2 == '':
            self.m = Message(Messages.empty_field(self), self)
            self.m.show()
            return

        self.loading = Loading(self.addPushButton)
        self.loading.start()
        self.loading.show()

        self.c_t = PointToShpConvert(c_1, c_2, self.file, self.out_file, self)
        self.c_t.finished_signal.connect(lambda: (
            self.finish_signal.emit(),
            self.loading.stop(),
            self.loading.deleteLater()
        ))
        self.c_t.start()
