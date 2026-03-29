import ctypes
import ctypes.wintypes
import time
import logging
import uuid
import keyboard
import pyperclip
import threading
from deep_translator import GoogleTranslator

log = logging.getLogger("translator")

user32 = ctypes.WinDLL("user32", use_last_error=True)

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

SCAN_CTRL = 0x1D
SCAN_A = 0x1E
SCAN_C = 0x2E
SCAN_V = 0x2F

COPY_KEY_SCAN_CODES = frozenset(keyboard.key_to_scan_codes("c"))
COPY_KEY_NAMES = frozenset({"c", "с"})

DOUBLE_C_INTERVAL = 0.6

_last_ctrl_c_time = 0.0
_double_c_hook = None
_double_c_callback = None

_after_translate_fn = None


ULONG_PTR = ctypes.wintypes.WPARAM


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUTUNION),
    ]


user32.SendInput.argtypes = (
    ctypes.wintypes.UINT,
    ctypes.POINTER(INPUT),
    ctypes.c_int,
)
user32.SendInput.restype = ctypes.wintypes.UINT


def set_after_translate_fn(fn):
    global _after_translate_fn
    _after_translate_fn = fn


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
        _send_key_event(vk, KEYEVENTF_KEYUP)


def _make_key_input(vk: int, flags: int = 0) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=vk,
            wScan=0,
            dwFlags=flags,
            time=0,
            dwExtraInfo=0,
        ),
    )


def _send_inputs(*inputs: INPUT) -> bool:
    if not inputs:
        return True

    ctypes.set_last_error(0)
    payload = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(payload), payload, ctypes.sizeof(INPUT))
    if sent != len(payload):
        log.error(
            "SendInput failed: sent=%s expected=%s last_error=%s",
            sent,
            len(payload),
            ctypes.get_last_error(),
        )
        return False
    return True


def _send_key_event(vk: int, flags: int = 0) -> bool:
    return _send_inputs(_make_key_input(vk, flags))


def _send_ctrl_key(key_vk: int, key_scan: int, post_delay: float = 0.2):
    ctrl_down = _make_key_input(VK_CONTROL)
    key_down = _make_key_input(key_vk)
    key_up = _make_key_input(key_vk, KEYEVENTF_KEYUP)
    ctrl_up = _make_key_input(VK_CONTROL, KEYEVENTF_KEYUP)
    sent = _send_inputs(ctrl_down, key_down, key_up, ctrl_up)
    log.info(
        "SendInput Ctrl+key batch status: sent=%s key_vk=0x%02X",
        sent,
        key_vk,
    )
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

    clipboard_marker = f"__translator_copy_marker__:{uuid.uuid4()}"
    marker_set = _clipboard_set(clipboard_marker)
    log.info(f"Clipboard marker installed: {marker_set}")

    log.info("Sending Ctrl+A ...")
    _send_ctrl_key(VK_A, SCAN_A, post_delay=0.15)
    log.info("Ctrl+A done")

    text = None
    for attempt in range(10):
        log.info(f"Copy attempt {attempt + 1}/10: sending Ctrl+C ...")
        _send_ctrl_key(VK_C, SCAN_C, post_delay=0.25)

        content = _clipboard_get()
        log.info(f"Clipboard: {repr(content[:80])}")

        if content != clipboard_marker and content.strip():
            text = content
            log.info(f"Copied! ({len(text)} chars)")
            break

        log.warning("Clipboard unchanged, retrying...")
        time.sleep(0.1)

    if text is None:
        log.error("FAILED to copy after all attempts")
        _clipboard_set(old_clipboard)
        _call_after_translate()
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

    _call_after_translate()
    log.info("=== do_translate END ===")


def _translate_and_paste(source_lang: str, target_lang: str) -> None:
    log.info(f"=== translate_and_paste START ===")

    _release_all_modifiers()
    _wait_modifiers_released(timeout=1.0)
    time.sleep(0.05)

    text = _clipboard_get()
    log.info(f"Clipboard text ({len(text)} chars): {repr(text[:150])}")

    if not text or not text.strip():
        log.warning("Clipboard is empty, nothing to translate")
        _call_after_translate()
        return

    translated = translate_text(text, source_lang, target_lang)
    log.info(f"Translated: {repr(translated[:150])}")

    old_clipboard = text

    _clipboard_set(translated)
    time.sleep(0.1)

    log.info("Sending Ctrl+V ...")
    keyboard.unhook_all()
    time.sleep(0.05)
    _send_ctrl_key(VK_V, SCAN_V, post_delay=0.3)
    log.info("Ctrl+V done")

    time.sleep(0.2)
    _clipboard_set(old_clipboard)
    log.info("Clipboard restored")

    _call_after_translate()
    log.info("=== translate_and_paste END ===")


def _call_after_translate():
    if _after_translate_fn:
        log.info("Calling after-translate callback...")
        _after_translate_fn()


def _is_copy_key_event(event) -> bool:
    if getattr(event, "scan_code", None) in COPY_KEY_SCAN_CODES:
        return True

    name = (getattr(event, "name", "") or "").lower()
    return name in COPY_KEY_NAMES


def _on_ctrl_c_event(event):
    global _last_ctrl_c_time, _double_c_hook

    if event.event_type != keyboard.KEY_DOWN:
        return

    ctrl_pressed = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
    if not ctrl_pressed or not _is_copy_key_event(event):
        return

    now = time.time()
    time_since_last = now - _last_ctrl_c_time

    log.info(f"Ctrl+C detected (time_since_last={time_since_last:.3f}s)")

    if time_since_last < DOUBLE_C_INTERVAL:
        log.info("Double Ctrl+C detected! Triggering translation...")
        _last_ctrl_c_time = 0.0

        if _double_c_callback:
            src, tgt = _double_c_callback()
            threading.Thread(
                target=_translate_and_paste, args=(src, tgt), daemon=True
            ).start()
        return

    _last_ctrl_c_time = now


def start_double_ctrl_c_monitor(get_langs_fn) -> None:
    global _double_c_callback, _double_c_hook, _last_ctrl_c_time

    stop_double_ctrl_c_monitor()

    _double_c_callback = get_langs_fn
    _last_ctrl_c_time = 0.0

    _double_c_hook = keyboard.hook(_on_ctrl_c_event, suppress=False)
    log.info("Double Ctrl+C trigger scan codes: %s", sorted(COPY_KEY_SCAN_CODES))
    log.info("Double Ctrl+C monitor started")


def stop_double_ctrl_c_monitor() -> None:
    global _double_c_hook, _double_c_callback, _last_ctrl_c_time
    if _double_c_hook:
        try:
            keyboard.unhook(_double_c_hook)
        except Exception:
            pass
        _double_c_hook = None
    _double_c_callback = None
    _last_ctrl_c_time = 0.0
    log.info("Double Ctrl+C monitor stopped")
