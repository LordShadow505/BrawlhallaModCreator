"""
generate_splash.py – BrawlhallaModCreator
==========================================
Loads the manually designed splash.png base image and overlays:
  - "Loading files:"  (Bespoke 9pt, white, bottom-left)
  - "ver. X.Y.Z"      (Bespoke 9pt, white, bottom-left, below loading label)

Everything else stays exactly as drawn in the manual design.
Run this script whenever the version changes or after editing the base image.
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QColor, QFont, QFontDatabase, QPixmap, QImage

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_PATH = os.path.join(
    _SCRIPT_DIR,
    "ui", "ui_sources", "resources", "fonts", "Bespoke", "Bespoke.ttf"
)

# splash_base.png  = manually designed image (never modified by this script)
# splash.png        = final output (readable by PyInstaller's pyi_splash)
BASE_IMAGE_PATH = os.path.join(_SCRIPT_DIR, "splash_base.png")
OUTPUT_PATH     = os.path.join(_SCRIPT_DIR, "splash.png")

# ──────────────────────────────────────────────────────────────────────────────
# Version (fallback used when running as plain script)
# ──────────────────────────────────────────────────────────────────────────────
VERSION = "0.4.0"

VERSION_TEXT_SIZE = 10   # pt
VERSION_X         = 736  # px from left
VERSION_Y         = 440  # px from top (baseline)


# ──────────────────────────────────────────────────────────────────────────────
def create_splash(version: str = VERSION):
    app = QApplication.instance() or QApplication(sys.argv)

    # Load Bespoke font
    font_id = QFontDatabase.addApplicationFont(FONT_PATH)
    if font_id == -1:
        print(f"[WARNING] Could not load Bespoke font from: {FONT_PATH}  – using Arial")
        font_family = "Arial"
    else:
        families    = QFontDatabase.applicationFontFamilies(font_id)
        font_family = families[0] if families else "Arial"
        print(f"[INFO] Loaded font: {font_family}")

    # Read the manually designed base image into memory BEFORE opening the
    # output file for writing, so read-then-write is safe even when paths match.
    base_pixmap = QPixmap(BASE_IMAGE_PATH)
    if base_pixmap.isNull():
        print(f"[ERROR] Could not load base image: {BASE_IMAGE_PATH}")
        print("        Make sure splash.png exists in the same folder as this script.")
        return

    width  = base_pixmap.width()
    height = base_pixmap.height()

    image = base_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    # Version text at fixed position, white, Bespoke 10pt
    font = QFont(font_family, VERSION_TEXT_SIZE)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))

    version_str = f"ver. {version}"
    painter.drawText(VERSION_X, VERSION_Y, version_str)

    painter.end()

    image.save(OUTPUT_PATH)
    print(f"[OK] Splash saved: {OUTPUT_PATH}")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Optional CLI version override:  python generate_splash.py 0.4.0
    ver = sys.argv[1] if len(sys.argv) > 1 else VERSION
    create_splash(version=ver)
