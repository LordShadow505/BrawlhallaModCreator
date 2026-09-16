"""
generate_splash.py – BrawlhallaModCreator
==========================================
Loads the manually designed splash_base.png image and overlays:
  - "ver. X.Y.Z" (Bespoke 10pt, white, bottom-right)
Generates:
  - splash.png: clean template for PySide6 dynamic loading text
  - pre_splash.png: static splash with "Extracting Python runtime & dependencies..." for Nuitka bootloader
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

BASE_IMAGE_PATH   = os.path.join(_SCRIPT_DIR, "splash_base.png")
OUTPUT_SPLASH     = os.path.join(_SCRIPT_DIR, "splash.png")
OUTPUT_PRE_SPLASH = os.path.join(_SCRIPT_DIR, "pre_splash.png")

# ──────────────────────────────────────────────────────────────────────────────
# Version (fallback used when running as plain script)
# ──────────────────────────────────────────────────────────────────────────────
VERSION = "0.4.2"

VERSION_TEXT_SIZE = 10   # pt
VERSION_X         = 736  # px from left
VERSION_Y         = 440  # px from top (baseline)

STATUS_TEXT_SIZE  = 13   # pt
STATUS_X          = 202  # px from left
STATUS_Y          = 302  # px from top


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

    # Read base image
    base_pixmap = QPixmap(BASE_IMAGE_PATH)
    if base_pixmap.isNull():
        print(f"[ERROR] Could not load base image: {BASE_IMAGE_PATH}")
        return

    # 1. Clean dynamic splash.png (PySide6 renders status texts onto this at runtime)
    image_dynamic = base_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    p1 = QPainter(image_dynamic)
    p1.setRenderHint(QPainter.Antialiasing)
    p1.setFont(QFont(font_family, VERSION_TEXT_SIZE))
    p1.setPen(QColor("#FFFFFF"))
    p1.drawText(VERSION_X, VERSION_Y, f"ver. {version}")
    p1.end()
    image_dynamic.save(OUTPUT_SPLASH)
    print(f"[OK] Dynamic splash saved: {OUTPUT_SPLASH}")

    # 2. Pre-splash for Nuitka C-bootloader (while extracting Python environment)
    image_pre = base_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    p2 = QPainter(image_pre)
    p2.setRenderHint(QPainter.Antialiasing)
    p2.setFont(QFont(font_family, VERSION_TEXT_SIZE))
    p2.setPen(QColor("#FFFFFF"))
    p2.drawText(VERSION_X, VERSION_Y, f"ver. {version}")

    p2.setFont(QFont(font_family, STATUS_TEXT_SIZE))
    p2.setPen(QColor("#CCCCCC"))
    p2.drawText(STATUS_X, STATUS_Y, "Extracting Python runtime & dependencies...")
    p2.end()
    image_pre.save(OUTPUT_PRE_SPLASH)
    print(f"[OK] Pre-splash saved: {OUTPUT_PRE_SPLASH}")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ver = sys.argv[1] if len(sys.argv) > 1 else VERSION
    create_splash(version=ver)

