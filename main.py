import os
import sys
import threading
import webbrowser
import multiprocessing
import traceback

from typing import List

# ── Development bootstrap ─────────────────────────────────────────────────────
# In dev, resolve `import core` to the shared BhModLoaderCore-main package.
# This file is excluded from production .spec builds — packaged apps use the
# local core/ folder bundled by PyInstaller.
try:
    _bootstrap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dev_bootstrap.py")
    if os.path.exists(_bootstrap_path):
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("dev_bootstrap", _bootstrap_path)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
except Exception as _e:
    print(f"[dev_bootstrap] skipped: {_e}")
# ─────────────────────────────────────────────────────────────────────────────

try:
    import core
    from core import NotificationType, Notification, Environment, CORE_VERSION

    JAVA_FOUND = True
except ImportError as e:
    Notification = None
    JAVA_FOUND = False

    if e.msg != "Java not found!":
        print(f"Error importing core: {e}")

from PySide6.QtGui import QIcon, QFontDatabase
from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QFrame, QVBoxLayout, QLabel

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
from ui.utils.version import GetLatest, GITHUB, REPO, VERSION, GIT_VERSION, PRERELEASE, GAMEBANANA
from ui.utils.mainthread import QExecMainThread
from ui.utils.config import CreatorConfig

SUPPORT_URL = "https://www.patreon.com/bhmodloader"

PROGRAM_NAME = "Brawlhalla Mod Creator"


def InitWindowSetText(text):
    if getattr(sys, "frozen", False):
        try:
            import pyi_splash
            pyi_splash.update_text(text)
        except:
            pass


def InitWindowClose():
    if getattr(sys, "frozen", False):
        try:
            import pyi_splash
            pyi_splash.update_text("application")
            pyi_splash.close()
        except:
            pass


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
    elif os.path.exists(_local_mods):
        modsPath = _local_mods
    else:
        modsPath = os.path.join(core.MODLOADER_CACHE_PATH, "Mods")

    if config.modsSourcesPath:
        modsSourcesPath = config.modsSourcesPath
    elif os.path.exists(_local_mods_sources):
        modsSourcesPath = _local_mods_sources
    else:
        modsSourcesPath = os.path.join(core.MODLOADER_CACHE_PATH, "Mods Sources")

    errors: List[Notification] = []

    app = None

    def __init__(self):
        super().__init__()
        self.ui = Window(self)

        self.config = CreatorConfig()

        QExecMainThread.init(self)

        InitWindowSetText("ui")

        self.setWindowTitle(PROGRAM_NAME)
        self.setWindowIcon(QIcon(':/icons/resources/icons/App.ico'))

        self.loading = Loading()
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
                         uninstallAllMethod=self.uninstallAllMods)
        self.progressDialog = ProgressDialog(self)
        self.acceptDialog = AcceptDialog(self)  # TODO: Remake to buttons dialog
        self.inputDialog = InputDialog(self)
        self.buttonsDialog = ButtonsDialog(self)

        self.settings = SettingsFrame(
            saveCallback=self.syncSettingsWithCore,
            openCacheMethod=self.openCacheFolder,
            clearCacheMethod=self.clearCache,
            bhPath=core.worker.brawlhalla.BRAWLHALLA_PATH or "Not found",
            modsPath=self.modsPath,
            modsSourcesPath=self.modsSourcesPath,
            cacheSize=format_size(get_dir_size(core.MODLOADER_CACHE_PATH))
        )
        self.bulkOperationCount = 0
        self.setLoadingScreen()
        self.header.setSettingsButtonPressed(self.setSettingsScreen)
        self.header.setModsButtonPressed(lambda: self.checkUnsavedSettings(self.setModsScreen))

        self.setMinimumSize(QSize(850, 550))

        threading.Thread(target=self.checkNewVersion).start()

        self.controller = None

        if JAVA_FOUND:
            threading.Thread(target=self.runController).start()

            # Get core events
            self.controllerGetterTimer = QTimer()
            self.controllerGetterTimer.timeout.connect(self.controllerHandler)
            self.controllerGetterTimer.start(10)
        else:
            message = ("Java not found!\n\nRecommended java: "
                       "<url=\"https://libericajdk.ru/pages/downloads/#/java-8-lts\">"
                       "https://libericajdk.ru/pages/downloads/#/java-8-lts</url>")
            self.showError("Fatal Error:", TextFormatter.format(message, 11), terminate=True)

        InitWindowClose()
        self.__class__.app = self

    def runController(self):
        self.loading.setText("Loading ModLoader Core")

        self.controller = core.Controller()
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

        self.controller.reloadMods()
        self.controller.reloadModsSources()

        self.controller.getModsSourcesData()
        self.controller.getModsData()

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
                    self.loading.setText(f"Loading mod '{modPath}'")
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
                self.showErrorNotifications()

                # Optimized reload: only reload the mod we just built
                self.controller.reloadMod(modHash)
                self.controller.getModsData()

                # Update UI for this mod
                for btn in self.mods.modsButtons:
                    if btn.modClass.hash == modHash:
                        btn.updateData()
                        break
                if self.mods.selectedModButton and self.mods.selectedModButton.modClass.hash == modHash:
                    self.mods.updateAll()

                self.progressDialog.hide()
                self.bulkOperationCount = 0
                #print(f"[DL DEBUG] UI: Progress dialog HIDDEN (Compile Finished)")

            # Errors
            elif ntype in [NotificationType.CompileModSourcesSpriteHasNoSymbolclass,  # Compiler
                           NotificationType.CompileModSourcesSpriteEmpty,
                           NotificationType.CompileModSourcesSpriteNotFoundInFolder,
                           NotificationType.CompileModSourcesUnsupportedCategory,
                           NotificationType.CompileModSourcesUnknownFile,
                           NotificationType.CompileModSourcesSaveError,
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
                                 modSourcesPath=modSourcesData.get("modSourcesPath", ""), date=modSourcesData.get("date", 0.0))

                self.mods.currentGameVersion = modSourcesData.get("currentGameVersion", "")

            self.showErrorNotifications()

        elif cmd == Environment.GetModsData:
            for modData in data[1]:
                self.mods.updateMod(hash=modData.get("hash", ""),
                                    installed=modData.get("installed", False),
                                    modFileExist=modData.get("modFileExist", False))

                self.mods.updateAll()

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
                                 modSourcesPath=modSourcesData.get("modSourcesPath", ""), date=modSourcesData.get("date", 0.0))

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
                    string = f"Unsupported elements category '{notif.args[1]}'"

                elif ntype == NotificationType.CompileModSourcesUnknownFile:
                    string = f"Unknown file '{notif.args[1]}'"

                elif ntype == NotificationType.CompileModSourcesSaveError:
                    string = "Error save .bmod"

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

    def copyToClipboard(self, text):
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(text, mode=cb.Clipboard)

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
            self.modsSourcesPath = self.config.modsSourcesPath or self._local_mods_sources
            self.controller.setModsPath(self.modsPath)
            self.controller.setModsSourcesPath(self.modsSourcesPath)
            
            if self.config.brawlhallaPath:
                core.worker.config.ModloaderCoreConfig.customBrawlhallaPath = self.config.brawlhallaPath
                core.worker.config.ModloaderCoreConfig.save()

    def openCacheFolder(self):
        os.startfile(core.MODLOADER_CACHE_PATH)

    def uninstallAllMods(self):
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
                                      ["Contacts:", "Discord: I_FabrizioG_I#8111"],
                                      [None, "VK: vk/fabriziog"]], newLine=False)

        self.buttonsDialog.setContent(TextFormatter.format(string, 11))
        self.buttonsDialog.setButtons([("Ok", self.buttonsDialog.hide)])
        self.buttonsDialog.show()

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
        if self.mods.selectedModButton is not None:
            if self.bulkOperationCount <= 0:
                self.bulkOperationCount = 1
            modClass = self.mods.selectedModButton.modClass
            if modClass.modFileExist:
                self.controller.getModConflict(modClass.hash)

    def uninstallMod(self, modButton=None):
        if modButton is None or isinstance(modButton, bool):
            modButton = self.mods.selectedModButton
            if self.bulkOperationCount <= 0:
                self.bulkOperationCount = 1
            
        if modButton is not None:
            modClass = modButton.modClass
            self.controller.uninstallMod(modClass.hash)

    def reinstallMod(self):
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
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
        self.buttonsDialog.setTitle(f"New version available '{version}'")
        self.buttonsDialog.setContent(TextFormatter.format(body, 11))
        self.buttonsDialog.deleteButtons()
        self.buttonsDialog.addButton("GO TO SITE", lambda: [webbrowser.open(url),
                                                            self.buttonsDialog.hide()])
        self.buttonsDialog.addButton("CANCEL", self.buttonsDialog.hide)
        self.buttonsDialog.show()

    def checkNewVersion(self):
        latest = GetLatest()

        if latest is not None:
            newVersion, fileUrl, version, body = latest
            self.newVersion(newVersion, fileUrl, version, body)


def RunApp():
    app = QApplication(sys.argv)
    # font_db = QFontDatabase()
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Exo 2/Exo2-SemiBold.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Black.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-BlackItalic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Bold.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-BoldItalic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Italic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Medium.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-MediumItalic.ttf")
    QFontDatabase.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Regular.ttf")
    window = ModCreator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    RunApp()
