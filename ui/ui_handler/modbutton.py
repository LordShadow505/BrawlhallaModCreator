import re

from PySide6.QtWidgets import QWidget, QScrollArea, QPushButton
from PySide6.QtGui import QFontMetrics, Qt, QPixmap, QIcon, QCursor
from PySide6.QtCore import QEvent, QSize

from .modclass import ModClass

from ..ui_sources.ui_mod_button import Ui_ModButton


class ModButton(QWidget):
    buttons = []

    def __init__(self, modClass: ModClass, method):
        self.pressed = False
        self.modClass = modClass
        self.method = method

        super().__init__()

        self.ui = Ui_ModButton()
        self.ui.setupUi(self)

        # Open Folder Button
        self.ui.openFolderBtn = QPushButton(self.ui.background)
        self.ui.openFolderBtn.setObjectName(u"openFolderBtn")
        self.ui.openFolderBtn.setMinimumSize(QSize(24, 24))
        self.ui.openFolderBtn.setMaximumSize(QSize(24, 24))
        self.ui.openFolderBtn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ui.openFolderBtn.setStyleSheet(u"QPushButton { border: none; background-color: transparent; }")
        icon = QIcon()
        icon.addFile(u":/icons/resources/icons/OpenModsFolder.png", QSize(), QIcon.Normal, QIcon.Off)
        self.ui.openFolderBtn.setIcon(icon)
        self.ui.openFolderBtn.setIconSize(QSize(20, 20))
        self.ui.openFolderBtn.setToolTip("Open mod source folder")
        self.ui.openFolderBtn.clicked.connect(self.openFolder)

        # Layout adjustments
        self.ui.horizontalLayout_2.setContentsMargins(10, 0, 10, 0)
        self.ui.horizontalLayout_2.setSpacing(8)
        self.ui.horizontalLayout_2.insertWidget(0, self.ui.openFolderBtn)
        
        # Stability: Ensure modInfo expands while others stay fixed
        self.ui.horizontalLayout_2.setStretch(0, 0)
        self.ui.horizontalLayout_2.setStretch(1, 1)
        self.ui.horizontalLayout_2.setStretch(2, 0)

        self.updateData()

        self.ui.background.installEventFilter(self)

        self.buttons.append(self)

    def updateData(self):
        self.ui.modName.setText(self.modClass.name)
        self.ui.gameVersion.setText(f"[{self.modClass.gameVersion}]")
        self.ui.modAuthor.setText("Author: " + self.modClass.author)
        if self.modClass.currentVersion:
            gameVersionColor = "#43C15F"
        else:
            gameVersionColor = "#3FAED1"
        self.ui.gameVersion.setStyleSheet(f"color: {gameVersionColor}")

        if self.modClass.installed and self.modClass.modFileExist:
            self.ui.modState.setPixmap(QPixmap(u":/icons/resources/icons/Installed.png"))
        elif self.modClass.installed:
            self.ui.modState.setPixmap(QPixmap(u":/icons/resources/icons/GhostInstalled.png"))
        else:
            self.ui.modState.setPixmap(QPixmap(u":/icons/resources/icons/NotInstalled.png"))

    def onParentResize(self):
        parent = self
        while True:
            parent = parent.parent()
            if type(parent) == QScrollArea:
                break

            if parent is None:
                return False

        versionWidth = self.ui.gameVersion.fontMetrics().boundingRect(self.ui.gameVersion.text()).width()

        elided = self.ui.modName.fontMetrics().elidedText(self.modClass.name,
                                                          Qt.ElideRight, parent.width() - 100 - versionWidth)
        self.ui.modName.setText(elided)
        self.ui.modName.setMaximumWidth(parent.width() - 100)

        elided = self.ui.modAuthor.fontMetrics().elidedText(f"Author: {self.modClass.author}",
                                                            Qt.ElideRight, parent.width() - 90)
        self.ui.modAuthor.setText(elided)
        self.ui.modAuthor.setMaximumWidth(parent.width() - 90)

    def select(self):
        if self.pressed:
            pass
        else:
            for button in self.buttons:
                if button.pressed:
                    button.pressed = False
                    styleSheet = button.ui.background.styleSheet()
                    bgColor = re.findall(r"background-color: #FF(.+);", styleSheet)[0]
                    button.ui.background.setStyleSheet(
                        styleSheet.replace(f"#FF{bgColor}", f"#00{bgColor}").replace(f"#FE{bgColor}", f"#77{bgColor}"))

            self.pressed = True
            ss = self.ui.background.styleSheet()
            bgColor = re.findall(r"background-color: #00(.+);", ss)[0]
            self.ui.background.setStyleSheet(
                ss.replace(f"#00{bgColor}", f"#FF{bgColor}").replace(f"#77{bgColor}", f"#FE{bgColor}"))

            self.method(self.modClass)

    def openFolder(self, event=None):
        import os
        if self.modClass.modSourcesPath and os.path.exists(self.modClass.modSourcesPath):
            os.startfile(self.modClass.modSourcesPath)

    def remove(self):
        self.layout().removeWidget(self)
        self.setParent(None)

    def restore(self, frame):
        self.setParent(frame)
        frame.layout().addWidget(self)

    def eventFilter(self, qobject: QWidget, event):
        if event.type() == QEvent.MouseButtonPress:
            self.select()

        return False

    def cleanup(self):
        if self in self.buttons:
            self.buttons.remove(self)
        self.setParent(None)
        self.deleteLater()
