import os
import sys

# Ensure PyInstaller runtime directories are registered for Windows DLL search
if getattr(sys, 'frozen', False):
    _base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    os.environ['PATH'] = _base_dir + os.pathsep + os.path.join(_base_dir, 'PySide6') + os.pathsep + os.path.join(_base_dir, 'shiboken6') + os.pathsep + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(_base_dir)
        except Exception:
            pass
        for _sub in ['PySide6', 'shiboken6']:
            _sub_dir = os.path.join(_base_dir, _sub)
            if os.path.isdir(_sub_dir):
                try:
                    os.add_dll_directory(_sub_dir)
                except Exception:
                    pass
    try:
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(_base_dir)
    except Exception:
        pass

import threading
import webbrowser
import multiprocessing
import traceback
import subprocess

from typing import List



core = None
try:
    import core
    from core import NotificationType, Notification, Environment, CORE_VERSION

    JAVA_FOUND = True
except Exception as e:
    Notification = None
    JAVA_FOUND = False

    CORE_IMPORT_ERROR = f"{type(e).__name__}: {str(e)}"
    print(f"Error importing core: {CORE_IMPORT_ERROR}")
    traceback.print_exc()

from PySide6.QtGui import QIcon, QFontDatabase, QFont, QPixmap, QPainter, QColor
from PySide6.QtCore import QTimer, QSize, Qt, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QFrame, QVBoxLayout, QLabel, QSplashScreen

from ui.ui_handler.window import Window
from ui.ui_handler.loading import Loading
from ui.ui_handler.header import HeaderFrame
from ui.ui_handler.mods import Mods
from ui.ui_handler.settings import SettingsFrame
from ui.ui_handler.progressdialog import ProgressDialog
from ui.ui_handler.buttonsdialog import ButtonsDialog
from ui.ui_handler.acceptdialog import AcceptDialog
from ui.ui_handler.inputdialog import InputDialog

from ui.utils.layout import AddToFrame, ClearFrame
from ui.utils.textformater import TextFormatter
from ui.utils.markdown_helper import render_markdown_to_html
from ui.utils.version import GetLatest, GITHUB, REPO, VERSION, GIT_VERSION, PRERELEASE, GAMEBANANA
from ui.utils.mainthread import QExecMainThread
from ui.utils.config import CreatorConfig

SUPPORT_URL = "https://www.patreon.com/bhmodloader"

PROGRAM_NAME = "Brawlhalla Mod Creator"


GLOBAL_SPLASH = None


def close_nuitka_splash():
    """Ensure Nuitka onefile bootloader splash is completely closed/hidden."""
    # 1. Official Nuitka onefile splash dismissal using NUITKA_ONEFILE_PARENT environment variable
    try:
        if "NUITKA_ONEFILE_PARENT" in os.environ:
            import tempfile
            splash_filename = os.path.join(
                tempfile.gettempdir(),
                "onefile_%d_splash_feedback.tmp" % int(os.environ["NUITKA_ONEFILE_PARENT"]),
            )
            if os.path.exists(splash_filename):
                try:
                    os.unlink(splash_filename)
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Native module fallback if available
    try:
        import onefile_splash
        onefile_splash.close()
    except Exception:
        pass

    # 3. Clean any remaining splash feedback tmp files in temp directory
    try:
        import tempfile, glob
        temp_dir = tempfile.gettempdir()
        for f in glob.glob(os.path.join(temp_dir, "onefile_*_splash_feedback.tmp")):
            try:
                os.unlink(f)
            except Exception:
                pass
    except Exception:
        pass

    # 4. Find and close any lingering Windows splash window with class "Splash"
    try:
        import win32gui, win32con
        def enum_cb(hwnd, _):
            if win32gui.GetClassName(hwnd) == "Splash":
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass


def set_global_splash(splash):
    global GLOBAL_SPLASH
    GLOBAL_SPLASH = splash


def get_global_splash():
    global GLOBAL_SPLASH
    return GLOBAL_SPLASH


def InitWindowSetText(text, delay_ms=120):
    global GLOBAL_SPLASH
    if GLOBAL_SPLASH is not None:
        GLOBAL_SPLASH.set_status(str(text), delay_ms=delay_ms)


def InitWindowClose():
    global GLOBAL_SPLASH
    if GLOBAL_SPLASH is not None:
        InitWindowSetText("Ready!", delay_ms=80)
        close_nuitka_splash()
        if hasattr(ModCreator, 'app') and ModCreator.app:
            GLOBAL_SPLASH.finish(ModCreator.app)
        else:
            GLOBAL_SPLASH.close()
        GLOBAL_SPLASH = None


def TerminateApp():
    for proc in multiprocessing.active_children():
        proc.kill()
    os.kill(multiprocessing.current_process().pid, 0)
    sys.exit(0)


def get_dir_size(path='.'):
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
    except:
        pass
    return total

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def restart_app():
    # Kill background children before restarting
    for proc in multiprocessing.active_children():
        proc.kill()
    os.execl(sys.executable, sys.executable, *sys.argv)


class ModCreator(QMainWindow):
    brawlhallaNotFoundSignal = Signal()
    _loaded = False

    # Path resolution:
    # 1. Look for local folders (Portable mode)
    # 2. Fallback to APPDATA (Persistent mode)
    _local_base = (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(sys.argv[0]))
    )
    _local_mods = os.path.join(_local_base, "Mods")
    _local_mods_sources = os.path.join(_local_base, "Mods Sources")

    config = CreatorConfig()
    if config.modsPath:
        modsPath = config.modsPath
    else:
        modsPath = _local_mods
        os.makedirs(modsPath, exist_ok=True)

    if config.modsSourcesPath:
        modsSourcesPath = config.modsSourcesPath
    else:
        modsSourcesPath = _local_mods_sources
        os.makedirs(modsSourcesPath, exist_ok=True)

    errors: List[Notification] = []

    app = None

    def __init__(self):
        super().__init__()
        self.ui = Window(self)

        self.config = CreatorConfig()

        QExecMainThread.init(self)

        InitWindowSetText("Loading user interface...")

        self.setWindowTitle(PROGRAM_NAME)
        self.setWindowIcon(QIcon(':/icons/resources/icons/App.ico'))

        self.loading = Loading(is_creator=True)
        self.header = HeaderFrame(githubMethod=lambda: webbrowser.open(f"{GITHUB}/{REPO}"),
                                  supportMethod=lambda: webbrowser.open(SUPPORT_URL),
                                  infoMethod=self.showInformation)
        self.mods = Mods(saveMethod=self.saveModSource,
                         installMethod=self.installMod,
                         uninstallMethod=self.uninstallMod,
                         reinstallMethod=self.reinstallMod,
                         deleteMethod=self.deleteMod,
                         buildMethod=self.buildMod,
                         createMethod=self.createMod,
                         reloadMethod=self.reloadMods,
                         openFolderMethod=self.openModsSourcesFolder,
                         uninstallAllMethod=self.uninstallAllMods,
                         sortCallback=self.updateSortState)
        self.progressDialog = ProgressDialog(self)
        self.acceptDialog = AcceptDialog(self)  # TODO: Remake to buttons dialog
        self.inputDialog = InputDialog(self)
        self.buttonsDialog = ButtonsDialog(self)

        bhPath = "Not found"
        cacheSize = "0 B"
        if core and hasattr(core, 'worker') and hasattr(core.worker, 'brawlhalla'):
            bhPath = core.worker.brawlhalla.BRAWLHALLA_PATH or "Not found"
        if core and hasattr(core, 'MODLOADER_CACHE_PATH'):
            cacheSize = format_size(get_dir_size(core.MODLOADER_CACHE_PATH))

        self.settings = SettingsFrame(
            saveCallback=self.syncSettingsWithCore,
            openCacheMethod=self.openCacheFolder,
            clearCacheMethod=self.clearCache,
            bhPath=bhPath,
            modsPath=self.modsPath,
            modsSourcesPath=self.modsSourcesPath,
            cacheSize=cacheSize
        )
        self.bulkOperationCount = 0
        self.currentSortField = getattr(self.config, 'sortField', 'Date') or 'Date'
        self.currentSortReverse = getattr(self.config, 'sortReverse', True) if getattr(self.config, 'sortReverse', None) is not None else True
        self.setLoadingScreen()
        self.header.setSettingsButtonPressed(self.setSettingsScreen)
        self.header.setModsButtonPressed(lambda: self.checkUnsavedSettings(self.setModsScreen))

        self.setMinimumSize(QSize(850, 550))

        self.brawlhallaNotFoundSignal.connect(self.showBrawlhallaNotFoundDialog)
        threading.Thread(target=self.checkNewVersion).start()

        self.controller = None

        if JAVA_FOUND:
            threading.Thread(target=self.runController).start()

            # Get core events
            self.controllerGetterTimer = QTimer()
            self.controllerGetterTimer.timeout.connect(self.controllerHandler)
            self.controllerGetterTimer.start(10)
        else:
            err_str = str(CORE_IMPORT_ERROR).lower() if CORE_IMPORT_ERROR else ""
            is_java_error = not CORE_IMPORT_ERROR or any(k in err_str for k in ["java not found", "jvmnotfoundexception"])
            if not is_java_error:
                message = f"Error importing core:\n\n{CORE_IMPORT_ERROR}\n\nPlease check your installation."
            else:
                message = ("Java Not Found!\n\n"
                           "Java 64-bit is required to run this application.\n\n"
                           "<b>1. Download & Install (If not installed):</b>\n"
                           "Download and install the <u>Windows Offline (64-bit)</u> version from:\n"
                           "<url=\"https://www.java.com/en/download/windows_manual.jsp\">"
                           "https://www.java.com/en/download/windows_manual.jsp</url>\n\n"
                           "<b>2. If already installed:</b>\n"
                           "Set <b>JAVA_HOME</b> as the variable name, and for the path, enter your Java installation directory "
                           "(e.g. <i>C:\\Program Files\\Java\\jre1.8.0_401</i>). Click OK and restart Brawlhalla Mod Creator.")
            self.showError("Fatal Error:", TextFormatter.format(message, 11), terminate=True)

        InitWindowClose()
        self.__class__.app = self

    def runController(self):
        self.loading.setStep(1, "success")
        self.loading.setStep(2, "success")
        self.loading.setStep(3, "active")

        self.controller = core.Controller()
        self.loading.setStep(3, "success")
        self.controller.setDefaultMetadata(
            self.config.defaultAuthor,
            self.config.defaultGameVersion,
            self.config.defaultModVersion
        )
        self.controller.setModsPath(self.modsPath)
        self.controller.setModsSourcesPath(self.modsSourcesPath)

        # Sync custom brawlhalla path to core
        if self.config.brawlhallaPath:
            core.worker.config.ModloaderCoreConfig.customBrawlhallaPath = self.config.brawlhallaPath
            core.worker.config.ModloaderCoreConfig.save()
            if hasattr(core, 'worker') and hasattr(core.worker, 'brawlhalla'):
                core.worker.brawlhalla.BRAWLHALLA_PATH = self.config.brawlhallaPath

        self.controller.reloadMods()
        self.controller.reloadModsSources()

        self.controller.getModsSourcesData()
        self.controller.getModsData()

        # Check if Brawlhalla path was found
        bh_path = getattr(core.worker.brawlhalla, 'BRAWLHALLA_PATH', None) if (hasattr(core, 'worker') and hasattr(core.worker, 'brawlhalla')) else None
        if not bh_path or not os.path.exists(bh_path) or not os.path.isfile(os.path.join(bh_path, "Brawlhalla.exe")):
            QTimer.singleShot(500, self.brawlhallaNotFoundSignal.emit)

    def resizeEvent(self, event):
        self.progressDialog.onResize()
        self.acceptDialog.onResize()
        self.inputDialog.onResize()
        self.buttonsDialog.onResize()
        super().resizeEvent(event)

    def controllerHandler(self):
        if self.controller is None:
            return

        # Process up to 100 messages per tick to avoid overwhelming the UI
        processed = 0
        while self.controller.ready_to_receive and processed < 100:
            try:
                data = self.controller.getData()
                if data is None:
                    break
                self._processControllerData(data)
                processed += 1
            except Exception as e:
                #print(f"[DL ERROR] Exception in controllerHandler: {e}")
                traceback.print_exc()
                break

    def _processControllerData(self, data):
        cmd = data[0]

        if cmd == Environment.Notification:
            notification: core.notifications.Notification = data[1]
            ntype = notification.notificationType

            # print(notification)

            if ntype == NotificationType.LoadingModSource:
                modPath = notification.args[0]
                try:
                    self.loading.setMod(modPath)
                except RuntimeError:
                    pass

            elif ntype in [NotificationType.ModElementsCount, NotificationType.CompileElementsCount]:
                modHash, count = notification.args
                self.progressDialog.setMaximum(count)

            # Check conflicts
            elif ntype == NotificationType.ModConflictSearchInSwf:
                modHash, swfName = notification.args
                self.progressDialog.setContent(f"Searching in: {swfName}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.ModConflictNotFound:
                modHash, = notification.args
                self.progressDialog.setValue(0)
                self.controller.installMod(modHash)
            elif ntype == NotificationType.ModConflict:
                modHash, modConflictHashes = notification.args
                self.acceptDialog.setTitle("Conflict mods!")
                content = "Mods:"

                for modConflictHash in modConflictHashes:
                    if modConflictHash in self.mods.modsSources:
                        mod = self.mods.modsSources[modConflictHash]
                        content += f"\n- {mod.name}"

                    else:
                        content += f"\n- UNKNOWN MOD: {modConflictHash}"
                        #print("ERROR: One of the installed mods was not found in the ModLoader!")

                self.acceptDialog.setContent(content)
                self.acceptDialog.setAccept(lambda: [self.acceptDialog.hide(), self.controller.installMod(modHash)])
                self.acceptDialog.setCancel(self.acceptDialog.hide)

                self.progressDialog.hide()
                self.acceptDialog.show()

            # Installing
            elif ntype == NotificationType.InstallingModSwf:
                modHash, swfName = notification.args
                self.progressDialog.setContent(f"Open game file: {swfName}")
            elif ntype == NotificationType.InstallingModSwfSprite:
                modHash, sprite = notification.args
                self.progressDialog.setContent(f"Installing sprite: {sprite}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModSwfSound:
                modHash, sound = notification.args
                self.progressDialog.setContent(f"Installing sound: {sound}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModFile:
                modHash, fileName = notification.args
                self.progressDialog.setContent(f"Installing file: {fileName}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModFileCache:
                modHash, fileName = notification.args
                self.progressDialog.setContent(fileName)
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModFinished:
                modHash = notification.args[0]
                modClass = self.mods.modsSources.get(modHash)
                if modClass:
                    modClass.installed = True
                
                # Update specific mod button UI
                for btn in self.mods.modsButtons:
                    if btn.modClass.hash == modHash:
                        btn.updateData()
                        break
                
                # Update main view if it's the selected one
                if self.mods.selectedModButton and self.mods.selectedModButton.modClass.hash == modHash:
                    self.mods.updateAll()
                
                if self.bulkOperationCount > 0:
                    self.bulkOperationCount -= 1
                    
                if self.bulkOperationCount <= 0:
                    self.bulkOperationCount = 0
                    self.progressDialog.hide()
                    #print(f"[DL DEBUG] UI: Progress dialog HIDDEN (Install Finished)")

                if self.currentSortField == "Installed":
                    self.mods.applySort(self.currentSortField, self.currentSortReverse)
                    
                self.showErrorNotifications()
                #print(f"[DL DEBUG] UI: Installation Finished processed for {modHash}")

            # Uninstalling
            elif ntype == NotificationType.UninstallingModSwf:
                modHash, swfName = notification.args
                self.progressDialog.setContent(swfName)
            elif ntype == NotificationType.UninstallingModSwfSprite:
                modHash, sprite = notification.args
                self.progressDialog.setContent(sprite)
                self.progressDialog.addValue()
            elif ntype == NotificationType.UninstallingModSwfSound:
                modHash, sprite = notification.args
                self.progressDialog.setContent(sprite)
                self.progressDialog.addValue()
            elif ntype == NotificationType.UninstallingModFile:
                modHash, fileName = notification.args
                self.progressDialog.setContent(fileName)
                self.progressDialog.addValue()
            elif ntype == NotificationType.UninstallingModFinished:
                modHash = notification.args[0]
                modClass = self.mods.modsSources.get(modHash)
                if modClass:
                    modClass.installed = False
                
                # Update specific mod button UI
                for btn in self.mods.modsButtons:
                    if btn.modClass.hash == modHash:
                        btn.updateData()
                        break
                
                # Update main view if it's the selected one
                if self.mods.selectedModButton and self.mods.selectedModButton.modClass.hash == modHash:
                    self.mods.updateAll()

                if self.bulkOperationCount > 0:
                    self.bulkOperationCount -= 1
                    
                if self.bulkOperationCount <= 0:
                    self.bulkOperationCount = 0
                    self.progressDialog.hide()
                    #print(f"[DL DEBUG] UI: Progress dialog HIDDEN (Uninstall Finished)")

                if self.currentSortField == "Installed":
                    self.mods.applySort(self.currentSortField, self.currentSortReverse)
                    
                self.showErrorNotifications()
                #print(f"[DL DEBUG] UI: Uninstallation Finished for {modHash}")

            # Compile
            elif ntype == NotificationType.CompileModSourcesImportActionScripts:
                modHash, actionScript = notification.args
                self.progressDialog.setContent(f"Assembly ActionScript: {actionScript}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.CompileModSourcesImportFile:
                modHash, file = notification.args
                self.progressDialog.setContent(f"Assembly file: {file}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.CompileModSourcesImportSound:
                modHash, sound = notification.args
                self.progressDialog.setContent(f"Assembly sound: {sound}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.CompileModSourcesImportSprite:
                modHash, sprite = notification.args
                self.progressDialog.setContent(f"Assembly sprite: {sprite}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.CompileModSourcesImportPreview:
                modHash, preview = notification.args
                self.progressDialog.setContent(f"Assembly preview: {preview}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.CompileModSourcesFinished:
                modHash = notification.args[0]
                elapsed = notification.args[1] if len(notification.args) > 1 else None
                message = (notification.args[2] if len(notification.args) > 2 else
                           (f"Build completed in {float(elapsed):.2f} seconds."
                            if elapsed is not None else "Build completed."))
                self.showErrorNotifications()

                # The worker already reloads the newly published bmod before
                # emitting Finished. Avoid opening/checking it a second time.
                self.controller.getModsData()

                # Update UI for this mod
                for btn in self.mods.modsButtons:
                    if btn.modClass.hash == modHash:
                        btn.updateData()
                        break
                if self.mods.selectedModButton and self.mods.selectedModButton.modClass.hash == modHash:
                    self.mods.updateAll()

                self.bulkOperationCount = 0
                self.progressDialog.setTitle("Build completed")
                self.progressDialog.setContent(message)
                self.progressDialog.setValue(self.progressDialog.ui.progressBar.maximum())

                # Keep the existing progress overlay briefly as the success
                # notification.  Do not let an old timer hide a newer job.
                def hideCompletedBuild(expectedMessage=message):
                    if (self.progressDialog.isShown() and
                            self.progressDialog.ui.title.text() == "Build completed" and
                            self.progressDialog.ui.content.text() == expectedMessage):
                        self.progressDialog.hide()

                QTimer.singleShot(1000, hideCompletedBuild)
                #print(f"[DL DEBUG] UI: Progress dialog HIDDEN (Compile Finished)")

            # Errors
            elif ntype in [NotificationType.CompileModSourcesSpriteHasNoSymbolclass,  # Compiler
                           NotificationType.CompileModSourcesSpriteEmpty,
                           NotificationType.CompileModSourcesSpriteNotFoundInFolder,
                           NotificationType.CompileModSourcesUnsupportedCategory,
                           NotificationType.CompileModSourcesUnknownFile,
                           NotificationType.CompileModSourcesSaveError,
                           NotificationType.CompileModSourcesDefectivePiece,
                           NotificationType.CompileModSourcesDuplicateSpriteId,
                           NotificationType.CompileModSourcesGeneralError,
                           NotificationType.LoadingModIsEmpty,  # Loader
                           NotificationType.InstallingModNotFoundFileElement,  # Installer
                           NotificationType.InstallingModNotFoundGameSwf,
                           NotificationType.InstallingModSwfScriptError,
                           NotificationType.InstallingModSwfSoundSymbolclassNotExist,
                           NotificationType.InstallingModSoundNotExist,
                           NotificationType.InstallingModSwfSpriteSymbolclassNotExist,
                           NotificationType.InstallingModSpriteNotExist,
                           NotificationType.UninstallingModSwfOriginalElementNotFound,  # Uninstaller
                           NotificationType.UninstallingModSwfElementNotFound]:
                self.errors.append(notification)
                if ntype in [NotificationType.CompileModSourcesDefectivePiece, NotificationType.CompileModSourcesDuplicateSpriteId, NotificationType.CompileModSourcesGeneralError,
                             NotificationType.CompileModSourcesSaveError, NotificationType.CompileModSourcesSpriteNotFoundInFolder,
                             NotificationType.CompileModSourcesSpriteEmpty, NotificationType.CompileModSourcesSpriteHasNoSymbolclass]:
                    self.showErrorNotifications()
                    self.controller.getModsData()

            elif ntype == NotificationType.FatalError:
                self.showError("Fatal Error:", notification.args[0])

        elif cmd == Environment.GetModsSourcesData:
            for modSourcesData in data[1]:
                self.mods.addMod(gameVersion=modSourcesData.get("gameVersion", ""),
                                 name=modSourcesData.get("name", ""),
                                 author=modSourcesData.get("author", ""),
                                 version=modSourcesData.get("version", ""),
                                 description=modSourcesData.get("description", ""),
                                 tags=modSourcesData.get("tags", []),
                                 previewsPaths=modSourcesData.get("previewsPaths", []),
                                 hash=modSourcesData.get("hash", ""),
                                 platform=modSourcesData.get("platform", ""),
                                 # installed=modData.get("installed", False),
                                 currentVersion=modSourcesData.get("gameVersion", "") == \
                                                modSourcesData.get("currentGameVersion", " "),
                                 # modFileExist=modData.get("modFileExist", False)
                                 modSourcesPath=modSourcesData.get("modSourcesPath", ""), date=modSourcesData.get("date", 0.0),
                                 swfNames=modSourcesData.get("swfNames", []),
                                 spriteNames=modSourcesData.get("spriteNames", []),
                                 swfs=modSourcesData.get("swfs", {}))

                self.mods.currentGameVersion = modSourcesData.get("currentGameVersion", "")

            self.showErrorNotifications()

        elif cmd == Environment.GetModsData:
            # Reset flags for all known mods first to clear stale data
            for mod in self.mods.modsSources.values():
                mod.modFileExist = False
                mod.installed = False

            for modData in data[1]:
                self.mods.updateMod(hash=modData.get("hash", ""),
                                    installed=modData.get("installed", False),
                                    modFileExist=modData.get("modFileExist", False))

            self.mods.applySort(self.currentSortField, self.currentSortReverse)
            self.mods.updateAll()
            if hasattr(self, 'loading'):
                self.loading.setStep(4, "success", "Mods loaded")
                self.loading.setStep(5, "success")
            self.setModsScreen()
            self.showErrorNotifications()

        elif cmd == Environment.GetModConflict:
            searching, modHash = data[1]
            if searching:
                modClass = self.mods.modsSources.get(modHash)
                if modClass:
                    self.progressDialog.setTitle(f"Searching conflicts '{modClass.name}'...")
                else:
                    self.progressDialog.setTitle(f"Searching conflicts...")
                self.progressDialog.setContent("Searching...")
                self.progressDialog.show()

        elif cmd == Environment.InstallMod:
            installing, modHash = data[1]
            if installing:
                modClass = self.mods.modsSources.get(modHash)
                if modClass:
                    self.progressDialog.setTitle(f"Installing mod '{modClass.name}'...")
                else:
                    self.progressDialog.setTitle(f"Installing mod...")
                self.progressDialog.setContent("Loading mod...")
                self.progressDialog.show()

        elif cmd == Environment.UninstallMod:
            uninstalling, modHash = data[1]
            if uninstalling:
                modClass = self.mods.modsSources.get(modHash)
                if modClass:
                    self.progressDialog.setTitle(f"Uninstalling mod '{modClass.name}'...")
                else:
                    self.progressDialog.setTitle(f"Uninstalling mod...")
                self.progressDialog.setContent("")
                self.progressDialog.show()

        elif cmd == Environment.CompileModSources:
            compiling, modHash = data[1]
            if compiling:
                modClass = self.mods.modsSources.get(modHash)
                if modClass:
                    self.progressDialog.setTitle(f"Build mod '{modClass.name}'...")
                else:
                    self.progressDialog.setTitle(f"Build mod...")
                self.progressDialog.setContent("")
                self.progressDialog.show()

        elif cmd == Environment.CreateMod:
            created, modSourcesData = data[1]
            if created:
                modHash = modSourcesData.get("hash")
                
                # Apply defaults
                self.controller.setModAuthor(modHash, self.config.defaultAuthor)
                self.controller.setModGameVersion(modHash, self.config.defaultGameVersion)
                self.controller.setModVersion(modHash, self.config.defaultModVersion)
                self.controller.saveModSource(modHash)

                # Update local data for display
                modSourcesData["author"] = self.config.defaultAuthor
                modSourcesData["gameVersion"] = self.config.defaultGameVersion
                modSourcesData["version"] = self.config.defaultModVersion

                self.inputDialog.hide()
                self.mods.addMod(gameVersion=modSourcesData.get("gameVersion", ""),
                                 name=modSourcesData.get("name", ""),
                                 author=modSourcesData.get("author", ""),
                                 version=modSourcesData.get("version", ""),
                                 description=modSourcesData.get("description", ""),
                                 tags=modSourcesData.get("tags", []),
                                 previewsPaths=modSourcesData.get("previewsPaths", []),
                                 hash=modSourcesData.get("hash", ""),
                                 platform=modSourcesData.get("platform", ""),
                                 # installed=modData.get("installed", False),
                                 currentVersion=modSourcesData.get("gameVersion", "") == \
                                                modSourcesData.get("currentGameVersion", " "),
                                 # modFileExist=modData.get("modFileExist", False)
                                 modSourcesPath=modSourcesData.get("modSourcesPath", ""), date=modSourcesData.get("date", 0.0),
                                 swfNames=modSourcesData.get("swfNames", []),
                                 spriteNames=modSourcesData.get("spriteNames", []),
                                 swfs=modSourcesData.get("swfs", {}))

                self.mods.currentGameVersion = modSourcesData.get("currentGameVersion", "")
            else:
                self.inputDialog.clearInput()
                self.inputDialog.setTitle("Create mod...")
                self.inputDialog.setContent(TextFormatter.format("Enter mod folder name\n\n"
                                                                 '<color="#ff5050">This folder already exists!</color>'))
                # self.controller.reloadModsSources()

    def showErrorNotifications(self):
        if self.errors:
            errors = []
            errorsNotifications = self.errors.copy()
            self.errors.clear()

            for notif in errorsNotifications:
                ntype = notif.notificationType
                string = ""

                # Compiler
                if ntype == NotificationType.CompileModSourcesSpriteHasNoSymbolclass:
                    string = f"Sprite '{notif.args[1]}' has no name"

                elif ntype == NotificationType.CompileModSourcesSpriteEmpty:
                    string = f"Sprite '{notif.args[1]}' is empty"

                elif ntype == NotificationType.CompileModSourcesSpriteNotFoundInFolder:
                    string = f"Not found sprite in '{notif.args[1]}'"

                elif ntype == NotificationType.CompileModSourcesUnsupportedCategory:
                    string = (f"Unsupported elements category '{notif.args[1]}'.\n\n"
                              f"Make sure the format is correct, for example:\n"
                              f"Gfx_Something.swf/sprites/.../...")

                elif ntype == NotificationType.CompileModSourcesUnknownFile:
                    string = f"Unknown file '{notif.args[1]}'"

                elif ntype == NotificationType.CompileModSourcesSaveError:
                    string = "Error save .bmod"

                elif ntype == NotificationType.CompileModSourcesDuplicateSpriteId:
                    sprite_id = notif.args[1]
                    sprite1 = notif.args[2]
                    sprite2 = notif.args[3]
                    string = (f"There is a conflict because two sprites share the same ID number.\n\n"
                              f"Duplicate ID: {sprite_id}\n"
                              f"Found in: '{sprite1}' and '{sprite2}'\n"
                              f"Please change the ID of one of them and try again.")

                elif ntype == NotificationType.CompileModSourcesDefectivePiece:
                    sprite = notif.args[1]
                    element_id = notif.args[2]
                    string = (f"There is a defective piece in the mod, please delete it and try again.\n\n"
                             f"The defective piece is: {sprite} (Element ID: {element_id})")



                elif ntype == NotificationType.CompileModSourcesGeneralError:
                    error_msg = notif.args[1]
                    # traceback_str = notif.args[2]
                    string = f"An error occurred during compilation: {error_msg}"

                # Loader
                elif ntype == NotificationType.LoadingModIsEmpty:
                    string = f"Mod '{notif.args[1]}' is empty"

                # Installer
                elif ntype == NotificationType.InstallingModNotFoundFileElement:
                    string = f"Not found element '{notif.args[1]}' in bmod "

                elif ntype == NotificationType.InstallingModNotFoundGameSwf:
                    string = f"Not found game file '{notif.args[1]}'"

                elif ntype == NotificationType.InstallingModSwfScriptError:
                    string = f"Script '{notif.args[1]}' not installed"

                elif ntype == NotificationType.InstallingModSwfSoundSymbolclassNotExist:
                    string = f"Not found sound '{notif.args[1]}' in '{notif.args[2]}'"

                elif ntype == NotificationType.InstallingModSoundNotExist:
                    string = f"Not found sound '{notif.args[1]} ({notif.args[2]})' in '{notif.args[3]}'"

                elif ntype == NotificationType.InstallingModSwfSpriteSymbolclassNotExist:
                    string = f"Not found sprite '{notif.args[1]}' in '{notif.args[2]}'"

                elif ntype == NotificationType.InstallingModSpriteNotExist:
                    string = f"Not found sprite '{notif.args[1]} ({notif.args[2]})' in mod file"

                # Uninstaller
                elif ntype == NotificationType.UninstallingModSwfOriginalElementNotFound:
                    string = f"Not found orig element '{notif.args[1]}' in '{notif.args[2]}'"

                elif ntype == NotificationType.UninstallingModSwfElementNotFound:
                    string = f"Not found mod element '{notif.args[1]}' in '{notif.args[2]}'"

                if string:
                    errors.append(string)
                else:
                    errors.append(repr(notif))

            if errors:
                string = ""
                for error in errors:
                    string += f"{error}\n"

                self.showError("Errors:", string)

    @QExecMainThread
    def showError(self, title, content, action=None, terminate=False):
        self.buttonsDialog.setTitle(title)

        if self.acceptDialog.isShown():
            self.acceptDialog.hide()

        if self.buttonsDialog.isShown():
            self.buttonsDialog.hide()

        if self.progressDialog.isShown():
            self.progressDialog.hide()
            self.bulkOperationCount = 0

        if action is None:
            action = self.buttonsDialog.hide

        if terminate:
            action = TerminateApp

        # If it's a long traceback, show a shorter summary and keep the full one for the button
        display_content = content
        if "Traceback (most recent call last):" in content:
            lines = content.strip().split("\n")
            # Extract the last few lines (the actual error)
            display_content = "An unexpected error occurred during the operation.\n\n" + "\n".join(lines[-2:])

        self.buttonsDialog.setContent(display_content)
        self.buttonsDialog.setButtons([("Copy Error", lambda: self.copyToClipboard(f"{title}\n\n{content}")),
                                       ("Ok", action)])
        self.buttonsDialog.show()

    def checkGameRunning(self):
        try:
            # Try multiple process names to be sure
            for proc_name in ["Brawlhalla.exe", "Brawlhalla64.exe"]:
                output = subprocess.check_output(f'tasklist /FI "IMAGENAME eq {proc_name}" /NH', 
                                                 shell=True, 
                                                 creationflags=subprocess.CREATE_NO_WINDOW).decode(errors='ignore').lower()
                if proc_name.lower() in output:
                    self.showError("Game is running!", 
                                   "Brawlhalla is currently running. Please close the game before installing or uninstalling mods.")
                    return True
        except Exception as e:
            print(f"[DEBUG] checkGameRunning error: {e}")
        return False

    def copyToClipboard(self, text):
        cb = QApplication.clipboard()
        cb.clear()
        cb.setText(text)

    def checkUnsavedSettings(self, nextScreenMethod):
        if self.settings.hasUnsavedChanges:
            self.acceptDialog.setTitle("Unsaved Changes")
            self.acceptDialog.setContent("Save the settings before changing tab!")
            self.acceptDialog.ui.accept.setText("Save")
            self.acceptDialog.ui.cancel.setText("Discard")
            
            def saveAndContinue():
                self.settings.saveSettings()
                self.acceptDialog.hide()
                nextScreenMethod()
            
            def discardAndContinue():
                self.settings.hasUnsavedChanges = False
                self.acceptDialog.hide()
                nextScreenMethod()
                
            self.acceptDialog.setAccept(saveAndContinue)
            self.acceptDialog.setCancel(discardAndContinue)
            self.acceptDialog.show()
        else:
            nextScreenMethod()

    def syncSettingsWithCore(self):
        if self.controller:
            self.controller.setDefaultMetadata(
                self.config.defaultAuthor,
                self.config.defaultGameVersion,
                self.config.defaultModVersion
            )
            
            # Update paths if they changed
            self.modsPath = self.config.modsPath or self._local_mods
            os.makedirs(self.modsPath, exist_ok=True)
            self.modsSourcesPath = self.config.modsSourcesPath or self._local_mods_sources
            os.makedirs(self.modsSourcesPath, exist_ok=True)
            self.controller.setModsPath(self.modsPath)
            self.controller.setModsSourcesPath(self.modsSourcesPath)
            
            if self.config.brawlhallaPath:
                core.worker.config.ModloaderCoreConfig.customBrawlhallaPath = self.config.brawlhallaPath
                core.worker.config.ModloaderCoreConfig.save()

    def openCacheFolder(self):
        os.startfile(core.MODLOADER_CACHE_PATH)

    def uninstallAllMods(self):
        if self.checkGameRunning():
            return
            
        installed_mods = [btn for btn in self.mods.modsButtons if btn.modClass.installed]
        if not installed_mods:
            return
            
        self.acceptDialog.setTitle("Uninstall All")
        self.acceptDialog.setContent(f"Are you sure you want to uninstall all {len(installed_mods)} installed mods?")
        self.acceptDialog.ui.accept.setText("Uninstall All")
        self.acceptDialog.ui.cancel.setText("Cancel")
        self.acceptDialog.setAccept(lambda: self._doUninstallAll(installed_mods))
        self.acceptDialog.show()

    def _doUninstallAll(self, mods_to_uninstall):
        self.acceptDialog.hide()
        self.bulkOperationCount = len(mods_to_uninstall)
        for modButton in mods_to_uninstall:
            self.uninstallMod(modButton)

    def clearCache(self):
        self.acceptDialog.setTitle("Clear Cache")
        self.acceptDialog.setContent(
            "Clearing the cache may cause problems, especially if you already have mods installed.\n\n"
            "It is recommended to uninstall mods first before clearing the cache.\n\n"
            "The application will CLOSE after clearing the cache. You must reopen it manually.\n\n"
            "Are you sure you want to clear the cache?"
        )
        self.acceptDialog.ui.accept.setText("Clear")
        self.acceptDialog.ui.cancel.setText("Cancel")
        self.acceptDialog.setAccept(self._doClearCache)
        self.acceptDialog.setCancel(self.acceptDialog.hide)
        self.acceptDialog.show()

    def _doClearCache(self):
        import shutil
        try:
            # Delete everything inside MODLOADER_CACHE_PATH except core.*, config_*, files.json, and association files
            for filename in os.listdir(core.MODLOADER_CACHE_PATH):
                file_path = os.path.join(core.MODLOADER_CACHE_PATH, filename)
                try:
                    # Protection list
                    if any([
                        filename.startswith("core."),
                        filename.startswith("config_"),
                        filename == "files.json",
                        filename.endswith(".ico"),
                        filename.endswith(".png"),
                        filename.endswith(".reg")
                    ]):
                        continue
                        
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
            
            # Recreate necessary folders
            os.makedirs(os.path.join(core.MODLOADER_CACHE_PATH, "OriginalFiles"), exist_ok=True)
            
            self.buttonsDialog.setTitle("Cache Cleared")
            self.buttonsDialog.setContent("The application cache has been cleared. The app will now close.")
            self.buttonsDialog.setButtons([("Ok", TerminateApp)])
            self.buttonsDialog.show()
        except Exception as e:
            self.showError("Error clearing cache", str(e))
        finally:
            self.acceptDialog.hide()

    def setLoadingScreen(self):
        ClearFrame(self.ui.mainFrame)
        AddToFrame(self.ui.mainFrame, self.loading)
        self.loading.setText("Loading mods sources...")

    def setModsScreen(self):
        ClearFrame(self.ui.mainFrame)
        AddToFrame(self.ui.mainFrame, self.header)
        AddToFrame(self.ui.mainFrame, self.mods)

    def updateSortState(self, field, reverse):
        self.currentSortField = field
        self.currentSortReverse = reverse

    def setSettingsScreen(self):
        ClearFrame(self.ui.mainFrame)

        AddToFrame(self.ui.mainFrame, self.header)
        AddToFrame(self.ui.mainFrame, self.settings)

    def showInformation(self):
        self.buttonsDialog.setTitle("About")

        string = TextFormatter.table([["Product:", PROGRAM_NAME],
                                      ["Version:", VERSION],
                                      ["GitHub tag:", GIT_VERSION or "None"],
                                      ["Status:", 'Beta' if PRERELEASE else 'Release'],
                                      ["Core version:", CORE_VERSION],
                                      ["Homepage:", f"<url=\"{GITHUB}/{REPO}\">{GITHUB}/{REPO}</url>"],
                                      [None, f"<url=\"{GAMEBANANA}\">{GAMEBANANA}</url>"],
                                      ["Tool Maintainers:", "LordShadow505 & Bucccket"],
                                      ["Author:", "I_FabrizioG_I"],
                                      ["Modhalla Discord:", f"<url=\"https://discord.gg/ctzYZxBHgY\">https://discord.gg/ctzYZxBHgY</url>"]], newLine=False)

        self.buttonsDialog.setContent(TextFormatter.format(string, 11))
        self.buttonsDialog.setButtons([("Ok", self.buttonsDialog.hide)])
        self.buttonsDialog.show()

    def showBrawlhallaNotFoundDialog(self):
        message = (
            "Brawlhalla Path Not Found!\n\n"
            "The location of <b>Brawlhalla.exe</b> could not be detected automatically.\n\n"
            "Please click <b>'Select Path'</b> to locate your <i>Brawlhalla.exe</i> or installation folder.\n\n"
            "<b>Note:</b>\n"
            "• You can also set or change the Brawlhalla path anytime in <b>Settings</b>.\n"
            "• If you cancel, the application will still load, but mods <u>cannot be installed</u> until 'Brawlhalla.exe' is selected."
        )
        self.acceptDialog.setTitle("Brawlhalla Path Not Found")
        self.acceptDialog.setContent(TextFormatter.format(message, 11))
        self.acceptDialog.ui.accept.setText("Select Path")
        self.acceptDialog.ui.cancel.setText("Cancel")
        self.acceptDialog.setAccept(self._browseBrawlhallaPath)
        self.acceptDialog.setCancel(self.acceptDialog.hide)
        self.acceptDialog.show()

    def _browseBrawlhallaPath(self):
        self.acceptDialog.hide()
        from PySide6.QtWidgets import QFileDialog

        initial_dir = self.config.brawlhallaPath if (self.config.brawlhallaPath and os.path.exists(self.config.brawlhallaPath)) else "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Brawlhalla"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Brawlhalla.exe or Installation Folder",
            initial_dir,
            "Brawlhalla Executable (Brawlhalla.exe *.exe);;All Files (*)"
        )

        if not file_path:
            return

        folder = os.path.dirname(file_path) if os.path.isfile(file_path) else file_path

        if os.path.exists(folder) and (os.path.isfile(os.path.join(folder, "Brawlhalla.exe")) or "Brawlhalla.exe" in os.listdir(folder)):
            self.config.brawlhallaPath = folder
            self.config.save()
            if hasattr(core, 'worker') and hasattr(core.worker, 'config'):
                core.worker.config.ModloaderCoreConfig.customBrawlhallaPath = folder
                core.worker.config.ModloaderCoreConfig.save()
            if hasattr(core, 'worker') and hasattr(core.worker, 'brawlhalla'):
                core.worker.brawlhalla.BRAWLHALLA_PATH = folder
                
            if hasattr(self, 'controller') and self.controller and hasattr(self.controller, 'reloadMods'):
                self.controller.reloadMods()
        else:
            err_msg = (
                "Invalid Brawlhalla Path!\n\n"
                f"The selected directory:\n<b>{folder}</b>\n\n"
                "Does not contain <b>Brawlhalla.exe</b>. Please select the folder containing Brawlhalla.exe."
            )
            self.acceptDialog.setTitle("Invalid Path")
            self.acceptDialog.setContent(TextFormatter.format(err_msg, 11))
            self.acceptDialog.ui.accept.setText("Try Again")
            self.acceptDialog.ui.cancel.setText("Cancel")
            self.acceptDialog.setAccept(self.showBrawlhallaNotFoundDialog)
            self.acceptDialog.setCancel(self.acceptDialog.hide)
            self.acceptDialog.show()

    def saveModSource(self):
        if self.mods.selectedModButton is not None:
            modSources = self.mods.selectedModButton.modClass

            self.controller.setModName(modSources.hash, modSources.name)
            self.controller.setModAuthor(modSources.hash, modSources.author)
            self.controller.setModGameVersion(modSources.hash, modSources.gameVersion)
            self.controller.setModVersion(modSources.hash, modSources.version)
            self.controller.setModTags(modSources.hash, modSources.tags)
            self.controller.setModDescription(modSources.hash, modSources.description)
            self.controller.setModPreviews(modSources.hash, modSources.previewsPaths)

            self.controller.saveModSource(modSources.hash)

    def installMod(self):
        bh_path = getattr(core.worker.brawlhalla, 'BRAWLHALLA_PATH', None) if (hasattr(core, 'worker') and hasattr(core.worker, 'brawlhalla')) else None
        if not bh_path or not os.path.exists(bh_path) or not os.path.isfile(os.path.join(bh_path, "Brawlhalla.exe")):
            self.showBrawlhallaNotFoundDialog()
            return

        if self.checkGameRunning():
            return
            
        if self.mods.selectedModButton is not None:
            if self.bulkOperationCount <= 0:
                self.bulkOperationCount = 1
            modClass = self.mods.selectedModButton.modClass
            print(f"[Creator DEBUG] installMod called for: '{modClass.name}' | hash: {modClass.hash} | modFileExist: {modClass.modFileExist}", flush=True)
            if modClass.modFileExist:
                self.controller.getModConflict(modClass.hash)

    def uninstallMod(self, modButton=None):
        if self.checkGameRunning():
            return
            
        if modButton is None or isinstance(modButton, bool):
            modButton = self.mods.selectedModButton
            if self.bulkOperationCount <= 0:
                self.bulkOperationCount = 1
            
        if modButton is not None:
            modClass = modButton.modClass
            print(f"[Creator DEBUG] uninstallMod called for: '{modClass.name}' | hash: {modClass.hash}", flush=True)
            self.controller.uninstallMod(modClass.hash)

    def reinstallMod(self):
        if self.checkGameRunning():
            return
            
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            print(f"[Creator DEBUG] reinstallMod called for: '{modClass.name}' | hash: {modClass.hash}", flush=True)
            self.controller.uninstallMod(modClass.hash)
            self.controller.getModConflict(modClass.hash)

    def deleteMod(self):
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass

            self.buttonsDialog.deleteButtons()
            self.buttonsDialog.setTitle(f"Delete mod '{modClass.name}'")

            if modClass.installed:
                self.buttonsDialog.setContent("To delete mod, you need to uninstall it")
            elif modClass.modFileExist:
                self.buttonsDialog.setContent("")
                self.buttonsDialog.addButton("Delete mod and sources", self.deleteModAllData)
                self.buttonsDialog.addButton("Delete mod", self.deleteModFile)
            else:
                self.buttonsDialog.addButton("Delete sources", self.deleteModSources)

            self.buttonsDialog.addButton("Cancel", self.buttonsDialog.hide)

            self.buttonsDialog.show()

    def buildMod(self):
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            print(f"[Creator DEBUG] buildMod (compileModSources) called for: '{modClass.name}' | hash: {modClass.hash}", flush=True)
            self.controller.compileModSources(modClass.hash)

    def createMod(self):
        folderName = self.inputDialog.getInput().strip()

        if not folderName:
            self.inputDialog.clearInput()
            self.inputDialog.setTitle("Create mod...")
            self.inputDialog.setContent("Enter mod folder name")
            self.inputDialog.setAccept(self.createMod)
            self.inputDialog.setCancel(lambda: [self.inputDialog.hide(), self.inputDialog.clearInput()])
            self.inputDialog.show()
        else:
            self.controller.createMod(folderName)

    def reloadMods(self):
        self.setLoadingScreen()
        self.mods.removeAllMods()
        self.controller.reloadModsSources()
        self.controller.reloadMods()
        self.controller.getModsSourcesData()
        self.controller.getModsData()

    def openModsSourcesFolder(self):
        os.startfile(self.modsSourcesPath)

    def deleteModFile(self):
        modClass = self.mods.selectedModButton.modClass
        modClass.modFileExist = False
        self.controller.deleteMod(modClass.hash)
        self.mods.updateButtons()
        self.buttonsDialog.hide()

    def deleteModSources(self):
        modClass = self.mods.selectedModButton.modClass
        self.controller.deleteModSources(modClass.hash)
        self.buttonsDialog.hide()
        self.reloadMods()

    def deleteModAllData(self):
        self.deleteModFile()
        self.deleteModSources()

    @QExecMainThread
    def newVersion(self, url: str, fileUrl: str, version: str, body: str):
        self.buttonsDialog.setTitle(f"New Version Available '{version}'")
        rendered_html = render_markdown_to_html(body)
        self.buttonsDialog.setContent(rendered_html)
        self.buttonsDialog.setDialogSize(min_width=680, max_height=420)
        self.buttonsDialog.deleteButtons()
        self.buttonsDialog.addButton("GO TO SITE", lambda: webbrowser.open(url))
        if fileUrl:
            self.buttonsDialog.addButton("UPDATE", lambda: [self.buttonsDialog.hide(),
                                                            self.updateApp(fileUrl, version)])
        self.buttonsDialog.addButton("CANCEL", self.buttonsDialog.hide)
        self.buttonsDialog.show()

    def handleUpdateApp(self, blocknum, blocksize, totalsize):
        readedData = blocknum * blocksize

        if totalsize > 0:
            downloadPercentage = int(readedData * 100 / totalsize)
            self.progressDialog.setValue(downloadPercentage)
            QApplication.processEvents()

    def updateApp(self, fileUrl: str, version: str):
        import urllib.request
        filePath = os.path.join(os.getcwd(), "temp.exe")
        fileName = os.path.split(fileUrl)[1]

        self.progressDialog.setMaximum(100)
        self.progressDialog.setTitle(f"Update ModCreator to '{version}'")
        self.progressDialog.setContent(f"Download '{fileName}'")
        self.progressDialog.show()
        urllib.request.urlretrieve(fileUrl, filePath, self.handleUpdateApp)
        self.progressDialog.hide()

        clientPath = os.environ.get("CLIENT_PATH")
        if not clientPath and core and hasattr(core, 'MODLOADER_CACHE_PATH'):
            possibleClient = os.path.join(core.MODLOADER_CACHE_PATH, "ModLoaderClient.exe")
            if os.path.exists(possibleClient):
                clientPath = possibleClient

        currentExe = os.path.abspath(sys.argv[0])
        if clientPath and os.path.exists(clientPath):
            subprocess.Popen([clientPath, "-update", currentExe, filePath])
        else:
            cmd = f'ping 127.0.0.1 -n 3 > NUL & move /y "{filePath}" "{currentExe}" & start "" "{currentExe}"'
            subprocess.Popen(cmd, shell=True)

        QApplication.exit(0)

    def checkNewVersion(self):
        latest = GetLatest()

        if latest is not None:
            newVersion, fileUrl, version, body = latest
            self.newVersion(newVersion, fileUrl, version, body)


class BmodsSplash(QSplashScreen):
    """
    QSplashScreen that renders real-time dynamic loading text
    at fixed position (202, 302) using Bespoke font.
    """
    def __init__(self, pixmap: QPixmap, font_family: str):
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self._font_family = font_family
        self._status = ""

    def set_status(self, text: str, delay_ms: int = 120):
        self._status = text
        self.repaint()
        QApplication.processEvents()
        if delay_ms > 0:
            import time
            time.sleep(delay_ms / 1000.0)
            QApplication.processEvents()

    def drawContents(self, painter: QPainter):
        if not self._status:
            return
        font = QFont(self._font_family, 13)
        painter.setFont(font)
        painter.setPen(QColor("#CCCCCC"))
        painter.drawText(202, 302, self._status)


def RunApp():
    app = QApplication.instance() or QApplication(sys.argv)
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Exo 2/Exo2-SemiBold.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Black.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-BlackItalic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Bold.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-BoldItalic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Italic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Medium.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-MediumItalic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Regular.ttf")

    # Load Bespoke font for splash
    font_family = "Arial"
    bespoke_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "ui_sources", "resources", "fonts", "Bespoke", "Bespoke.ttf"),
        os.path.join(os.path.dirname(sys.executable), "ui", "ui_sources", "resources", "fonts", "Bespoke", "Bespoke.ttf"),
    ]
    for b_path in bespoke_candidates:
        if os.path.exists(b_path):
            f_id = QFontDatabase.addApplicationFont(b_path)
            if f_id != -1:
                fams = QFontDatabase.applicationFontFamilies(f_id)
                if fams:
                    font_family = fams[0]
                    break

    splash_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "splash.png"),
        os.path.join(os.path.dirname(sys.executable), "splash.png"),
    ]
    splash = get_global_splash()
    if not splash:
        for s_path in splash_candidates:
            if os.path.exists(s_path):
                pixmap = QPixmap(s_path)
                if not pixmap.isNull():
                    splash = BmodsSplash(pixmap, font_family)
                    splash.show()
                    set_global_splash(splash)
                    break

    InitWindowSetText("Loading mods sources and core...")

    window = ModCreator()
    window.show()

    InitWindowClose()

    exitId = app.exec()
    TerminateApp()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    RunApp()
