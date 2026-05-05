import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QColor, QFont, QBrush, QImage, QPainterPath, QPixmap
from PySide6.QtCore import Qt, QRect

def create_splash():
    app = QApplication(sys.argv)
    
    # Using a slightly larger canvas to avoid edge clipping artifacts
    width, height = 650, 420
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    
    # Draw background with a 1px margin to ensure smooth edges and no artifacts
    bg_rect = QRect(1, 1, width - 2, height - 2)
    path = QPainterPath()
    path.addRoundedRect(bg_rect, 15, 15)
    
    # Clean fill
    painter.setBrush(QBrush(QColor("#18191e")))
    painter.setPen(Qt.NoPen)
    painter.drawPath(path)
    
    x_offset = 40
    y_start = 60
    
    # Title - 24px
    painter.setPen(QColor("#4A90E2"))
    font_title = QFont("Exo 2", 24, QFont.Bold)
    painter.setFont(font_title)
    painter.drawText(x_offset, y_start + 30, "Brawlhalla Mod Creator")
    
    # Info lines - 14px
    painter.setPen(QColor("#888888"))
    font_info = QFont("Roboto", 14)
    painter.setFont(font_info)
    
    info_y = y_start + 65
    painter.drawText(x_offset, info_y, "Source: https://github.com/LordShadow505/BrawlhallaModCreator")
    painter.drawText(x_offset, info_y + 22, "Version: 3.0.0 Beta")
    painter.drawText(x_offset, info_y + 44, "Author: I_FabrizioG_I")
    painter.drawText(x_offset, info_y + 66, "Maintainers: LordShadow505 & Bucccket")
    painter.drawText(x_offset, info_y + 100, "Discord: I_FabrizioG_I#8111")
    
    # Loading label - 10px
    painter.setPen(QColor("#AAAAAA"))
    font_load = QFont("Roboto", 10, QFont.Bold)
    painter.setFont(font_load)
    # Aligned with text_pos=(170, 306)
    painter.drawText(x_offset, 306, "Loading files:") 
    
    # Warning message at the bottom in red - 10px
    painter.setPen(QColor("#FF5252"))
    font_warn = QFont("Roboto", 10, QFont.Bold)
    painter.setFont(font_warn)
    
    warning_msg = "Note: Skin mods require a PAID base skin. Check requirements on GameBanana."
    icon_path = "ui/ui_sources/resources/icons/Warning.png"
    if os.path.exists(icon_path):
        warning_icon = QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(x_offset, 370, warning_icon)
        painter.drawText(x_offset + 25, 383, warning_msg)
    else:
        painter.drawText(x_offset, 383, warning_msg)
    
    painter.end()
    image.save("splash.png")
    print("Splash screen generated successfully as splash.png")

if __name__ == "__main__":
    create_splash()
