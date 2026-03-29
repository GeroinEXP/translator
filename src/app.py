import sys
import os
from functools import partial

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import QSize, Qt

from src.config import load_config, LANGUAGES
from src.hotkey_manager import HotkeyManager
from src.translator import do_translate
from src.settings_window import SettingsWindow


def _create_icon() -> QIcon:
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor("#0078d4"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 12, 12)

    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(10, 18, 20, 6, 3, 3)
    painter.drawRoundedRect(34, 18, 20, 6, 3, 3)

    painter.setBrush(QColor("#50e6ff"))
    painter.drawRoundedRect(10, 30, 20, 6, 3, 3)
    painter.drawRoundedRect(34, 40, 20, 6, 3, 3)

    painter.setBrush(QColor("#ffffff"))
    font = QFont("Segoe UI", 14, QFont.Bold)
    painter.setFont(font)
    painter.drawText(18, 58, "T")

    painter.end()

    return QIcon(pixmap)


class TranslatorApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config = load_config()
        self.hotkey_manager = HotkeyManager()
        self.settings_window = None

        self._setup_translations()
        self._setup_tray()
        self._register_hotkey()

    def _setup_translations(self):
        self._translate_fn = partial(
            do_translate,
            source_lang=self.config.get("source_lang", "auto"),
            target_lang=self.config.get("target_lang", "en"),
        )

    def _setup_tray(self):
        self.icon = _create_icon()

        self.tray = QSystemTrayIcon(self.icon, self.app)
        self.tray.setToolTip(
            f"HotKey Translator\n"
            f"Hotkey: {self.config.get('hotkey', 'ctrl+shift+t')}\n"
            f"{LANGUAGES.get(self.config.get('source_lang', 'auto'), '?')} → "
            f"{LANGUAGES.get(self.config.get('target_lang', 'en'), '?')}"
        )

        menu = QMenu()

        settings_action = QAction("Settings", self.app)
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Exit", self.app)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_settings()

    def _register_hotkey(self):
        hotkey = self.config.get("hotkey", "ctrl+shift+t")
        self.hotkey_manager.register(hotkey, self._translate_fn)

    def _show_settings(self):
        if self.settings_window is not None:
            self.settings_window.show()
            self.settings_window.activateWindow()
            self.settings_window.raise_()
            return

        self.settings_window = SettingsWindow(self.config)
        self.settings_window.settings_changed.connect(self._on_settings_changed)
        self.settings_window.show()

    def _on_settings_changed(self, new_config: dict):
        self.config = new_config
        self._setup_translations()
        self._register_hotkey()
        self.tray.setToolTip(
            f"HotKey Translator\n"
            f"Hotkey: {self.config.get('hotkey', 'ctrl+shift+t')}\n"
            f"{LANGUAGES.get(self.config.get('source_lang', 'auto'), '?')} → "
            f"{LANGUAGES.get(self.config.get('target_lang', 'en'), '?')}"
        )

    def _quit(self):
        self.hotkey_manager.unregister()
        self.tray.hide()
        self.app.quit()

    def run(self) -> int:
        return self.app.exec_()
