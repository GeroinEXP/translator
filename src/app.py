import sys
import os
import time
import logging
from functools import partial

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import QSize, Qt

from src.config import load_config, LANGUAGES, MODES
from src.hotkey_manager import HotkeyManager
from src.translator import (
    do_translate,
    start_double_ctrl_c_monitor,
    stop_double_ctrl_c_monitor,
    set_after_translate_fn,
)
from src.settings_window import SettingsWindow

log = logging.getLogger("app")


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

        set_after_translate_fn(self._after_translate)

        self._setup_mode()
        self._setup_tray()

    def _get_langs(self):
        return (
            self.config.get("source_lang", "auto"),
            self.config.get("target_lang", "en"),
        )

    def _setup_mode(self):
        mode = self.config.get("mode", "hotkey")
        log.info(f"Setting up mode: {mode}")

        stop_double_ctrl_c_monitor()
        self.hotkey_manager.unregister()

        time.sleep(0.05)

        if mode == "double_ctrl_c":
            self._setup_double_ctrl_c()
        else:
            self._setup_hotkey_mode()

    def _setup_hotkey_mode(self):
        src, tgt = self._get_langs()
        self._translate_fn = partial(do_translate, source_lang=src, target_lang=tgt)
        hotkey = self.config.get("hotkey", "ctrl+shift+t")
        self.hotkey_manager.register(hotkey, self._translate_fn)

    def _setup_double_ctrl_c(self):
        self._translate_fn = None
        start_double_ctrl_c_monitor(self._get_langs)

    def _after_translate(self):
        mode = self.config.get("mode", "hotkey")
        log.info(f"After translate callback, mode={mode}")

        time.sleep(0.1)

        if mode == "double_ctrl_c":
            start_double_ctrl_c_monitor(self._get_langs)
        else:
            hotkey = self.config.get("hotkey", "ctrl+shift+t")
            self.hotkey_manager.register(hotkey, self._translate_fn)

    def _setup_tray(self):
        self.icon = _create_icon()
        self.tray = QSystemTrayIcon(self.icon, self.app)

        self._update_tray_tooltip()

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

    def _update_tray_tooltip(self):
        mode = self.config.get("mode", "hotkey")
        mode_label = MODES.get(mode, mode)
        lines = ["HotKey Translator", f"Mode: {mode_label}"]

        if mode == "hotkey":
            lines.append(f"Hotkey: {self.config.get('hotkey', 'ctrl+shift+t')}")
        else:
            lines.append("Trigger: Double Ctrl+C")

        src = LANGUAGES.get(self.config.get("source_lang", "auto"), "?")
        tgt = LANGUAGES.get(self.config.get("target_lang", "en"), "?")
        lines.append(f"{src} → {tgt}")

        self.tray.setToolTip("\n".join(lines))

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_settings()

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
        self._setup_mode()
        self._update_tray_tooltip()

    def _quit(self):
        stop_double_ctrl_c_monitor()
        self.hotkey_manager.unregister()
        self.tray.hide()
        self.app.quit()

    def run(self) -> int:
        return self.app.exec_()
