from pathlib import Path
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QMovie, QFont, QFontDatabase
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame

from ..ui_sources.ui_loading import Ui_Loading


class Loading(QWidget):
    def __init__(self, is_creator: bool = True):
        super().__init__()
        self.is_creator = is_creator
        self.accent_color = "#50c678" if is_creator else "#3e9cff"
        self.pending_color = "#72757d"
        self.error_color = "#ff4d4d"

        self.ui = Ui_Loading()
        self.ui.setupUi(self)

        # Hide default label
        self.ui.label.hide()

        # Perfectly center all parent and child layouts
        self.ui.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.ui.verticalLayout.setSpacing(0)
        self.ui.verticalLayout.setAlignment(Qt.AlignCenter)

        self.ui.loadingFrame.setStyleSheet("background: transparent; border: none;")
        self.ui.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.ui.verticalLayout_2.setSpacing(14)
        self.ui.verticalLayout_2.setAlignment(Qt.AlignCenter)

        # Load Bespoke font
        font_id = QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Bespoke/Bespoke.ttf")
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        font_family = families[0] if families else "BMG Bespoke Sans Bold"
        self.step_font = QFont(font_family, 11)

        # Smooth GIF movie rendering (Centered)
        self.movie = QMovie(":/icons/resources/icons/Loading.gif")
        self.ui.anim.setFixedSize(192, 192)
        self.ui.anim.setScaledContents(False)
        self.ui.anim.setAlignment(Qt.AlignCenter)
        self.ui.verticalLayout_2.setAlignment(self.ui.anim, Qt.AlignCenter)

        def _on_frame(frame_num=0):
            pix = self.movie.currentPixmap()
            if not pix.isNull():
                scaled = pix.scaled(192, 192, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.ui.anim.setPixmap(scaled)

        self.movie.frameChanged.connect(_on_frame)

        # Step labels container (Centered)
        self.stepsContainer = QFrame(self.ui.loadingFrame)
        self.stepsContainer.setStyleSheet("background: transparent; border: none;")
        self.stepsLayout = QVBoxLayout(self.stepsContainer)
        self.stepsLayout.setContentsMargins(0, 0, 0, 0)
        self.stepsLayout.setSpacing(6)
        self.stepsLayout.setAlignment(Qt.AlignCenter)

        self.core_title = "Loading Mod Creator Core" if is_creator else "Loading Mod Loader Core"
        self.step_texts = [
            "Client Launched",
            "Connection to GameBanana complete",
            self.core_title,
            "Loading mods",
            "Happy Modding!"
        ]

        self.step_labels = []
        for text in self.step_texts:
            lbl = QLabel(text, self.stepsContainer)
            lbl.setFont(self.step_font)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {self.pending_color}; background: transparent;")
            self.stepsLayout.addWidget(lbl, 0, Qt.AlignCenter)
            self.step_labels.append(lbl)

        self.ui.verticalLayout_2.addWidget(self.stepsContainer, 0, Qt.AlignCenter)

        self.movie.start()
        _on_frame(0)

        # Step 1 is completed immediately on client launch
        self.setStep(1, "success")

    def setStep(self, step_num: int, state: str = "success", custom_text: str = None):
        """
        Updates the visual state of a specific step (1-indexed).
        state: 'pending' / 'active' (dark gray #72757d), 'success' (blue/green), 'error' (red)
        """
        idx = step_num - 1
        if 0 <= idx < len(self.step_labels):
            lbl = self.step_labels[idx]
            if custom_text:
                lbl.setText(custom_text)

            color = self.pending_color
            if state == "success":
                color = self.accent_color
            elif state == "error":
                color = self.error_color
            else:
                color = self.pending_color

            lbl.setStyleSheet(f"color: {color}; background: transparent;")

    def setCoreProgress(self, percent: int):
        """
        Updates step 3 with an explicit progress percentage in dark gray until 100%.
        """
        p = max(0, min(100, int(percent)))
        if p >= 100:
            self.setStep(3, "success", f"{self.core_title} complete")
        else:
            self.setStep(3, "pending", f"{self.core_title} - {p}%")

    def setMod(self, mod_path_or_name: str, percent: int = None):
        """
        Updates step 4 in dark gray with just the file name (e.g. 'Cherry.bmod').
        """
        if not mod_path_or_name:
            self.setStep(4, "pending", "Loading mods")
            return

        name = Path(mod_path_or_name).name
        if percent is not None:
            self.setStep(4, "pending", f"Loading mod: {name} ({percent}%)")
        else:
            self.setStep(4, "pending", f"Loading mod: {name}")

    def setText(self, text: str):
        """Backwards-compatibility fallback."""
        if not text:
            return
        t_lower = text.lower()
        if "mod" in t_lower and ("loading" in t_lower or ".bmod" in t_lower):
            cleaned = text.replace("Loading mod '", "").replace("'", "").replace("Loading mod: ", "").strip()
            self.setMod(cleaned)
        elif "core" in t_lower:
            self.setStep(3, "pending", text)
        elif "gamebanana" in t_lower:
            self.setStep(2, "pending", text)
        elif "happy" in t_lower or "ready" in t_lower:
            self.setStep(5, "success")
