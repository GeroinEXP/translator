import keyboard
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.config import LANGUAGES, MODES, save_config, set_autostart


class HotkeyRecorder(QLineEdit):
    recorded = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click then press key combination...")
        self._recording = False
        self._keys = set()
        self._hook = None

    def mousePressEvent(self, event):
        if not self._recording:
            self.start_recording()
        super().mousePressEvent(event)

    def start_recording(self):
        self._recording = True
        self._keys = set()
        self.setText("Press key combination...")
        self.setStyleSheet("background-color: #fff3cd; border: 2px solid #ffc107;")
        self.setFocus()
        if self._hook:
            keyboard.unhook(self._hook)
        self._hook = keyboard.hook(self._on_key_event)

    def _on_key_event(self, event):
        if not self._recording:
            return

        if event.event_type == keyboard.KEY_DOWN:
            self._keys.add(event.name)
        elif event.event_type == keyboard.KEY_UP:
            if len(self._keys) > 1 or (
                len(self._keys) == 1
                and event.name not in ("ctrl", "alt", "shift", "windows")
            ):
                hotkey_str = "+".join(
                    sorted(
                        self._keys,
                        key=lambda k: (
                            0
                            if k == "ctrl"
                            else 1
                            if k == "alt"
                            else 2
                            if k == "shift"
                            else 3
                            if k == "windows"
                            else 4
                        ),
                    )
                )
                self.stop_recording(hotkey_str)

    def stop_recording(self, hotkey_str: str = ""):
        self._recording = False
        if self._hook:
            keyboard.unhook(self._hook)
            self._hook = None
        self._keys = set()
        if hotkey_str:
            self.setText(hotkey_str)
            self.recorded.emit(hotkey_str)
        self.setStyleSheet("")

    def set_hotkey(self, hotkey_str: str):
        self.setText(hotkey_str)


class SettingsWindow(QWidget):
    settings_changed = pyqtSignal(dict)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = dict(config)
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        self.setWindowTitle("HotKey Translator — Settings")
        self.setMinimumWidth(450)
        self.setWindowFlags(self.windowFlags())

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("⚙ Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        mode_group = QGroupBox("Translation Mode")
        mode_layout = QVBoxLayout(mode_group)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        for mode_id, mode_label in MODES.items():
            self.mode_combo.addItem(mode_label, mode_id)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_layout.addLayout(mode_row)

        self.mode_desc = QLabel("")
        self.mode_desc.setWordWrap(True)
        self.mode_desc.setStyleSheet("color: #666; font-size: 11px; padding: 4px 0;")
        mode_layout.addWidget(self.mode_desc)

        layout.addWidget(mode_group)

        self.hotkey_group = QGroupBox("Hotkey")
        hotkey_layout = QVBoxLayout(self.hotkey_group)

        hotkey_hint = QLabel("Hotkey to trigger translation:")
        hotkey_layout.addWidget(hotkey_hint)

        hotkey_row = QHBoxLayout()
        self.hotkey_recorder = HotkeyRecorder()
        hotkey_row.addWidget(self.hotkey_recorder)
        self.btn_reset_hotkey = QPushButton("Reset")
        self.btn_reset_hotkey.setFixedWidth(70)
        self.btn_reset_hotkey.clicked.connect(self._reset_hotkey)
        hotkey_row.addWidget(self.btn_reset_hotkey)
        hotkey_layout.addLayout(hotkey_row)

        layout.addWidget(self.hotkey_group)

        lang_group = QGroupBox("Languages")
        lang_layout = QVBoxLayout(lang_group)

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Source language:"))
        self.source_lang_combo = QComboBox()
        self._populate_languages(self.source_lang_combo)
        src_row.addWidget(self.source_lang_combo)
        lang_layout.addLayout(src_row)

        tgt_row = QHBoxLayout()
        tgt_row.addWidget(QLabel("Target language:"))
        self.target_lang_combo = QComboBox()
        self._populate_languages(self.target_lang_combo, include_auto=False)
        tgt_row.addWidget(self.target_lang_combo)
        lang_layout.addLayout(tgt_row)

        layout.addWidget(lang_group)

        system_group = QGroupBox("System")
        system_layout = QVBoxLayout(system_group)
        self.autostart_check = QCheckBox("Run at Windows startup")
        system_layout.addWidget(self.autostart_check)
        layout.addWidget(system_group)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #0078d4; color: white; "
            "padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #106ebe; }"
        )
        self.btn_save.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def _populate_languages(self, combo: QComboBox, include_auto: bool = True):
        for code, name in LANGUAGES.items():
            if not include_auto and code == "auto":
                continue
            combo.addItem(f"{name} ({code})", code)

    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        if mode == "double_ctrl_c":
            self.mode_desc.setText(
                "Select text manually, then press Ctrl+C twice quickly.\n"
                "The clipboard text will be translated and pasted back."
            )
            self.hotkey_group.setVisible(False)
        else:
            self.mode_desc.setText(
                "Press the hotkey → text in active field is selected (Ctrl+A), "
                "translated and replaced."
            )
            self.hotkey_group.setVisible(True)

    def _load_config(self):
        mode = self._config.get("mode", "hotkey")
        idx = self.mode_combo.findData(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self._on_mode_changed()

        self.hotkey_recorder.set_hotkey(self._config.get("hotkey", "ctrl+shift+t"))

        src = self._config.get("source_lang", "auto")
        idx = self.source_lang_combo.findData(src)
        if idx >= 0:
            self.source_lang_combo.setCurrentIndex(idx)

        tgt = self._config.get("target_lang", "en")
        idx = self.target_lang_combo.findData(tgt)
        if idx >= 0:
            self.target_lang_combo.setCurrentIndex(idx)

        self.autostart_check.setChecked(self._config.get("autostart", False))

    def _reset_hotkey(self):
        self.hotkey_recorder.set_hotkey("ctrl+shift+t")

    def _save(self):
        mode = self.mode_combo.currentData()

        if mode == "hotkey":
            hotkey = self.hotkey_recorder.text().strip()
            if not hotkey or "Press key" in hotkey:
                QMessageBox.warning(self, "Error", "Please set a hotkey.")
                return
        else:
            hotkey = self._config.get("hotkey", "ctrl+shift+t")

        new_config = {
            "mode": mode,
            "hotkey": hotkey,
            "source_lang": self.source_lang_combo.currentData(),
            "target_lang": self.target_lang_combo.currentData(),
            "autostart": self.autostart_check.isChecked(),
        }

        save_config(new_config)
        set_autostart(new_config["autostart"])

        self._config = new_config
        self.settings_changed.emit(new_config)

        QMessageBox.information(self, "Saved", "Settings saved successfully!")

    def closeEvent(self, event):
        self.hotkey_recorder.stop_recording()
        super().closeEvent(event)
