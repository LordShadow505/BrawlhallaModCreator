from typing import List, Tuple, Callable

from PySide6.QtGui import QFont, QCursor, Qt
from PySide6.QtWidgets import QWidget, QPushButton
from ..ui_sources.ui_buttons_dialog import Ui_ButtonsDialog


class ButtonsDialog(QWidget):
    font = QFont()
    font.setFamilies([u"Roboto Medium"])
    font.setPointSize(10)
    font.setBold(False)

    maxContentHeight = 300
    customMinWidth = None
    customMaxHeight = None

    def __init__(self, window):
        super().__init__()

        self.ui = Ui_ButtonsDialog()
        self.ui.setupUi(self)
        self.ui.content.setWordWrap(True)

        self.mainWindow = window

        self.ui.content.setOpenExternalLinks(True)
        self.ui.content.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)

        #self.buttons: List[Tuple[str, Callable]] = []
        self.buttons: List[QPushButton] = []

    def setDialogSize(self, min_width=None, max_height=None):
        self.customMinWidth = min_width
        self.customMaxHeight = max_height

    def resetDialogSize(self):
        self.customMinWidth = None
        self.customMaxHeight = None
        self.ui.dialogBackground.setMinimumWidth(500)

    def deleteButtons(self):
        for button in self.buttons:
            self.ui.buttons.layout().removeWidget(button)
            button.setParent(None)
            button.deleteLater()
            del button

        self.buttons.clear()

    def addButton(self, text: str, function: Callable):
        button = QPushButton()
        button.setFont(self.font)
        button.setCursor(QCursor(Qt.PointingHandCursor))
        button.setText(text)
        button.setParent(self.ui.buttons)
        button.clicked.connect(function)
        self.ui.buttons.layout().addWidget(button)
        self.buttons.append(button)

    def setButtons(self, buttons: List[Tuple[str, Callable]]):
        self.deleteButtons()
        for button in buttons:
            self.addButton(*button)

    def onResize(self):
        self.setGeometry(0, 0, self.mainWindow.width(), self.mainWindow.height())

    def isShown(self):
        return self.parent() is not None

    def show(self):
        if self.parent() is None:
            self.setParent(self.mainWindow)
            self.onResize()
            super().show()
            self.raise_()

            if self.customMinWidth:
                self.ui.dialogBackground.setMinimumWidth(self.customMinWidth)
            else:
                self.ui.dialogBackground.setMinimumWidth(500)

            target_max_height = self.customMaxHeight if self.customMaxHeight is not None else self.maxContentHeight

            if self.ui.content.height() <= target_max_height:
                self.ui.scrollLabel.setMinimumHeight(self.ui.content.height())
                self.ui.scrollLabel.setMaximumHeight(self.ui.content.height())
            else:
                self.ui.scrollLabel.setMinimumHeight(target_max_height)
                self.ui.scrollLabel.setMaximumHeight(target_max_height)

    def hide(self):
        if self.parent() is not None:
            super().hide()
            self.setParent(None)
            self.resetDialogSize()

    def setContent(self, content: str):
        self.ui.content.setText(content)

    def setTitle(self, title: str):
        self.ui.title.setText(title)
