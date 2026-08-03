# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['run.py'],
             binaries=[],
             datas=[],
             hiddenimports=['core', 'core.worker', 'core.worker.brawlhalla', 'core.worker.config', 'markdown', 'markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.sane_lists'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['tkinter', '_tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

a.datas += Tree("ui", "ui", excludes=["*.ttf", "*.png", "*.jpg", "*.ui", "*.txt", "*.pyc", "*.pyo"])
a.datas += Tree("core", "core", excludes=["*.pyc", "*.pyo"])

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
          splash,
          splash.binaries,
          name='Brawlhalla Mod Creator',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
          runtime_tmpdir=None,
          version='version.spec',
          console=False,
          uac_admin=False,
          icon='ui/ui_sources/resources/icons/App.ico')
