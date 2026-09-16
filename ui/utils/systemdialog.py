import sys
import ctypes


def Error(title, message):
    if sys.platform in ["win32", "win64"]:
        try:
            import win32api
            import win32con
            win32api.MessageBox(None, str(message), str(title),
                                win32con.MB_ICONERROR | win32con.MB_OK | win32con.MB_DEFBUTTON1)
        except Exception:
            try:
                ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x10 | 0x0)
            except Exception:
                pass
    else:
        pass
