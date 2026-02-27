"""
VISE OS — Shared Utilities

Logging with millisecond timestamps, screenshot capture, human-like wait/typing,
tiered element finding with selector fallback, and debug-first error handling wrapper.
"""

import datetime
import os
import random
import time

from src.platform_config import platform_ayarlari_al
from src.country_manager import UlkeYonetici


# --- Module-Level Directory Setup ---
# Resolve debug directories from platform config on import.
# These must be available before any log() or screenshot_al() call.
_platform = platform_ayarlari_al()
LOG_DIR = os.path.join(_platform["debug_dir"], "logs")
SCREENSHOT_DIR = os.path.join(_platform["debug_dir"], "screenshots")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Singleton UlkeYonetici instance for selector loading
_ulke_yonetici = None


def _ulke_yonetici_al():
    """Lazy-load singleton UlkeYonetici instance.

    Returns:
        UlkeYonetici: Shared country manager instance.
    """
    global _ulke_yonetici
    if _ulke_yonetici is None:
        _ulke_yonetici = UlkeYonetici()
    return _ulke_yonetici


# --- Pattern 7: Logging Standard ---

def log(mesaj):
    """Log a message to both console and daily log file with millisecond timestamps.

    Dual output:
        - Console: print() for real-time monitoring
        - File: debug/logs/vise_YYYY-MM-DD.log (UTF-8, append mode)

    Format: [YYYY-MM-DD HH:MM:SS.mmm] message

    Args:
        mesaj: Log message string (supports Turkish characters via UTF-8).
    """
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    satir = f"[{zaman}] {mesaj}"
    print(satir)

    log_dosya = os.path.join(LOG_DIR, f"vise_{datetime.date.today()}.log")
    with open(log_dosya, "a", encoding="utf-8") as f:
        f.write(satir + "\n")


# --- Screenshot Capture ---

def screenshot_al(page, ad):
    """Capture a timestamped screenshot for debugging.

    Saves to debug/screenshots/{YYYYMMDD_HHMMSS}_{ad}.png

    Args:
        page: Playwright page object.
        ad: Descriptive name for the screenshot (e.g., "login_timeout", "register_ok").
    """
    try:
        zaman = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dosya_adi = f"{zaman}_{ad}.png"
        dosya_yolu = os.path.join(SCREENSHOT_DIR, dosya_adi)
        page.screenshot(path=dosya_yolu, full_page=True)
        log(f"[SCREENSHOT] {dosya_yolu}")
    except Exception as e:
        log(f"[SCREENSHOT] HATA: Screenshot alinamadi: {type(e).__name__}: {e}")


# --- Pattern 5: Human-Like Behavior ---

def insan_gibi_bekle(min_sn=1.0, max_sn=3.0):
    """Wait for a random duration to simulate human behavior.

    NEVER uses fixed time.sleep — always random.uniform(min, max).

    Args:
        min_sn: Minimum wait time in seconds (default: 1.0).
        max_sn: Maximum wait time in seconds (default: 3.0).
    """
    time.sleep(random.uniform(min_sn, max_sn))


def insan_gibi_yaz(page, selector, metin):
    """Type text into a form field with human-like behavior.

    Pattern:
        1. Click the element first (mimics human focus behavior)
        2. Wait briefly (0.3-0.8s)
        3. Type character by character with random 50-150ms delay per keystroke
        4. Wait briefly after typing (0.5-1.5s)

    Args:
        page: Playwright page object.
        selector: CSS selector string for the target input element.
        metin: Text string to type into the field.
    """
    element = page.locator(selector)
    element.click()
    insan_gibi_bekle(0.3, 0.8)
    for karakter in metin:
        element.type(karakter, delay=random.randint(50, 150))
    insan_gibi_bekle(0.5, 1.5)


# --- Pattern 4: Tiered Selector Fallback ---

def element_bul(page, ulke_kodu, sayfa, alan_adi, timeout=15000):
    """Find a page element using tiered fallback selectors from country config.

    Tries selectors in order: primary -> fallback_1 -> fallback_2.
    Each tier gets timeout/3 milliseconds to resolve.
    On total failure, captures a screenshot and raises an exception.

    Args:
        page: Playwright page object.
        ulke_kodu: VFS country code (e.g., "aut", "hrv").
        sayfa: Page name — "register" or "login".
        alan_adi: Field name — e.g., "email", "password", "first_name".
        timeout: Total timeout in milliseconds (default: 15000). Split across 3 tiers.

    Returns:
        ElementHandle: The found page element.

    Raises:
        Exception: If all three selector tiers fail. Screenshot captured before raising.
    """
    uy = _ulke_yonetici_al()
    selectors = uy.selectors_yukle(ulke_kodu)
    sel = selectors.get(sayfa, {}).get(alan_adi, {})

    kademe_timeout = timeout // 3

    for kademe in ["primary", "fallback_1", "fallback_2"]:
        selector_deger = sel.get(kademe)
        if not selector_deger:
            log(f"[SELECTOR] {alan_adi} -> {kademe} tanimli degil, atlaniyor...")
            continue
        try:
            element = page.wait_for_selector(selector_deger, timeout=kademe_timeout)
            if element:
                log(f"[SELECTOR] {alan_adi} -> {kademe} found")
                return element
        except Exception:
            log(f"[SELECTOR] {alan_adi} -> {kademe} failed...")

    # All tiers failed — capture debug screenshot and raise
    ai_hint = sel.get("ai_hint", "No hint available")
    screenshot_al(page, f"selector_not_found_{alan_adi}")
    raise Exception(
        f"Element not found: {ulke_kodu}/{sayfa}/{alan_adi}. "
        f"All 3 selector tiers failed. Hint: {ai_hint}"
    )


# --- Pattern 6: Debug-First Error Handling ---

def akis_calistir(adim_adi, fonksiyon, page, *args, **kwargs):
    """Execute a flow step with debug-first error handling.

    Wraps any function with:
        - Start/end logging
        - Screenshot + log on TimeoutError
        - Screenshot + log on any other Exception
        - Always re-raises — never swallows errors

    Args:
        adim_adi: Step name for logging (e.g., "REGISTER_FORM_FILL").
        fonksiyon: Callable to execute (receives page as first arg).
        page: Playwright page object (passed to fonksiyon).
        *args: Additional positional arguments for fonksiyon.
        **kwargs: Additional keyword arguments for fonksiyon.

    Returns:
        Any: Return value of fonksiyon.

    Raises:
        TimeoutError: Re-raised after logging and screenshot.
        Exception: Re-raised after logging and screenshot.
    """
    try:
        log(f"[{adim_adi}] Starting...")
        sonuc = fonksiyon(page, *args, **kwargs)
        log(f"[{adim_adi}] OK")
        return sonuc
    except TimeoutError:
        log(f"[{adim_adi}] TIMEOUT")
        screenshot_al(page, f"{adim_adi}_timeout")
        raise
    except Exception as e:
        log(f"[{adim_adi}] ERROR: {type(e).__name__}: {e}")
        screenshot_al(page, f"{adim_adi}_error")
        raise
