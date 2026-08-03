# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

qt_excludes = [
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineProcess',
    'PySide6.Qt3DCore', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic',
    'PySide6.Qt3DRender', 'PySide6.Qt3DExtras',
    'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQuickControls2', 'PySide6.QtQml',
    'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    'PySide6.QtSql', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
    'PySide6.QtDesigner', 'PySide6.QtTest', 'PySide6.QtPositioning', 'PySide6.QtSensors',
    'PySide6.QtNfc', 'PySide6.QtBluetooth', 'PySide6.QtSpatialAudio',
    'tkinter', '_tkinter', 'unittest', 'doctest', 'pydoc', 'pygame', 'scipy', 'numpy', 'matplotlib'
]

a = Analysis(['run.py'],
             binaries=[],
             datas=[],
             hiddenimports=['core', 'core.worker', 'core.worker.brawlhalla', 'core.worker.config'],
             hookspath=[],
             runtime_hooks=[],
             excludes=qt_excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
splash = Splash('splash.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(192, 290),
                text_font="ui/ui_sources/resources/fonts/Bespoke/Bespoke.ttf",
                text_size=12,
                text_color='#FFFFFF')
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          Tree("ui", "ui", excludes=["*.ttf", "*.png", "*.jpg", "*.ui", "*.txt", "*.pyc", "*.pyo"]),
          Tree("core", "core", excludes=["*.pyc", "*.pyo"]),
          [],
          splash,
          splash.binaries,
          name='Brawlhalla Mod Creator',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
          runtime_tmpdir=None,
          version='version.spec',
          console=False,
          uac_admin=False,
          icon='ui/ui_sources/resources/icons/App.ico')
