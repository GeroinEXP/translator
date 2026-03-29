# HotKey Translator

HotKey Translator is a small Windows tray app that translates text in place inside the currently focused application.

It supports two input flows:

- `Hotkey` mode: press a global shortcut, the app selects all text in the active field, copies it, translates it, and pastes the result back.
- `Double Ctrl+C` mode: select text manually, press `Ctrl+C` twice quickly, and the app translates the clipboard contents and pastes the translation back.

The app uses Google Translate through `deep-translator`, stores settings locally, and can be packaged into a single `.exe` with PyInstaller.

## Features

- System tray application with a settings window
- Configurable global hotkey
- Double `Ctrl+C` translation mode
- Source and target language selection
- Clipboard preservation and restore
- Optional Windows startup integration
- One-file Windows build via PyInstaller

## Screenshots

<img width="452" height="495" alt="image" src="https://github.com/user-attachments/assets/4b1796dd-e78a-420a-8239-dd68e5293999" />


## Requirements

- Windows 10 or Windows 11
- Python 3.12 recommended
- Internet connection for translation requests

This project is currently Windows-focused. It uses WinAPI keyboard input and global keyboard hooks.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run From Source

```bash
python main.py
```

The app starts in the system tray. Double-click the tray icon to open settings.

## Build

Build a single executable:

```bash
python build.py
```

Output:

```text
dist/HotKeyTranslator.exe
```

You can also build directly with PyInstaller:

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name HotKeyTranslator --hidden-import deep_translator --hidden-import keyboard --hidden-import pyperclip --hidden-import PyQt5 main.py
```

## How It Works

### Hotkey mode

1. A global hotkey triggers translation.
2. The app sends `Ctrl+A` to the active control.
3. The selected text is copied with `Ctrl+C`.
4. The text is translated.
5. The translation is pasted with `Ctrl+V`.
6. The original clipboard content is restored.

### Double Ctrl+C mode

1. You select text manually.
2. You press `Ctrl+C` twice within a short interval.
3. The app reads the clipboard text.
4. The text is translated.
5. The result is pasted back into the active application.

## Settings

The settings window lets you configure:

- Translation mode
- Global hotkey
- Source language
- Target language
- Run at Windows startup

Configuration is stored here:

```text
%APPDATA%\HotKeyTranslator\config.json
```

## Project Structure

```text
main.py                 Entry point and logging setup
build.py                PyInstaller build script
src/app.py              Tray app lifecycle and mode switching
src/config.py           Config loading, saving, autostart handling
src/hotkey_manager.py   Global hotkey registration
src/settings_window.py  PyQt settings UI
src/translator.py       Translation flow, clipboard handling, WinAPI input
```

## Notes

- Global keyboard hooks may require running in an environment where the `keyboard` package can access input events reliably.
- Some applications do not support `Ctrl+A`, `Ctrl+C`, or `Ctrl+V` in the usual way. In those cases, `Hotkey` mode may not work for that specific target.
- Translation depends on external network access through Google Translate.
- The app logs detailed debug information to stdout when launched from `python main.py`.

## License

No license file is included in this repository at the moment.
