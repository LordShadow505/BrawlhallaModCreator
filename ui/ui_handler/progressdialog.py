from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt

from ..ui_sources.ui_progress_dialog import Ui_ProgressDialog


class ProgressDialog(QWidget):
    def __init__(self, window):
        super().__init__()

        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)

        self.mainWindow = window

        # Skin Warning
        self.skinWarning = QLabel("Remember that any existing skin mod requires a PAID skin, check the REQUIREMENTS section in gamebanana to find out which skin it replaces")
        self.skinWarning.setWordWrap(True)
        self.skinWarning.setAlignment(Qt.AlignCenter)
        self.skinWarning.setStyleSheet("color: #FF5252; font-size: 10px; font-weight: bold; margin-top: 5px;")
        self.ui.verticalLayout.addWidget(self.skinWarning)
        # self.ui.content.setWordWrap(True) # Removed to keep progress on one line

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

    def hide(self):
        if self.parent() is not None:
            super().hide()
            self.setParent(None)
            self.setValue(self.ui.progressBar.minimum())

    def removeContent(self):
        self.ui.content.setParent(None)

    def addContent(self):
        self.ui.content.setParent(self.ui.dialogBackground)

    def setMinimum(self, value: int):
        self.ui.progressBar.setMinimum(value)

    def setMaximum(self, value: int):
        self.ui.progressBar.setMaximum(value)

    def setValue(self, value: int):
        self.ui.progressBar.setValue(value)

    def addValue(self):
        self.ui.progressBar.setValue(self.ui.progressBar.value() + 1)

    def setTitle(self, title: str):
        self.ui.title.setText(title)

    def setContent(self, content: str):
        if self.ui.content.parent() is None:
            self.addContent()

        self.ui.content.setText(content)
