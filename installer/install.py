import sys
import os
import requests
import shutil
import subprocess
import json
from zipfile import BadZipFile
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QCheckBox,
    QPushButton, QMessageBox, QScrollArea, QGroupBox, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from ctypes import windll
import zipfile

UPDATE_SERVER = "http://134.17.25.127:54321"
CONFIG_URL = f"{UPDATE_SERVER}/installer_config.json"

class InstallerApp(QWidget):
    def __init__(self):
        super().__init__()

        self.apply_dark_theme()

        if not self.is_admin():
            self.request_admin()

        self.setWindowTitle("Установщик программ")
        self.resize(500, 600)

        self.layout = QVBoxLayout(self)
        self.label = QLabel("Выберите компоненты для установки:")
        self.layout.addWidget(self.label)

        self.checkboxes = []
        self.apps_data = []

        self.scroll = QScrollArea()
        self.group = QGroupBox()
        self.group_layout = QVBoxLayout()
        self.group_layout.setSpacing(10)
        self.group.setLayout(self.group_layout)
        self.scroll.setWidget(self.group)
        self.scroll.setWidgetResizable(True)
        self.layout.addWidget(self.scroll)

        self.install_button = QPushButton("Установить")
        self.install_button.setStyleSheet("padding: 10px; font-weight: bold; background-color: #2d89ef; color: white; border-radius: 5px;")
        self.install_button.clicked.connect(self.install_selected)
        self.layout.addWidget(self.install_button)

        self.load_config()

    def apply_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        QApplication.instance().setPalette(dark_palette)

    def is_admin(self):
        try:
            return windll.shell32.IsUserAnAdmin()
        except:
            return False

    def request_admin(self):
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        ctypes = __import__('ctypes')
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)

    def load_config(self):
        try:
            resp = requests.get(CONFIG_URL, timeout=10)
            config = resp.json()
            self.nssm_url = f"{UPDATE_SERVER}/{config.get('nssm_url')}"
            self.apps_data = config.get("apps", [])

            for app in self.apps_data:
                frame = QFrame()
                frame.setStyleSheet("background-color: #3c3c3c; border-radius: 6px; padding: 6px;")
                frame_layout = QVBoxLayout()
                cb = QCheckBox(f"{app['name']} — {app.get('description', '')}")
                cb.setChecked(True)
                cb.setStyleSheet("font-size: 14px; color: white;")
                frame_layout.addWidget(cb)
                frame.setLayout(frame_layout)
                self.group_layout.addWidget(frame)
                self.checkboxes.append(cb)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить конфигурацию: {e}")

    def install_selected(self):
        for i, cb in enumerate(self.checkboxes):
            if cb.isChecked():
                self.install_app(self.apps_data[i])
        QMessageBox.information(self, "Готово", "Выбранные программы установлены.")

    def install_app(self, app):
        try:
            exe_url = f"{UPDATE_SERVER}/{app['exe']}"
            install_dir = app["install_dir"]
            os.makedirs(install_dir, exist_ok=True)

            exe_name = os.path.basename(app["exe"])
            local_exe_path = os.path.join(install_dir, exe_name)

            print(f"Скачиваю {exe_url}...")
            with requests.get(exe_url, stream=True, timeout=30) as r:
                with open(local_exe_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)

            if app.get("create_shortcut"):
                desktop = os.path.join(os.environ["PUBLIC"], "Desktop")
                shortcut_path = os.path.join(desktop, f"{app['name']}.lnk")
                self.create_shortcut(local_exe_path, shortcut_path)

            if app.get("register_service"):
                nssm_path = os.path.join(os.getenv("TEMP"), "nssm.exe")
                if not os.path.exists(nssm_path):
                    with requests.get(self.nssm_url, stream=True, timeout=30) as r:
                        with open(nssm_path, "wb") as f:
                            shutil.copyfileobj(r.raw, f)
                service_name = app["register_service"]
                subprocess.run([nssm_path, "install", service_name, local_exe_path])
                subprocess.run([nssm_path, "set", service_name, "Start", "SERVICE_AUTO_START"])
                subprocess.run(["sc", "start", service_name], check=False)

            for item in app.get("extra", []):
                item_url = f"{UPDATE_SERVER}/{item}"
                if item.endswith('/'):
                    zip_name = os.path.basename(item.rstrip('/')) + ".zip"
                    zip_url = f"{UPDATE_SERVER}/{os.path.dirname(item.rstrip('/'))}/{zip_name}"
                    zip_path = os.path.join(install_dir, "_temp.zip")

                    print(f"Пробуем скачать {zip_url}")
                    with requests.get(zip_url, stream=True, timeout=30) as r:
                        with open(zip_path, "wb") as f:
                            shutil.copyfileobj(r.raw, f)
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(install_dir)
                        os.remove(zip_path)
                    except BadZipFile:
                        raise Exception(f"Файл не является ZIP: {zip_path}")
                else:
                    print(f"Скачиваю файл: {item_url}")
                    rel_path = os.path.relpath(item, start=os.path.dirname(app["exe"]))
                    target_path = os.path.join(install_dir, rel_path)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with requests.get(item_url, stream=True, timeout=30) as r:
                        with open(target_path, "wb") as f:
                            shutil.copyfileobj(r.raw, f)

        except Exception as e:
            QMessageBox.warning(self, "Ошибка установки", f"Ошибка при установке {app['name']}: {e}")

    def create_shortcut(self, target, shortcut_path):
        try:
            import pythoncom
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = os.path.dirname(target)
            shortcut.save()
        except Exception as e:
            print(f"Не удалось создать ярлык: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InstallerApp()
    window.show()
    sys.exit(app.exec())
