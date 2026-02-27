"""
VISE OS — Camoufox Browser Management

Launch/manage Camoufox browser sessions with anti-detect configuration.
Supports persistent (NewBrowser) and non-persistent (Camoufox context manager) modes.
Includes page navigation with wait-for-load and cleanup.
"""

import os
import shutil

from camoufox.sync_api import Camoufox, NewBrowser
from playwright.sync_api import sync_playwright

from src.platform_config import (
    camoufox_config_olustur,
    parmak_izi_os_sec,
    platform_ayarlari_al,
)
from src.utils import log, screenshot_al, insan_gibi_bekle


def proxy_yapilandir():
    """Build proxy configuration dict from .env variables.

    Reads PROXY_SERVER, PROXY_USERNAME, and PROXY_PASSWORD from environment.
    Returns None if PROXY_SERVER is not set.

    Returns:
        dict or None: Proxy config dict with server/username/password keys,
                      or None if no proxy configured.
    """
    server = os.getenv("PROXY_SERVER")
    if not server:
        return None

    proxy = {"server": server}

    username = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    if username:
        proxy["username"] = username
    if password:
        proxy["password"] = password

    log(f"[BROWSER] Proxy yapilandirildi: {server}")
    return proxy


def _xvfb_kontrol():
    """Check if Xvfb is available on Linux systems.

    Only relevant on Linux where headless='virtual' requires Xvfb.
    Logs a warning if Xvfb is not installed but does not raise —
    Camoufox will handle the virtual display requirement.

    Returns:
        bool: True if Xvfb is available or not needed, False if missing on Linux.
    """
    p = platform_ayarlari_al()
    if not p["xvfb_gerekli"]:
        return True

    xvfb_yolu = shutil.which("Xvfb")
    if not xvfb_yolu:
        log(
            "[BROWSER] UYARI: Linux'ta Xvfb bulunamadi. "
            "Kurulum: sudo apt install -y xvfb libgtk-3-0 libx11-xcb1 libasound2"
        )
        return False

    log(f"[BROWSER] Xvfb mevcut: {xvfb_yolu}")
    return True


def _profil_kilidi_kontrol(user_data_dir):
    """Check if a browser profile directory is locked by another process.

    Looks for common lock files that indicate an active browser session.

    Args:
        user_data_dir: Path to the browser profile directory.

    Returns:
        bool: True if profile appears available, False if locked.
    """
    if not os.path.exists(user_data_dir):
        return True

    lock_files = ["lock", "parent.lock", ".parentlock"]
    for lock_dosya in lock_files:
        lock_yolu = os.path.join(user_data_dir, lock_dosya)
        if os.path.exists(lock_yolu):
            log(
                f"[BROWSER] UYARI: Profil dizini kilitli olabilir: {lock_yolu}. "
                f"Baska bir tarayici oturumu acik olabilir."
            )
            return False

    return True


def tarayici_baslat(ulke_kodu: str, proxy: dict = None):
    """Launch Camoufox with persistent context for cookie/session reuse.

    Uses NewBrowser + sync_playwright() for persistent context, which
    preserves cookies (including cf_clearance) across sessions.

    All configuration comes from camoufox_config_olustur() which handles:
        - Platform-specific headless mode
        - Fingerprint OS rotation per session
        - Mandatory flags (humanize, disable_coop, geoip)
        - Per-country profile isolation

    Args:
        ulke_kodu: VFS country code (e.g., "aut", "hrv", "che").
        proxy: Optional proxy dict with server/username/password keys.
               If None, reads from .env via proxy_yapilandir().

    Returns:
        tuple: (pw, context, page) where:
            - pw: Playwright instance (for cleanup via pw.stop())
            - context: Browser context (for cleanup via context.close())
            - page: Active page for automation

    Raises:
        Exception: If browser fails to launch. Logged before re-raising.
    """
    log(f"[BROWSER] Tarayici baslatiliyor: ulke={ulke_kodu}, mod=persistent")

    # Pre-flight checks
    _xvfb_kontrol()

    # Resolve proxy from .env if not explicitly provided
    if proxy is None:
        proxy = proxy_yapilandir()

    # Build config from platform detection + fingerprint rotation
    config = camoufox_config_olustur(ulke_kodu, proxy)

    # Check for profile directory lock
    _profil_kilidi_kontrol(config["user_data_dir"])

    # KRITIK: main_world_eval=True — Camoufox izole JS dunyasini bypass et
    # Bu olmadan page.evaluate() Angular'in yasadigi ana dunyaya erisemez
    # ve click event'leri Angular event handler'larina ulasmaz
    config["main_world_eval"] = True

    log(
        f"[BROWSER] Config: headless={config['headless']}, "
        f"os={config['os']}, geoip={config['geoip']}, "
        f"humanize={config['humanize']}, disable_coop={config['disable_coop']}, "
        f"persistent_context={config['persistent_context']}, "
        f"user_data_dir={config['user_data_dir']}"
    )

    try:
        pw = sync_playwright().start()
        context = NewBrowser(pw, **config)
        page = context.new_page()

        log("[BROWSER] Tarayici basariyla baslatildi (persistent)")
        return pw, context, page

    except Exception as e:
        log(f"[BROWSER] Tarayici baslatilamadi: {type(e).__name__}: {e}")
        raise


def tarayici_baslat_test(ulke_kodu: str = None):
    """Launch Camoufox in non-persistent mode for testing/quick sessions.

    Uses the Camoufox() context manager which does NOT persist cookies
    or browser state. Suitable for health checks and one-off tests.

    Args:
        ulke_kodu: Optional VFS country code. If None, uses minimal config.

    Returns:
        tuple: (camoufox_cm, browser, page) where:
            - camoufox_cm: Camoufox context manager (for __exit__ cleanup)
            - browser: Browser instance
            - page: Active page for automation

    Raises:
        Exception: If browser fails to launch. Logged before re-raising.
    """
    log(f"[BROWSER] Test tarayicisi baslatiliyor: ulke={ulke_kodu}, mod=non-persistent")

    _xvfb_kontrol()

    p = platform_ayarlari_al()

    config = {
        "headless": p["headless"],
        "humanize": True,
        "os": parmak_izi_os_sec(),
        "geoip": True,
        "disable_coop": True,
    }

    # Add proxy from .env if available
    proxy = proxy_yapilandir()
    if proxy:
        config["proxy"] = proxy

    log(
        f"[BROWSER] Test config: headless={config['headless']}, "
        f"os={config['os']}, humanize={config['humanize']}"
    )

    try:
        camoufox_cm = Camoufox(**config)
        browser = camoufox_cm.__enter__()
        page = browser.new_page()

        log("[BROWSER] Test tarayicisi basariyla baslatildi (non-persistent)")
        return camoufox_cm, browser, page

    except Exception as e:
        log(f"[BROWSER] Test tarayicisi baslatilamadi: {type(e).__name__}: {e}")
        raise


def sayfa_git(page, url, wait_until="domcontentloaded", timeout=60000):
    """Navigate to a URL with configurable wait strategy.

    Wraps page.goto() with logging, error handling, and screenshot on failure.

    Args:
        page: Playwright page object.
        url: Target URL to navigate to.
        wait_until: Navigation wait condition (default: "domcontentloaded").
                    Options: "load", "domcontentloaded", "networkidle", "commit".
        timeout: Navigation timeout in milliseconds (default: 60000).

    Returns:
        Response: Playwright Response object from navigation.

    Raises:
        TimeoutError: If navigation times out. Screenshot captured before re-raising.
        Exception: If navigation fails. Screenshot captured before re-raising.
    """
    log(f"[BROWSER] Sayfa aciliyor: {url} (wait_until={wait_until})")

    try:
        response = page.goto(url, wait_until=wait_until, timeout=timeout)

        # Log response status
        if response:
            log(f"[BROWSER] Sayfa yuklendi: {url} (status={response.status})")
        else:
            log(f"[BROWSER] Sayfa yuklendi: {url} (response=None)")

        # Brief human-like pause after page load
        insan_gibi_bekle(1.0, 2.5)

        return response

    except TimeoutError:
        log(f"[BROWSER] TIMEOUT: Sayfa yuklenemedi: {url}")
        screenshot_al(page, "sayfa_git_timeout")
        raise
    except Exception as e:
        log(f"[BROWSER] HATA: Sayfa acma basarisiz: {type(e).__name__}: {e}")
        try:
            screenshot_al(page, "sayfa_git_error")
        except Exception:
            log("[BROWSER] Screenshot alinamadi (sayfa muhtemelen kapali)")
        raise


def tarayici_kapat(pw=None, context=None, page=None):
    """Safely close browser resources in the correct order.

    Handles persistent context cleanup (page -> context -> playwright).
    Each step is wrapped in its own try/except to ensure maximum cleanup
    even if one step fails.

    Args:
        pw: Playwright instance from sync_playwright().start().
        context: Browser context from NewBrowser().
        page: Page object (closed implicitly with context, but explicit close
              ensures clean state).
    """
    log("[BROWSER] Tarayici kapatiliyor...")

    if page:
        try:
            page.close()
            log("[BROWSER] Sayfa kapatildi")
        except Exception as e:
            log(f"[BROWSER] Sayfa kapatma hatasi: {type(e).__name__}: {e}")

    if context:
        try:
            context.close()
            log("[BROWSER] Context kapatildi")
        except Exception as e:
            log(f"[BROWSER] Context kapatma hatasi: {type(e).__name__}: {e}")

    if pw:
        try:
            pw.stop()
            log("[BROWSER] Playwright durduruldu")
        except Exception as e:
            log(f"[BROWSER] Playwright durdurma hatasi: {type(e).__name__}: {e}")

    log("[BROWSER] Tarayici basariyla kapatildi")


def tarayici_kapat_test(camoufox_cm=None, browser=None, page=None):
    """Safely close non-persistent browser resources.

    Handles Camoufox context manager cleanup for test sessions.

    Args:
        camoufox_cm: Camoufox context manager instance.
        browser: Browser instance from context manager.
        page: Page object.
    """
    log("[BROWSER] Test tarayicisi kapatiliyor...")

    if page:
        try:
            page.close()
            log("[BROWSER] Test sayfasi kapatildi")
        except Exception as e:
            log(f"[BROWSER] Test sayfasi kapatma hatasi: {type(e).__name__}: {e}")

    if camoufox_cm:
        try:
            camoufox_cm.__exit__(None, None, None)
            log("[BROWSER] Camoufox context manager kapatildi")
        except Exception as e:
            log(f"[BROWSER] Camoufox kapatma hatasi: {type(e).__name__}: {e}")

    log("[BROWSER] Test tarayicisi basariyla kapatildi")


def cf_clearance_kontrol(context):
    """Check if cf_clearance cookie exists in the browser context.

    Used to determine if Cloudflare challenge has been completed
    and cookie is being reused from a previous session.

    Args:
        context: Browser context to check cookies on.

    Returns:
        bool: True if cf_clearance cookie is present.
    """
    try:
        cookies = context.cookies()
        for cookie in cookies:
            if cookie.get("name") == "cf_clearance":
                log(
                    f"[BROWSER] cf_clearance bulundu: "
                    f"domain={cookie.get('domain')}, "
                    f"expires={cookie.get('expires')}"
                )
                return True

        log("[BROWSER] cf_clearance bulunamadi — Cloudflare challenge gerekebilir")
        return False

    except Exception as e:
        log(f"[BROWSER] Cookie kontrol hatasi: {type(e).__name__}: {e}")
        return False