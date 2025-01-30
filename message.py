from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QObject
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QGraphicsOpacityEffect


class Messages(QObject):

    def empty_field(self):
        return self.tr("Preencha todos os campos.")

    def only_numeric(self):
        return self.tr("O valor do campo não pode") + "\n" + self.tr("ser só numérico.")


class Message(QFrame):
    def __init__(self, text, parent=None):
        super(Message, self).__init__(parent)
        self.text = text
        self.w = 250
        self.h = 50
        self.init()
        self.resize_to_parent()

    def resize_to_parent(self):
        self.resize(QSize(self.w, self.h))

        x = int(self.parent().width() / 2 - self.width() / 2)
        # y = int(self.parent().height() / 2 - self.height() / 2)

        self.move(x, 10)

    def init(self) -> None:
        effect = QGraphicsOpacityEffect(self, opacity=1.0)
        self.setGraphicsEffect(effect)

        self.ani = QPropertyAnimation(self, b"opacity")
        self.ani.setTargetObject(effect)
        self.ani.setDuration(10000)
        self.ani.setStartValue(1)
        self.ani.setEndValue(0)
        self.ani.setEasingCurve(QEasingCurve.OutBack)
        self.setStyleSheet('''
             QFrame{
            background-color: transparent;
        }
        ''')

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet('''
            QLabel{
                background-color: rgba(255, 0, 0);
                color: white;
                border-radius: 5px;
            }
        ''')
        self.label.setText(self.text)
        self.layout.addWidget(self.label)

        self.setLayout(self.layout)
        self.ani.finished.connect(lambda: (
            self.deleteLater()
        ))
        self.ani.start(QPropertyAnimation.DeleteWhenStopped)
