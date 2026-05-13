import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QIcon

from ..utils.config import CreatorConfig


class SettingsFrame(QFrame):
    def __init__(self, saveCallback=None, openCacheMethod=None, clearCacheMethod=None,
                 bhPath="", modsPath="", modsSourcesPath="", cacheSize=""):
        super().__init__()
        self.config = CreatorConfig()
        self.saveCallback = saveCallback
        self.openCacheMethod = openCacheMethod
        self.clearCacheMethod = clearCacheMethod
        self.bhPath = bhPath
        self.modsPath = modsPath
        self.modsSourcesPath = modsSourcesPath
        self.cacheSize = cacheSize
        self.hasUnsavedChanges = False
        
        self.setObjectName("SettingsFrame")
        self.setStyleSheet("#SettingsFrame { background-color: #151518; }")

        self.scrollLayout = QVBoxLayout(self)
        self.scrollLayout.setContentsMargins(0, 0, 0, 0)
        
        from PySide6.QtWidgets import QScrollArea, QWidget
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: transparent; 
            }
            QScrollBar:vertical {         
                border: none;
                background: #2B2C32;
                width: 7px;
                margin: 0 0 0 0;
                border-radius: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #616161;
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #A1A1A1;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #717171;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        self.scrollContent = QWidget()
        self.scrollContent.setStyleSheet("background-color: transparent;")
        self.mainLayout = QVBoxLayout(self.scrollContent)
        self.mainLayout.setContentsMargins(40, 20, 40, 40)
        self.mainLayout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.mainLayout.setSpacing(24)
        
        self.scrollArea.setWidget(self.scrollContent)
        self.scrollLayout.addWidget(self.scrollArea)

        # ── Card 1: Mod Template ──────────────────────────────────
        self.card1 = self._createCard("Mod Template Settings", "#7E57C2")
        self.authorEdit      = self._addRow(self.card1, "Default Author:",       self.config.defaultAuthor)
        self.gameVersionEdit = self._addRow(self.card1, "Default Game Version:", self.config.defaultGameVersion)
        self.modVersionEdit  = self._addRow(self.card1, "Default Mod Version:",  self.config.defaultModVersion)
        self.mainLayout.addWidget(self.card1)

        # ── Card 2: Paths ─────────────────────────────────────────
        self.card2 = self._createCard("Game Path Settings", "#42A5F5")
        self.brawlhallaPathEdit = self._addPathRow(self.card2, "Brawlhalla Path:", self.bhPath)
        self.modsPathEdit       = self._addPathRow(self.card2, "Mods Path:",       self.modsPath)
        self.modsSourcesPathEdit = self._addPathRow(self.card2, "Mods Sources Path:", self.modsSourcesPath)
        
        pathWarning = QLabel("Warning: Only change paths if you know what you're doing!")
        pathWarning.setStyleSheet("color: #EF5350; font-size: 8pt; font-style: italic; margin-top: 4px;")
        self.card2.layout().addWidget(pathWarning)
        
        self.mainLayout.addWidget(self.card2)

        # ── Card 3: Cache ─────────────────────────────────────────
        self.card3 = self._createCard("Application Cache", "#EF5350")
        
        cacheInfoLayout = QHBoxLayout()
        self.cacheSizeLabel = QLabel(f"Total Cache Size: {self.cacheSize}")
        self.cacheSizeLabel.setStyleSheet("color: #bbbbbb; font-size: 9pt; margin-bottom: 8px;")
        cacheInfoLayout.addWidget(self.cacheSizeLabel)
        self.card3.layout().addLayout(cacheInfoLayout)
        
        cacheButtonsLayout = QHBoxLayout()
        cacheButtonsLayout.setSpacing(12)
        
        self.openCacheBtn = QPushButton("Open Cache Folder")
        self.openCacheBtn.setFixedSize(QSize(180, 36))
        self.openCacheBtn.setCursor(Qt.PointingHandCursor)
        self.openCacheBtn.setStyleSheet(self._getButtonStyle("#42A5F5"))
        self.openCacheBtn.clicked.connect(self.openCacheMethod)
        
        self.clearCacheBtn = QPushButton(" Clear Cache")
        self.clearCacheBtn.setFixedSize(QSize(180, 36))
        self.clearCacheBtn.setCursor(Qt.PointingHandCursor)
        self.clearCacheBtn.setIcon(QIcon(":/icons/resources/icons/UninstallAllMods.png")) # Using uninstall all icon as trash icon
        self.clearCacheBtn.setIconSize(QSize(16, 16))
        self.clearCacheBtn.setStyleSheet(self._getButtonStyle("#EF5350"))
        self.clearCacheBtn.clicked.connect(self.clearCacheMethod)
        
        cacheButtonsLayout.addWidget(self.openCacheBtn)
        cacheButtonsLayout.addWidget(self.clearCacheBtn)
        cacheButtonsLayout.addStretch()
        
        self.card3.layout().addLayout(cacheButtonsLayout)
        self.mainLayout.addWidget(self.card3)

        # ── Save button ───────────────────────────────────────────
        self.saveButton = QPushButton("Save Settings")
        self.saveButton.setFixedSize(QSize(180, 40))
        self.saveButton.setCursor(Qt.PointingHandCursor)
        self._setSaveButtonStyle(saved=False)
        self.saveButton.clicked.connect(self.saveSettings)
        self.mainLayout.addWidget(self.saveButton, alignment=Qt.AlignCenter)

    def _createCard(self, title: str, color: str) -> QFrame:
        card = QFrame()
        card.setFixedWidth(520)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #303136;
                border-left: 4px solid {color};
                border-radius: 0px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        titleLabel = QLabel(title)
        titleFont = QFont()
        titleFont.setPointSize(12)
        titleFont.setBold(True)
        titleLabel.setFont(titleFont)
        titleLabel.setStyleSheet(f"color: {color}; margin-bottom: 4px;")
        layout.addWidget(titleLabel)
        
        return card

    def _addRow(self, card: QFrame, labelText: str, initialValue: str) -> QLineEdit:
        row = QHBoxLayout()
        row.setSpacing(12)

        label = QLabel(labelText)
        label.setFixedWidth(160)
        label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        label.setStyleSheet("color: #aaaaaa; font-size: 9pt;")
        row.addWidget(label)

        edit = QLineEdit()
        edit.setText(initialValue)
        edit.setMinimumHeight(32)
        edit.setStyleSheet("""
            QLineEdit {
                background-color: #151518;
                color: #eeeeee;
                border: 1px solid #404146;
                border-radius: 4px;
                padding-left: 10px;
                font-size: 9pt;
            }
            QLineEdit:focus {
                border: 1px solid #7E57C2;
            }
        """)
        edit.textChanged.connect(lambda: setattr(self, 'hasUnsavedChanges', True))
        row.addWidget(edit)

        card.layout().addLayout(row)
        return edit

    def _addPathRow(self, card: QFrame, labelText: str, initialValue: str) -> QLineEdit:
        from PySide6.QtWidgets import QFileDialog

        row = QHBoxLayout()
        row.setSpacing(12)

        label = QLabel(labelText)
        label.setFixedWidth(160)
        label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        label.setStyleSheet("color: #aaaaaa; font-size: 9pt;")
        row.addWidget(label)

        edit = QLineEdit()
        edit.setText(initialValue)
        edit.setCursorPosition(0)
        edit.setReadOnly(True)
        edit.setMinimumHeight(32)
        edit.setStyleSheet("""
            QLineEdit {
                background-color: #1D1E20;
                color: #bbbbbb;
                border: 1px solid #404146;
                border-radius: 4px;
                padding-left: 10px;
                font-size: 9pt;
            }
        """)
        row.addWidget(edit)

        browseBtn = QPushButton()
        browseBtn.setFixedSize(QSize(32, 32))
        browseBtn.setCursor(Qt.PointingHandCursor)
        browseBtn.setIcon(QIcon(":/icons/resources/icons/OpenModsFolder.png"))
        browseBtn.setIconSize(QSize(18, 18))
        browseBtn.setStyleSheet("""
            QPushButton {
                background-color: #404146;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #505156; }
        """)
        
        def browse():
            dir_path = QFileDialog.getExistingDirectory(self, "Select Folder", edit.text() if os.path.exists(edit.text()) else "")
            if dir_path:
                edit.setText(dir_path)
                edit.setCursorPosition(0)
                self.hasUnsavedChanges = True
        
        browseBtn.clicked.connect(browse)
        row.addWidget(browseBtn)

        card.layout().addLayout(row)
        return edit

    def _getButtonStyle(self, color: str):
        return f"""
            QPushButton {{
                background-color: {color};
                color: #eeeeee;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{ opacity: 0.8; }}
        """

    def _setSaveButtonStyle(self, saved: bool):
        if saved:
            bg, hover, pressed = "#2ecc71", "#27ae60", "#1e8449"
        else:
            bg, hover, pressed = "#7E57C2", "#9575CD", "#673AB7"
        self.saveButton.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: #eeeeee;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {pressed}; }}
        """)

    def saveSettings(self):
        self.config.defaultAuthor      = self.authorEdit.text()
        self.config.defaultGameVersion = self.gameVersionEdit.text()
        self.config.defaultModVersion  = self.modVersionEdit.text()
        
        bh_path = self.brawlhallaPathEdit.text().strip()
        if bh_path in ["Default (Steam)", ""]:
            self.config.brawlhallaPath = ""
        else:
            self.config.brawlhallaPath = bh_path

        m_path = self.modsPathEdit.text().strip()
        if m_path in ["Default", ""]:
            self.config.modsPath = ""
        else:
            self.config.modsPath = m_path

        ms_path = self.modsSourcesPathEdit.text().strip()
        if ms_path in ["Default", ""]:
            self.config.modsSourcesPath = ""
        else:
            self.config.modsSourcesPath = ms_path

        if self.saveCallback:
            self.saveCallback()

        self.hasUnsavedChanges = False
        self.saveButton.setText("Settings Saved!")
        self._setSaveButtonStyle(saved=True)
        QTimer.singleShot(2000, self._resetSaveButton)

    def _resetSaveButton(self):
        self.saveButton.setText("Save Settings")
        self._setSaveButtonStyle(saved=False)
