"""
VISE OS — Cross-Platform Detection & Fingerprint OS Rotation

Runtime OS detection, platform-specific path/headless configuration,
fingerprint OS rotation for anti-detect, and Camoufox config builder.
"""

import platform
import os
import random


def platform_ayarlari_al():
    """Detect runtime OS, set platform-specific paths and headless mode.

    Returns:
        dict: Platform settings with keys:
            - sistem: Runtime OS name ("Darwin", "Windows", "Linux")
            - headless: False for macOS/Windows, "virtual" for Linux (Xvfb)
            - profile_dir: Browser profile storage path
            - debug_dir: Debug output (logs, screenshots, HAR) path
            - xvfb_gerekli: True only on Linux
    """
    sistem = platform.system()  # "Darwin", "Windows", "Linux"

    ayarlar = {
        "sistem": sistem,
        "headless": False,
        "profile_dir": "",
        "debug_dir": "",
        "xvfb_gerekli": False,
    }

    if sistem == "Darwin":
        ayarlar["headless"] = False
        ayarlar["profile_dir"] = os.path.expanduser(
            "~/Library/Application Support/VISE-OS/vfs-profile"
        )
        ayarlar["debug_dir"] = os.path.expanduser("~/vise-os-bot/debug")
    elif sistem == "Windows":
        ayarlar["headless"] = False
        ayarlar["profile_dir"] = os.path.join(
            os.environ.get("APPDATA", "C:\\Users\\Default\\AppData\\Roaming"),
            "VISE-OS", "vfs-profile"
        )
        ayarlar["debug_dir"] = os.path.join(
            os.environ.get("USERPROFILE", "C:\\Users\\Default"),
            "vise-os-bot", "debug"
        )
    elif sistem == "Linux":
        ayarlar["headless"] = "virtual"  # Xvfb required
        ayarlar["xvfb_gerekli"] = True
        ayarlar["profile_dir"] = os.path.expanduser("~/.config/vise-os/vfs-profile")
        ayarlar["debug_dir"] = os.path.expanduser("~/vise-os-bot/debug")

    # .env overrides — check BEFORE using defaults
    env_profile = os.getenv("PROFILE_DIR")
    env_debug = os.getenv("DEBUG_DIR")
    if env_profile:
        ayarlar["profile_dir"] = env_profile
    if env_debug:
        ayarlar["debug_dir"] = env_debug

    # HEADLESS override from .env
    env_headless = os.getenv("HEADLESS")
    if env_headless:
        # Convert string to boolean/virtual
        if env_headless.lower() in ["false", "no", "0"]:
            ayarlar["headless"] = False
            ayarlar["xvfb_gerekli"] = False
        elif env_headless.lower() in ["true", "yes", "1"]:
            ayarlar["headless"] = True
        elif env_headless.lower() == "virtual":
            ayarlar["headless"] = "virtual"
            ayarlar["xvfb_gerekli"] = True

    os.makedirs(ayarlar["profile_dir"], exist_ok=True)
    os.makedirs(ayarlar["debug_dir"], exist_ok=True)

    return ayarlar


def parmak_izi_os_sec():
    """Select fingerprint OS with weighted random based on Turkish user distribution.

    Weights mirror Turkey desktop OS market share:
        - Windows: 75%
        - macOS: 17%
        - Linux: 8%

    Called fresh for EVERY browser session — never use a static/fixed os parameter.
    This is the OS shown to VFS (fingerprint), NOT the runtime OS.

    Returns:
        str: One of "windows", "macos", "linux"
    """
    return random.choices(
        population=["windows", "macos", "linux"],
        weights=[75, 17, 8],
        k=1
    )[0]


def camoufox_config_olustur(ulke_kodu: str = "aut", proxy: dict = None):
    """Generate platform-agnostic, country-agnostic Camoufox configuration.

    Args:
        ulke_kodu: VFS country code for per-country profile isolation (e.g., "aut")
        proxy: Optional proxy dict with server/username/password keys

    Returns:
        dict: Camoufox launch configuration with keys:
            - headless: From platform detection
            - humanize: True (mandatory — human-like cursor movement)
            - os: Random fingerprint OS per session
            - geoip: True (auto timezone/locale from proxy IP)
            - disable_coop: True (mandatory — Cloudflare Turnstile iframe access)
            - persistent_context: True (cookie persistence for cf_clearance reuse)
            - user_data_dir: Per-country isolated profile path
            - proxy: (optional) Proxy configuration if provided
    """
    p = platform_ayarlari_al()

    config = {
        "headless": p["headless"],        # From platform detection
        "humanize": True,                  # MANDATORY — human-like cursor
        "os": parmak_izi_os_sec(),        # Random fingerprint per session
        "geoip": True,                     # Auto timezone/locale from proxy IP
        "disable_coop": True,              # MANDATORY — Cloudflare Turnstile iframe access
        "persistent_context": True,        # Cookie persistence (cf_clearance reuse)
        "user_data_dir": os.path.join(     # Per-country isolated profile
            p["profile_dir"], ulke_kodu
        ),
    }

    if proxy:
        config["proxy"] = proxy

    return config
