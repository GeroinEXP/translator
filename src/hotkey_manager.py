import threading
import logging
import keyboard

log = logging.getLogger("hotkey")

_re_register_callback = None


class HotkeyManager:
    def __init__(self):
        self._current_hotkey = None
        self._callback = None

    def register(self, hotkey_str: str, callback) -> None:
        global _re_register_callback
        self.unregister()
        self._current_hotkey = hotkey_str
        self._callback = callback
        keyboard.add_hotkey(hotkey_str, self._on_hotkey, suppress=False)
        log.info(f"Registered hotkey: {hotkey_str}")

        def re_register():
            keyboard.add_hotkey(self._current_hotkey, self._on_hotkey, suppress=False)
            log.info(f"Re-registered hotkey: {self._current_hotkey}")

        _re_register_callback = re_register
        from src.translator import set_re_register_fn

        set_re_register_fn(re_register)

    def unregister(self) -> None:
        if self._current_hotkey:
            try:
                keyboard.remove_hotkey(self._current_hotkey)
            except Exception:
                pass
            self._current_hotkey = None
            self._callback = None

    def _on_hotkey(self) -> None:
        log.info(f"Hotkey triggered!")
        if self._callback:
            threading.Thread(target=self._callback, daemon=True).start()

    def update(self, hotkey_str: str, callback) -> None:
        self.register(hotkey_str, callback)
