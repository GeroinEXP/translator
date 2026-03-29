import subprocess
import sys
import os


def build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "HotKeyTranslator",
        "--hidden-import",
        "deep_translator",
        "--hidden-import",
        "keyboard",
        "--hidden-import",
        "pyperclip",
        "--hidden-import",
        "PyQt5",
        main_py,
    ]

    print("Building HotKeyTranslator.exe...")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=script_dir, check=True)
    print("\nDone! Executable: dist/HotKeyTranslator.exe")


if __name__ == "__main__":
    build()
