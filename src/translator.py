import ctypes
import ctypes.wintypes
import time
import logging
import keyboard
import pyperclip
from deep_translator import GoogleTranslator

log = logging.getLogger("translator")

user32 = ctypes.windll.user32

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56

KEYEVENTF_KEYUP = 0x0002

SCAN_CTRL = 0x1D
SCAN_A = 0x1E
SCAN_C = 0x2E
SCAN_V = 0x2F


def _get_foreground_window_title() -> str:
    fg = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(fg, buf, 256)
    return buf.value


def _wait_modifiers_released(timeout: float = 2.0):
    start = time.time()
    while time.time() - start < timeout:
        ctrl = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        shift = user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
        alt = user32.GetAsyncKeyState(VK_MENU) & 0x8000
        if not ctrl and not shift and not alt:
            return True
        time.sleep(0.02)
    return False


def _release_all_modifiers():
    for vk in (VK_CONTROL, VK_SHIFT, VK_MENU):
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def _send_ctrl_key(key_vk: int, key_scan: int, post_delay: float = 0.2):
    ctypes.windll.user32.keybd_event(VK_CONTROL, SCAN_CTRL, 0, 0)
    time.sleep(0.04)
    ctypes.windll.user32.keybd_event(key_vk, key_scan, 0, 0)
    time.sleep(0.04)
    ctypes.windll.user32.keybd_event(key_vk, key_scan, KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)
    ctypes.windll.user32.keybd_event(VK_CONTROL, SCAN_CTRL, KEYEVENTF_KEYUP, 0)
    time.sleep(post_delay)


def _clipboard_get() -> str:
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _clipboard_set(text: str) -> bool:
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def translate_text(
    text: str, source_lang: str = "auto", target_lang: str = "en"
) -> str:
    if not text or not text.strip():
        return text
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result = translator.translate(text)
        return result if result else text
    except Exception as e:
        log.error(f"Translation error: {e}")
        return text


def do_translate(source_lang: str = "auto", target_lang: str = "en") -> None:
    log.info(f"=== do_translate START (src={source_lang}, tgt={target_lang}) ===")

    fg_title = _get_foreground_window_title()
    log.info(f"Foreground window: '{fg_title}'")

    log.info("Unhooking keyboard library...")
    keyboard.unhook_all()
    time.sleep(0.1)

    _release_all_modifiers()
    released = _wait_modifiers_released(timeout=2.0)
    log.info(f"Modifiers released: {released}")

    old_clipboard = _clipboard_get()
    log.info(f"Old clipboard ({len(old_clipboard)} chars): {repr(old_clipboard[:80])}")

    fg_title2 = _get_foreground_window_title()
    log.info(f"Foreground after unhook: '{fg_title2}'")

    log.info("Sending Ctrl+A ...")
    _send_ctrl_key(VK_A, SCAN_A, post_delay=0.15)
    log.info("Ctrl+A done")

    text = None
    for attempt in range(10):
        log.info(f"Copy attempt {attempt + 1}/10: sending Ctrl+C ...")
        _send_ctrl_key(VK_C, SCAN_C, post_delay=0.25)

        content = _clipboard_get()
        log.info(f"Clipboard: {repr(content[:80])}")

        if content != old_clipboard and content.strip():
            text = content
            log.info(f"Copied! ({len(text)} chars)")
            break

        log.warning("Clipboard unchanged, retrying...")
        time.sleep(0.1)

    if text is None:
        log.error("FAILED to copy after all attempts")
        _clipboard_set(old_clipboard)
        _re_register_hotkey()
        return

    log.info(f"Translating: {repr(text[:150])}")
    translated = translate_text(text, source_lang, target_lang)
    log.info(f"Result: {repr(translated[:150])}")

    _clipboard_set(translated)
    time.sleep(0.1)

    log.info("Sending Ctrl+V ...")
    _send_ctrl_key(VK_V, SCAN_V, post_delay=0.3)
    log.info("Ctrl+V done")

    time.sleep(0.2)
    _clipboard_set(old_clipboard)
    log.info("Clipboard restored")

    _re_register_hotkey()
    log.info("=== do_translate END ===")


_re_register_fn = None


def _re_register_hotkey():
    if _re_register_fn:
        log.info("Re-registering hotkey...")
        _re_register_fn()
        log.info("Hotkey re-registered")


def set_re_register_fn(fn):
    global _re_register_fn
    _re_register_fn = fn
