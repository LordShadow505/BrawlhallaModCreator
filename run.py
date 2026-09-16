import os
import sys

# Detect frozen/compiled binary: supports both PyInstaller (sys.frozen) and Nuitka (__compiled__)
_is_nuitka = False
try:
    _is_nuitka = bool(__compiled__)  # noqa - defined by Nuitka at compile time
except NameError:
    pass

_IS_FROZEN = getattr(sys, 'frozen', False) or _is_nuitka

if _IS_FROZEN:
    # PyInstaller extracts to sys._MEIPASS; Nuitka onefile extracts next to __file__
    if hasattr(sys, '_MEIPASS'):
        _base_dir = sys._MEIPASS
    else:
        _base_dir = os.path.dirname(os.path.abspath(__file__))
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
    # Do not call SetDllDirectoryW here. It replaces the normal Windows DLL
    # search path and prevents JPype from loading a JVM installed elsewhere.

import traceback
import threading
import multiprocessing

from ui.utils.systemdialog import Error



def _bootstrap(self, parent_sentinel=None):
    import itertools
    from multiprocessing.process import _ParentProcess
    from multiprocessing import util, context
    global _current_process, _parent_process, _process_counter, _children

    try:
        if self._start_method is not None:
            context._force_start_method(self._start_method)
        _process_counter = itertools.count(1)
        _children = set()
        util._close_stdin()
        old_process = multiprocessing.current_process()
        _current_process = self
        _parent_process = _ParentProcess(
            self._parent_name, self._parent_pid, parent_sentinel)
        if threading._HAVE_THREAD_NATIVE_ID:
            threading.main_thread()._set_native_id()
        try:
            util._finalizer_registry.clear()
            util._run_after_forkers()
        finally:
            # delay finalization of the old process object until after
            # _run_after_forkers() is executed
            del old_process
        util.info('child process calling self.run()')
        try:
            self.run()
            exitcode = 0
        finally:
            util._exit_function()
    except SystemExit as e:
        if not e.args:
            exitcode = 1
        elif isinstance(e.args[0], int):
            exitcode = e.args[0]
        else:
            sys.stderr.write(str(e.args[0]) + '\n')
            exitcode = 1
    except:
        exitcode = 1
        sys.excepthook(*sys.exc_info())
    finally:
        threading._shutdown()
        util.info('process exiting with exitcode %d' % exitcode)
        util._flush_std_streams()

    return exitcode


multiprocessing.Process._bootstrap = _bootstrap


def handle_exception(exc_type, exc_value, exc_traceback):
    try:
        import pyi_splash
        pyi_splash.close()
    except:
        pass

    errorText = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    from main import ModCreator, PROGRAM_NAME, TerminateApp
    if ModCreator.app is not None:
        ModCreator.app.showError("Fatal Error:",
                                 errorText,
                                 terminate=True)
    else:
        Error(PROGRAM_NAME, errorText)
        TerminateApp()
        #sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = handle_exception
threading.excepthook = lambda hook: handle_exception(hook.exc_type, hook.exc_value, hook.exc_traceback)


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


if __name__ == "__main__" and "--multiprocessing-fork" not in sys.argv:
    import os
    os.chdir(os.path.split(sys.argv[0])[0])

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase, QPixmap
    from main import BmodsSplash, set_global_splash, InitWindowSetText, RunApp

    app = QApplication.instance() or QApplication(sys.argv)

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
    for s_path in splash_candidates:
        if os.path.exists(s_path):
            pixmap = QPixmap(s_path)
            if not pixmap.isNull():
                splash = BmodsSplash(pixmap, font_family)
                splash.show()
                set_global_splash(splash)
                InitWindowSetText("Initializing Mod Creator...", delay_ms=100)
                app.processEvents()
                # Ensure dynamic splash is visibly rendered before dismissing Nuitka pre-splash
                import time
                time.sleep(0.05)
                close_nuitka_splash()
                break
    else:
        close_nuitka_splash()

    RunApp()

elif "--multiprocessing-fork" in sys.argv:
    from core import Controller
    Controller()
