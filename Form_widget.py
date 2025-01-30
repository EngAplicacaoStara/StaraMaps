import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import QPoint, QRegExp, QSize, pyqtSlot, pyqtSignal, QModelIndex, QTimer
from PyQt5.QtGui import QColor, QRegExpValidator, QFocusEvent
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QLabel, QLineEdit, QApplication, QComboBox, QListWidget
from qgis.PyQt import QtWidgets, QtCore

from .qgisFuncs import TextInfoTest

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/Form.ui'), resource_suffix='')


class FloatComboBox(QComboBox):
    textSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super(FloatComboBox, self).__init__(parent)

        self.setStyleSheet('''
            QComboBox{
                border:1px solid rgb(240, 240, 240);
                border-radius: 3px;
                background-color: rgb(250, 250, 250);
                color: rgb(120, 120, 120);
            }
            
            QComboBox::drop-down{
                border: 0px
            }
            
            QComboBox::down-arrow{
                border:none;
                width: 20px;
                height: 20px;
                image: url(:/plugins/StaraMaps/down.png);
            
            }
            QComboBox::down-arrow:disabled{
                image: url(:/plugins/StaraMaps/down_disabled.png);
            }
            
            QComboBox:disabled{
                color: rgb(240, 240, 240);
            }
            
            QComboBox QAbstractItemView {
                  border: 2px solid darkgray;
                  selection-background-color: red;
                  min-width: 80px;
              }
        ''')

        self.setMaximumSize(QSize(20, 20))
        self._set_line_edit_in_use = None
        self.view().pressed.connect(self.handle_item_pressed)

    @pyqtSlot(QModelIndex)
    def handle_item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        self._set_line_edit_in_use.setFocus(True)
        self.textSelected.emit(item.text())
        self.setMinimumSize(QSize(20, 20))
        self.setMaximumSize(QSize(20, 20))
        # VERIFICAR AQUI
        self.move(QPoint(
            int(self._set_line_edit_in_use.x() + self._set_line_edit_in_use.width() - self.width() / 2),
            int(self._set_line_edit_in_use.y() + self.height() / 2)
        ))
        super(FloatComboBox, self).hidePopup()

    def focusOutEvent(self, e: QFocusEvent) -> None:
        self.setMinimumSize(QSize(20, 20))
        self.setMaximumSize(QSize(20, 20))

    def set_line_edit_in_use(self, obj):
        self._set_line_edit_in_use = obj


class FormWidget(QtWidgets.QWidget, FORM_CLASS):
    addSignal = QtCore.pyqtSignal(object, object, list)
    cancelSignal = QtCore.pyqtSignal()

    def __init__(self, item, file, project, parent=None):
        super(FormWidget, self).__init__(parent)
        self.setupUi(self)
        self.item = item
        self.file = file
        self.project = project
        self.lineedit = None
        self.tree_list = []
        self.messages = TextInfoTest()
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(lambda: self.addPushButton.setEnabled(True))
        self.init()

        self.proLabel.setText(self.tr("Proprietário(a) *"))
        self.farmLabel.setText(self.tr("Fazenda *"))
        self.talLabel.setText(self.tr("Talhão *"))
        self.anoRadioButton.setText(self.tr("Ano"))
        self.bordRadioButton.setText(self.tr("Bordadura..."))
        self.anoLabel.setText(self.tr("Ano *"))
        self.culLabel.setText(self.tr("Cultura *"))
        self.appTyLabel.setText(self.tr("Tipo de aplicação *"))
        self.cancelPushButton.setText(self.tr("Cancelar"))
        self.addPushButton.setText(self.tr("Adicionar"))

    def get_group_childrens(self, name, qtd):
        root = self.project.layerTreeRoot()
        group = [group for group in root.findGroups() if group.name() == name]
        if len(group) == 0:
            return []
        to_return = group[0].children()
        if qtd == 0:
            return [p.name() for p in to_return]

        while qtd:
            to_return = to_return[0].children()
            qtd -= 1

        return [p.name() for p in to_return]

    def list_item_clicked(self, item):
        if self.lineedit is not None:
            self.lineedit.setText(item.text())
            self.float_list_widget.hide()

    def init(self):

        self.float_list_widget = QListWidget(self)
        self.float_list_widget.itemClicked.connect(self.list_item_clicked)
        self.float_list_widget.hide()

        regex = QRegExp("[A-Za-záàâãéèêíïóôõöúçñÁÀÂÃÉÈÍÏÓÔÕÖÚÇÑ - 0-9]{0,30}")
        regex_only_num = QRegExp("[0-9]{4}")
        pro_validator = QRegExpValidator(regex, self.proLineEdit)
        farm_validator = QRegExpValidator(regex, self.farmLineEdit)
        tal_validator = QRegExpValidator(regex, self.talLineEdit)
        ano_validator = QRegExpValidator(regex_only_num, self.anoLineEdit)
        cul_validator = QRegExpValidator(regex, self.culLineEdit)
        app_vilidator = QRegExpValidator(regex, self.appTyLineEdit)
        bord_validator = QRegExpValidator(regex, self.bordLineEdit)
        line_validator = QRegExpValidator(regex, self.lineLineEdit)
        point_validator = QRegExpValidator(regex, self.pointLineEdit)

        self.proLineEdit.setValidator(pro_validator)
        self.proLineEdit.focusInEvent = self.line_edit_text_changes
        self.proLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.farmLineEdit.setValidator(farm_validator)
        self.farmLineEdit.focusInEvent = self.line_edit_text_changes
        self.farmLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.talLineEdit.setValidator(tal_validator)
        self.talLineEdit.focusInEvent = self.line_edit_text_changes
        self.talLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.anoLineEdit.setValidator(ano_validator)
        self.anoLineEdit.focusInEvent = self.line_edit_text_changes
        self.anoLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.culLineEdit.setValidator(cul_validator)
        self.culLineEdit.focusInEvent = self.line_edit_text_changes
        self.culLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.appTyLineEdit.setValidator(app_vilidator)
        self.appTyLineEdit.focusInEvent = self.line_edit_text_changes
        self.appTyLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.bordLineEdit.setValidator(bord_validator)
        self.bordLineEdit.focusInEvent = self.line_edit_text_changes
        self.bordLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.lineLineEdit.setValidator(line_validator)
        self.lineLineEdit.focusInEvent = self.line_edit_text_changes
        self.lineLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.pointLineEdit.setValidator(point_validator)
        self.pointLineEdit.focusInEvent = self.line_edit_text_changes
        self.pointLineEdit.textChanged[str].connect(self.line_edit_text_changes)

        self.effect = QGraphicsDropShadowEffect()
        self.effect.setBlurRadius(5.0)
        self.effect.setColor(QColor(0, 0, 0, 80))
        self.effect.setOffset(1.0)
        self.setGraphicsEffect(self.effect)

        self.m_direction = QtCore.Qt.Horizontal
        self.m_speed = 500
        self.m_animationtype = QtCore.QEasingCurve.OutCubic
        self.m_now = 0
        self.m_next = 0
        self.m_wrap = False
        self.m_pnow = QtCore.QPoint(0, 0)
        self.m_active = False

        self.anoRadioButton.clicked.connect(self.checkYearOrBord)
        self.bordRadioButton.clicked.connect(self.checkYearOrBord)

        self.bordRadioButtonEdit.clicked.connect(self.checkYearOptions)
        self.lineRadioButton.clicked.connect(self.checkYearOptions)
        self.pointRadioButton.clicked.connect(self.checkYearOptions)

        self.addPushButton.clicked.connect(self.addCheck)
        self.cancelPushButton.clicked.connect(self.cancelSignal.emit)

        # InfoLineEdit(self.messages.interpolate_info(), self.proLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.farmLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.talLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.anoLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.culLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.appTyLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.bordLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.lineLineEdit)
        # InfoLineEdit(self.messages.interpolate_info(), self.pointLineEdit)

    def line_edit_text_changes(self, text):

        widget = QApplication.focusWidget()
        self.lineedit = widget if type(widget) == QLineEdit else self.lineedit
        object_name = self.lineedit.objectName()
        print(object_name)

        root = self.project.layerTreeRoot()
        data = []

        if object_name == "proLineEdit":
            data = [ch.name() for ch in root.children()]
        elif object_name == "farmLineEdit":

            data = self.get_group_childrens(self.proLineEdit.text(), 0)
        elif object_name == "talLineEdit":

            data = self.get_group_childrens(self.proLineEdit.text(), 1)
        # size = self.get_tree_size(root.findGroup(self.proLineEdit.text()))
        # print(f"{self.proLineEdit.text()} : {size}")
        if self.anoRadioButton.isChecked():
            if object_name == "anoLineEdit":
                # data = self.rec_get_childrens(root, self.talLineEdit.text())
                data = self.get_group_childrens(self.proLineEdit.text(), 2)
            elif object_name == "culLineEdit":
                # data = self.rec_get_childrens(root, self.anoLineEdit.text())
                data = self.get_group_childrens(self.proLineEdit.text(), 3)
            elif object_name == "appTyLineEdit":
                # data = self.rec_get_childrens(root, self.culLineEdit.text())
                data = self.get_group_childrens(self.proLineEdit.text(), 4)
        else:
            if object_name == "bordLineEdit":
                # data = self.rec_get_childrens(root, self.talLineEdit.text())
                data = self.get_group_childrens(self.proLineEdit.text(), 2)

            elif object_name == "lineLineEdit":
                # data = self.rec_get_childrens(root, self.talLineEdit.text())
                data = self.get_group_childrens(self.proLineEdit.text(), 2)
            elif object_name == "pointLineEdit":
                # data = self.rec_get_childrens(root, self.talLineEdit.text())
                data = self.get_group_childrens(self.proLineEdit.text(), 2)

        # self.float_combobox.setParent(lineedit)

        self.float_list_widget.setParent(self.lineedit.parent())
        self.show_options(data)

    def get_tree_size(self, root):
        if root is None:
            return 0

        max_size = 0
        for child in root.children():
            size = self.get_tree_size(child)
            if size > max_size:
                max_size = size

        return max_size + 1

    def show_options(self, nodes):

        self.float_list_widget.clear()

        if nodes:

            if not self.float_list_widget.isVisible():
                self.float_list_widget.show()
            for fld in nodes:
                self.float_list_widget.addItem(fld)
        else:
            self.float_list_widget.hide()

        self.adjust_list_widget_height()

        self.float_list_widget.move(self.lineedit.x() + self.lineedit.cursorPosition(),
                                    self.lineedit.y() + self.lineedit.height())

        if self.float_list_widget.y() + self.float_list_widget.height() > self.lineedit.parent().y() + self.lineedit.parent().height():
            self.float_list_widget.move(self.lineedit.x() + self.lineedit.width() - self.float_list_widget.width(),
                                        self.lineedit.y() + self.lineedit.height() - self.float_list_widget.height())

    def adjust_list_widget_height(self):
        # Altura de cada item no QListWidget (pode variar conforme o estilo)
        item_height = self.float_list_widget.sizeHintForRow(0)

        # Altura total = altura de cada item * número de itens
        total_height = item_height * self.float_list_widget.count()

        total_height += 5

        # Defina a altura máxima
        self.float_list_widget.setFixedHeight(total_height)

    @pyqtSlot(str)
    def text_from_float_combobox(self, text):
        line_edit = QApplication.focusWidget()
        line_edit.setText(text)

    # combobox.parent().parent().set_line_edit_in_use.setText(text)

    def addCheck(self):
        listToAnim = []
        checkBoxEditEmpty = False
        infoToSend = []
        if self.proLineEdit.text() == "":
            listToAnim.append(self.proLabel)
            self.proLineEdit.setEnabled(False)
        else:
            infoToSend.append(self.proLineEdit.text())

        if self.farmLineEdit.text() == "":
            listToAnim.append(self.farmLabel)
            self.farmLineEdit.setEnabled(False)
        else:
            infoToSend.append(self.farmLineEdit.text())

        if self.talLineEdit.text() == "":
            listToAnim.append(self.talLabel)
            self.talLineEdit.setEnabled(False)

        else:
            infoToSend.append(self.talLineEdit.text())

        # ANO CHECK
        if self.anoRadioButton.isChecked():
            if self.anoLineEdit.text() == "":
                listToAnim.append(self.anoLabel)
                self.anoLineEdit.setEnabled(False)
            else:
                infoToSend.append(self.anoLineEdit.text())

            if self.culLineEdit.text() == "":
                listToAnim.append(self.culLabel)
                self.culLineEdit.setEnabled(False)

            else:
                infoToSend.append(self.culLineEdit.text())

            if self.appTyLineEdit.text() == "":
                listToAnim.append(self.appTyLabel)
                self.appTyLineEdit.setEnabled(False)
            else:
                infoToSend.append(self.appTyLineEdit.text())

        else:
            newStyle = '''
                        QLineEdit{
                            border: none;
                            border-bottom: 1px solid;
                            background-color: rgb(250, 250, 250);
                            border-bottom-color: rgb(255, 0, 0);
                            font: 10pt url(:/plugins/StaraMaps/Roboto-Regular.ttf);
                        }
                        
                    '''
            if self.bordRadioButtonEdit.isChecked():
                if self.bordLineEdit.text() == "":
                    self.bordLineEdit.setStyleSheet(newStyle)
                    checkBoxEditEmpty = True
                else:
                    infoToSend.append(self.bordLineEdit.text())

            elif self.lineRadioButton.isChecked():
                if self.lineLineEdit.text() == "":
                    self.lineLineEdit.setStyleSheet(newStyle)
                    checkBoxEditEmpty = True
                else:
                    infoToSend.append(self.lineLineEdit.text())

            else:
                if self.pointLineEdit.text() == "":
                    self.pointLineEdit.setStyleSheet(newStyle)
                    checkBoxEditEmpty = True
                else:
                    infoToSend.append(self.pointLineEdit.text())

        '''
        Caso somente um LineEdit das opções checbox e line edit ao lado estiver vazia
        acontece a mundaça de style, porém não é perceptível pois não existe labels para animar.
        '''
        # all right
        if self.bordRadioButton.isChecked():
            if not listToAnim and checkBoxEditEmpty == False:
                self.addSignal.emit(self.item, self.file, infoToSend)
                return
        else:
            if not listToAnim:
                self.addSignal.emit(self.item, self.file, infoToSend)
                return

        for l in listToAnim:
            l.setEnabled(False)

        self.anim_group = QtCore.QParallelAnimationGroup(
            self, finished=self.animGroupBack
        )
        self.anim_group.stateChanged.connect(self.on_anim_group_state_changed)

        self.anim_group.setDirection(QtCore.QAbstractAnimation.Forward)
        for lineW in listToAnim:
            startValue = lineW.pos()
            endValue = QPoint(startValue.x(), startValue.y() + 8)
            animation = QtCore.QPropertyAnimation(
                lineW,
                b"pos",
                easingCurve=self.m_animationtype,
                duration=200,
                startValue=startValue,
                endValue=endValue,
            )

            self.anim_group.addAnimation(animation)

        self.anim_group.start()
        listToAnim.clear()

    def on_anim_group_state_changed(self, state):

        if state == QtCore.QAbstractAnimation.Running:
            self.addPushButton.setEnabled(False)
        elif state == QtCore.QAbstractAnimation.Stopped:
            self.delay_timer.start(1000)

    def animGroupBack(self):
        self.anim_group.disconnect()
        self.anim_group.finished.connect(self.animGroupBackLabelStyle)
        self.anim_group.setDirection(QtCore.QAbstractAnimation.Backward)
        self.anim_group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def animGroupBackLabelStyle(self):
        labels = self.frame_2.findChildren(QLabel)
        lineEdits = self.frame_2.findChildren(QLineEdit)

        for label in labels:
            label.setEnabled(True)

        listBordCheck = ["bordLineEdit", "lineLineEdit", "pointLineEdit"]
        if self.anoRadioButton.isChecked():
            for lineE in lineEdits:
                if lineE.objectName() not in listBordCheck:
                    lineE.setEnabled(True)

        else:
            style = '''
                        QLineEdit{
                            border: none;
                            border-bottom: 1px solid;
                            border-bottom-color: rgb(235, 235, 235);
                            background-color: rgb(250, 250, 250);
                            font: 10pt url(:/plugins/StaraMaps/Roboto-Regular.ttf);
                        }
 
                        QLineEdit::hover{
                            border-bottom: 2px solid;
                            border-bottom-color: rgb(225, 225, 225);
                        }

                        QLineEdit:focus{
                            border-bottom-color: rgb(243, 116, 53);
                        }

                        QLineEdit:disabled{
                            background-color: rgb(230, 230, 230);
                        }
                    '''
            for lineE in lineEdits:
                if lineE.objectName() not in listBordCheck:
                    lineE.setEnabled(True)
                elif lineE.objectName() == listBordCheck[0] and self.bordRadioButtonEdit.isChecked():
                    lineE.setStyleSheet(style)
                elif lineE.objectName() == listBordCheck[1] and self.lineRadioButton.isChecked():
                    lineE.setStyleSheet(style)
                elif lineE.objectName() == listBordCheck[2] and self.pointRadioButton.isChecked():
                    lineE.setStyleSheet(style)

    def checkYearOptions(self):
        if self.bordRadioButtonEdit.isChecked():
            self.bordLineEdit.setEnabled(True)
            self.bordRadioButtonEdit.setText(self.tr("Bordadura *"))
        else:
            self.bordLineEdit.setEnabled(False)
            self.bordRadioButtonEdit.setText(self.tr("Bordadura"))

        if self.lineRadioButton.isChecked():
            self.lineLineEdit.setEnabled(True)
            self.lineRadioButton.setText(self.tr("Linhas *"))
        else:
            self.lineLineEdit.setEnabled(False)
            self.lineRadioButton.setText(self.tr("Linhas"))

        if self.pointRadioButton.isChecked():
            self.pointLineEdit.setEnabled(True)
            self.pointRadioButton.setText(self.tr("Pontos *"))
        else:
            self.pointLineEdit.setEnabled(False)
            self.pointRadioButton.setText(self.tr("Pontos"))

    def checkYearOrBord(self):
        if self.anoRadioButton.isChecked():
            self.slideInPrev()
        else:
            self.slideInNext()

    def setDirection(self, direction):
        self.m_direction = direction

    def setSpeed(self, speed):
        self.m_speed = speed

    def setAnimation(self, animationtype):
        self.m_animationtype = animationtype

    def setWrap(self, wrap):
        self.m_wrap = wrap

    @QtCore.pyqtSlot()
    def slideInPrev(self):
        now = self.stackedWidget.currentIndex()
        if self.m_wrap or now > 0:
            self.slideInIdx(now - 1)

    @QtCore.pyqtSlot()
    def slideInNext(self):
        now = self.stackedWidget.currentIndex()
        if self.m_wrap or now < (self.stackedWidget.count() - 1):
            self.slideInIdx(now + 1)

    def slideInIdx(self, idx):
        if idx > (self.stackedWidget.count() - 1):
            idx = idx % self.stackedWidget.count()
        elif idx < 0:
            idx = (idx + self.stackedWidget.count()) % self.stackedWidget.count()
        self.slideInWgt(self.stackedWidget.widget(idx))

    def slideInWgt(self, newwidget):
        if self.m_active:
            return

        self.m_active = True
        self.anoRadioButton.setEnabled(False)
        self.bordRadioButton.setEnabled(False)

        _now = self.stackedWidget.currentIndex()
        _next = self.stackedWidget.indexOf(newwidget)

        if _now == _next:
            self.m_active = False
            return

        offsetx, offsety = self.stackedWidget.frameRect().width(), self.stackedWidget.frameRect().height()
        self.stackedWidget.widget(_next).setGeometry(self.stackedWidget.frameRect())

        if not self.m_direction == QtCore.Qt.Horizontal:
            if _now < _next:
                offsetx, offsety = 0, -offsety
            else:
                offsetx = 0
        else:
            if _now < _next:
                offsetx, offsety = -offsetx, 0
            else:
                offsety = 0

        pnext = self.stackedWidget.widget(_next).pos()
        pnow = self.stackedWidget.widget(_now).pos()
        self.m_pnow = pnow

        offset = QtCore.QPoint(offsetx, offsety)
        self.stackedWidget.widget(_next).move(pnext - offset)
        self.stackedWidget.widget(_next).show()
        self.stackedWidget.widget(_next).raise_()

        anim_group = QtCore.QParallelAnimationGroup(
            self, finished=self.animationDoneSlot
        )

        for index, start, end in zip(
                (_now, _next), (pnow, pnext - offset), (pnow + offset, pnext)
        ):
            animation = QtCore.QPropertyAnimation(
                self.stackedWidget.widget(index),
                b"pos",
                duration=self.m_speed,
                easingCurve=self.m_animationtype,
                startValue=start,
                endValue=end,
            )
            anim_group.addAnimation(animation)

        self.m_next = _next
        self.m_now = _now
        self.m_active = True
        anim_group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    @QtCore.pyqtSlot()
    def animationDoneSlot(self):
        self.stackedWidget.setCurrentIndex(self.m_next)
        self.stackedWidget.widget(self.m_now).hide()
        self.stackedWidget.widget(self.m_now).move(self.m_pnow)
        self.m_active = False
        self.anoRadioButton.setEnabled(True)
        self.bordRadioButton.setEnabled(True)
